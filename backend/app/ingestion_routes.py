"""Authorized, validated observation ingestion."""
from __future__ import annotations
import hashlib,hmac,json,os
from datetime import datetime,timedelta,timezone
from typing import Any,Literal
from fastapi import APIRouter,Depends,Header
from pydantic import BaseModel,ConfigDict,Field,ValidationError,field_validator
from .auth import require_roles,require_patient_access
from .ingestion_store import persist_ingested_observation
from .live_events import hub
from .model import MODEL_VERSION,explain,predict_probability,risk_level
from .schemas import RiskPrediction,VitalInput
ingestion_router=APIRouter(prefix="/api/v1/ingestion",tags=["ingestion"],dependencies=[Depends(require_roles("admin","clinician"))])
class ObservationUnits(BaseModel):
    model_config=ConfigDict(extra="forbid")
    age:Literal["years"];heart_rate:Literal["bpm"];spo2:Literal["percent"];systolic_bp:Literal["mmHg"];diastolic_bp:Literal["mmHg"];temperature:Literal["degC"];respiratory_rate:Literal["breaths/min"]
class IngestionItem(BaseModel):
    model_config=ConfigDict(extra="forbid")
    source_system:str=Field(min_length=1,max_length=80,pattern=r"^[A-Za-z0-9._:-]+$");source_mode:Literal["live","historical_replay"];source_event_id:str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._:-]+$");observed_at:datetime;observation:VitalInput;units:ObservationUnits
    @field_validator("observed_at")
    @classmethod
    def validate_timestamp(cls,value):
        if value.tzinfo is None or value.utcoffset() is None:raise ValueError("observed_at must include a timezone offset")
        normalized=value.astimezone(timezone.utc);now=datetime.now(timezone.utc)
        if normalized>now+timedelta(minutes=5):raise ValueError("observed_at cannot be more than 5 minutes in the future")
        if normalized<now-timedelta(days=365):raise ValueError("observed_at is outside the accepted ingestion window")
        return normalized
class IngestionBatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    records:list[dict[str,Any]]=Field(min_length=1,max_length=100)
def _errors(error):return [{"field":".".join(str(p) for p in item["loc"]),"message":item["msg"]} for item in error.errors(include_url=False,include_context=False)]
@ingestion_router.post("/batch")
async def ingest_batch(batch:IngestionBatch,principal:dict=Depends(require_roles("admin","clinician")),x_source_token:str|None=Header(default=None,alias="X-Source-Token")):
    results=[];configured=os.getenv("VITALGUARD_LIVE_SOURCE_TOKEN","").strip()
    for index,raw in enumerate(batch.records):
        try:item=IngestionItem.model_validate(raw)
        except ValidationError as error:results.append({"index":index,"status":"rejected","errors":_errors(error)});continue
        require_patient_access(item.observation.patient_id,principal)
        if item.source_mode=="live" and (not configured or not x_source_token or not hmac.compare_digest(x_source_token,configured)):
            results.append({"index":index,"status":"rejected","errors":[{"field":"source_mode","message":"Authorized live source is not configured"}]});continue
        values=item.observation.model_dump(exclude={"patient_id"});probability=predict_probability(values);score=round(probability*100)
        prediction=RiskPrediction(patient_id=item.observation.patient_id,risk_score=score,risk_level=risk_level(score),model_probability=round(probability,4),factors=explain(values),model_version=MODEL_VERSION)
        payload_hash=hashlib.sha256(json.dumps(item.model_dump(mode="json"),sort_keys=True,separators=(",",":")).encode()).hexdigest()
        persisted=persist_ingested_observation(source_system=item.source_system,source_mode=item.source_mode,source_event_id=item.source_event_id,patient_id=item.observation.patient_id,observed_at=item.observed_at,units=item.units.model_dump(),payload_hash=payload_hash,inputs=values,prediction=prediction.model_dump())
        results.append({"index":index,**persisted,"source_system":item.source_system,"source_mode":item.source_mode,"source_event_id":item.source_event_id,"patient_id":item.observation.patient_id,"observed_at":item.observed_at.isoformat()})
        if persisted["status"]=="accepted":
            response=prediction.model_copy(update={"observation_id":persisted["observation_id"],"created_at":item.observed_at.isoformat()})
            await hub.broadcast({"type":"observation.created","event_id":persisted["observation_id"],"patient_id":item.observation.patient_id,"observed_at":item.observed_at.isoformat(),"observation":values,"prediction":response.model_dump(),"source_system":item.source_system,"source_mode":item.source_mode})
    accepted=sum(x["status"]=="accepted" for x in results);duplicates=sum(x["status"]=="duplicate" for x in results);conflicts=sum(x["status"]=="conflict" for x in results)
    return {"items":results,"count":len(results),"accepted":accepted,"duplicates":duplicates,"conflicts":conflicts,"rejected":len(results)-accepted-duplicates}
from .patient_routes import router as patient_router
router=APIRouter();router.include_router(ingestion_router);router.include_router(patient_router)