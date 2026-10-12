from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from .security_audit import record_security_event
from .auth import authenticate_principal, patient_scope_prefixes, require_patient_access, require_roles
from .storage import _engine
from .storage_schema import patients

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])

class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    external_identifier: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)
    sex: str = Field(min_length=1, max_length=32)
    unit: str = Field(min_length=1, max_length=80)
    bed: str = Field(min_length=1, max_length=40)

class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_identifier: str | None = Field(default=None, min_length=1, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    age: int | None = Field(default=None, ge=0, le=130)
    sex: str | None = Field(default=None, min_length=1, max_length=32)
    unit: str | None = Field(default=None, min_length=1, max_length=80)
    bed: str | None = Field(default=None, min_length=1, max_length=40)

def _serialize(row) -> dict:
    def iso(value): return value.isoformat() if hasattr(value, "isoformat") else value
    return {"patient_id": row["patient_id"], "external_identifier": row["external_identifier"],
            "display_name": row["display_name"], "age": row["age"], "sex": row["sex"],
            "unit": row["unit"], "bed": row["bed"], "active": bool(row["active"]),
            "created_at": iso(row["created_at"]), "updated_at": iso(row["updated_at"]),
            "deactivated_at": iso(row["deactivated_at"])}

def _get_patient(patient_id: str):
    engine = _engine()
    try:
        with engine.connect() as connection:
            return connection.execute(select(patients).where(patients.c.patient_id == patient_id)).mappings().first()
    finally: engine.dispose()

def _require_scoped_patient(patient_id: str, principal: dict[str, str]):
    require_patient_access(patient_id, principal)
    row = _get_patient(patient_id)
    if row is None: raise HTTPException(status_code=404, detail="Patient not found")
    return row

@router.post("", status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, principal: Annotated[dict[str, str], Depends(require_roles("admin", "operator"))]):
    engine = _engine(); now = datetime.now(timezone.utc)
    try:
        with engine.begin() as connection:
            if connection.execute(select(patients.c.patient_id).where(patients.c.patient_id == payload.patient_id)).first():
                raise HTTPException(status_code=409, detail="Patient identifier already exists")
            if connection.execute(select(patients.c.patient_id).where(patients.c.external_identifier == payload.external_identifier)).first():
                raise HTTPException(status_code=409, detail="External patient identifier already exists")
            try:
                connection.execute(patients.insert().values(**payload.model_dump(), created_at=now, updated_at=now, active=True))
            except IntegrityError as exc:
                raise HTTPException(status_code=409, detail="Patient identifier already exists") from exc
            row = connection.execute(select(patients).where(patients.c.patient_id == payload.patient_id)).mappings().one()
        return _serialize(row)
    finally: engine.dispose()

@router.get("")
def list_patients(active: bool | None = Query(default=True), principal: Annotated[dict[str, str], Depends(authenticate_principal)] = None):
    scope = patient_scope_prefixes(principal); engine = _engine()
    try:
        query = select(patients)
        if active is not None: query = query.where(patients.c.active == active)
        if scope is not None: query = query.where(or_(*[patients.c.patient_id.startswith(prefix, autoescape=True) for prefix in scope]))
        query = query.order_by(patients.c.unit.asc(), patients.c.bed.asc(), patients.c.patient_id.asc())
        with engine.connect() as connection: return [_serialize(row) for row in connection.execute(query).mappings().all()]
    finally: engine.dispose()

@router.get("/{patient_id}")
def get_patient(patient_id: str, principal: Annotated[dict[str, str], Depends(authenticate_principal)]):
    return _serialize(_require_scoped_patient(patient_id, principal))

@router.patch("/{patient_id}")
def update_patient(patient_id: str, payload: PatientUpdate, principal: Annotated[dict[str, str], Depends(require_roles("admin", "operator"))]):
    current = _require_scoped_patient(patient_id, principal)
    if not current["active"]: raise HTTPException(status_code=409, detail="Inactive patient must be reactivated through an explicit workflow")
    changes = {k:v for k,v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not changes: raise HTTPException(status_code=422, detail="At least one patient field is required")
    changes["updated_at"] = datetime.now(timezone.utc); engine = _engine()
    try:
        with engine.begin() as connection:
            if "external_identifier" in changes and connection.execute(select(patients.c.patient_id).where(
                patients.c.external_identifier == changes["external_identifier"], patients.c.patient_id != patient_id)).first():
                raise HTTPException(status_code=409, detail="External patient identifier already exists")
            try: connection.execute(update(patients).where(patients.c.patient_id == patient_id).values(**changes))
            except IntegrityError as exc: raise HTTPException(status_code=409, detail="Patient update conflicts with an existing record") from exc
            row = connection.execute(select(patients).where(patients.c.patient_id == patient_id)).mappings().one()
        return _serialize(row)
    finally: engine.dispose()

@router.post("/{patient_id}/deactivate")
def deactivate_patient(patient_id: str, principal: Annotated[dict[str, str], Depends(require_roles("admin", "operator"))]):
    _require_scoped_patient(patient_id, principal); engine = _engine(); now = datetime.now(timezone.utc)
    try:
        with engine.begin() as connection:
            connection.execute(update(patients).where(patients.c.patient_id == patient_id).values(active=False, deactivated_at=now, updated_at=now))
            row = connection.execute(select(patients).where(patients.c.patient_id == patient_id)).mappings().one()
        return _serialize(row)
    finally: engine.dispose()
