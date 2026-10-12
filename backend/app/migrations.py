"""Ordered, idempotent database migrations."""
from sqlalchemy import Column,DateTime,Integer,MetaData,Table,func,insert,inspect,select,text
from sqlalchemy.engine import Engine
from .storage import _METADATA
from .storage_schema import metadata as _EXTENDED_METADATA
from .ingestion_schema import metadata as _INGESTION_METADATA
_MIGRATION_METADATA=MetaData();MIGRATIONS=Table("schema_migrations",_MIGRATION_METADATA,Column("version",Integer,primary_key=True),Column("applied_at",DateTime(timezone=True),nullable=False,server_default=func.now()));LATEST_VERSION=6
def _applied_versions(engine:Engine):
    with engine.connect() as c:return set(c.execute(select(MIGRATIONS.c.version)).scalars())
def _record_version(engine,version):
    with engine.begin() as c:c.execute(insert(MIGRATIONS).values(version=version))
def migrate(engine:Engine):
    _MIGRATION_METADATA.create_all(engine);_METADATA.create_all(engine);_EXTENDED_METADATA.create_all(engine);_INGESTION_METADATA.create_all(engine)
    applied=_applied_versions(engine)
    if 1 not in applied:_record_version(engine,1)
    applied=_applied_versions(engine)
    if 2 not in applied:
        with engine.begin() as c:c.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_patient_status_created ON alerts (patient_id,status,created_at DESC)"))
        _record_version(engine,2)
    applied=_applied_versions(engine)
    if 3 not in applied:_record_version(engine,3)
    applied=_applied_versions(engine)
    if 4 not in applied:
        inspector=inspect(engine);existing={x["name"] for x in inspector.get_columns("patients")}
        with engine.begin() as c:
            for name,sql in {"external_identifier":"ALTER TABLE patients ADD COLUMN external_identifier VARCHAR(128)","age":"ALTER TABLE patients ADD COLUMN age INTEGER","sex":"ALTER TABLE patients ADD COLUMN sex VARCHAR(32)","bed":"ALTER TABLE patients ADD COLUMN bed VARCHAR(40)","active":"ALTER TABLE patients ADD COLUMN active BOOLEAN DEFAULT TRUE","deactivated_at":"ALTER TABLE patients ADD COLUMN deactivated_at TIMESTAMP"}.items():
                if name not in existing:c.execute(text(sql))
            c.execute(text("UPDATE patients SET external_identifier = patient_id WHERE external_identifier IS NULL"));c.execute(text("UPDATE patients SET active = TRUE WHERE active IS NULL"));c.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_patients_external_identifier_idx ON patients (external_identifier)"))
        _record_version(engine,4)
    applied=_applied_versions(engine)
    if 5 not in applied:
        inspector=inspect(engine);eo={x["name"] for x in inspector.get_columns("observations")};ei={x["name"] for x in inspector.get_columns("ingestion_records")};ea={x["name"] for x in inspector.get_columns("alerts")}
        with engine.begin() as c:
            for name,sql in {"observed_at":"ALTER TABLE observations ADD COLUMN observed_at TIMESTAMP","source_system":"ALTER TABLE observations ADD COLUMN source_system VARCHAR(80)","source_mode":"ALTER TABLE observations ADD COLUMN source_mode VARCHAR(32)","source_event_id":"ALTER TABLE observations ADD COLUMN source_event_id VARCHAR(128)","quality":"ALTER TABLE observations ADD COLUMN quality VARCHAR(32)"}.items():
                if name not in eo:c.execute(text(sql))
            if "source_mode" not in ei:c.execute(text("ALTER TABLE ingestion_records ADD COLUMN source_mode VARCHAR(32) DEFAULT 'live'"))
            if "quality" not in ei:c.execute(text("ALTER TABLE ingestion_records ADD COLUMN quality VARCHAR(32) DEFAULT 'accepted'"))
            if "assigned_to" not in ea:c.execute(text("ALTER TABLE alerts ADD COLUMN assigned_to VARCHAR(120)"))
            if "assigned_at" not in ea:c.execute(text("ALTER TABLE alerts ADD COLUMN assigned_at TIMESTAMP"))
            if "resolved_by" not in ea:c.execute(text("ALTER TABLE alerts ADD COLUMN resolved_by VARCHAR(120)"))
        _record_version(engine,5)
    applied=_applied_versions(engine)
    if 6 not in applied:_EXTENDED_METADATA.create_all(engine);_INGESTION_METADATA.create_all(engine);_record_version(engine,6)
    applied=_applied_versions(engine);expected=set(range(1,LATEST_VERSION+1))
    if not expected.issubset(applied):raise RuntimeError(f"Database migrations incomplete: expected {sorted(expected)}, found {sorted(applied)}")