"""Transactional observation ingestion persistence."""
from __future__ import annotations
import json
from sqlalchemy import insert,select
from sqlalchemy.exc import IntegrityError
from .ingestion_schema import ingestion_records
from .storage import _OBSERVATIONS,_engine
from .storage_schema import risk_assessments
def persist_ingested_observation(*,source_system,source_mode,source_event_id,patient_id,observed_at,units,payload_hash,inputs,prediction):
    engine=_engine()
    try:
        try:
            with engine.begin() as c:
                existing=c.execute(select(ingestion_records).where(ingestion_records.c.source_system==source_system,ingestion_records.c.source_event_id==source_event_id)).mappings().first()
                if existing:return {"status":"duplicate" if existing["payload_hash"]==payload_hash else "conflict","observation_id":existing["observation_id"],"ingestion_id":existing["id"]}
                result=c.execute(insert(_OBSERVATIONS).values(patient_id=patient_id,observed_at=observed_at,source_system=source_system,source_mode=source_mode,source_event_id=source_event_id,quality="accepted",input_json=json.dumps(inputs,separators=(",",":")),prediction_json=json.dumps(prediction,separators=(",",":")),model_version=prediction["model_version"]));oid=result.inserted_primary_key[0]
                c.execute(insert(risk_assessments).values(patient_id=patient_id,observation_id=oid,assessment_type="risk",risk_score=prediction["risk_score"],risk_level=prediction["risk_level"],model_version=prediction["model_version"],explanation_json=json.dumps(prediction.get("factors",[]),separators=(",",":"))))
                ir=c.execute(insert(ingestion_records).values(source_system=source_system,source_mode=source_mode,source_event_id=source_event_id,patient_id=patient_id,observed_at=observed_at,observation_id=oid,units_json=json.dumps(units,separators=(",",":"),sort_keys=True),quality="accepted",payload_hash=payload_hash))
                return {"status":"accepted","observation_id":oid,"ingestion_id":ir.inserted_primary_key[0]}
        except IntegrityError:
            with engine.connect() as c:existing=c.execute(select(ingestion_records).where(ingestion_records.c.source_system==source_system,ingestion_records.c.source_event_id==source_event_id)).mappings().first()
            if existing:return {"status":"duplicate" if existing["payload_hash"]==payload_hash else "conflict","observation_id":existing["observation_id"],"ingestion_id":existing["id"]}
            raise
    finally:engine.dispose()