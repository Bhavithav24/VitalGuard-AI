"""Additional durable tables for the synthetic VitalGuard demo."""
from sqlalchemy import (
    Column, DateTime, Index, Integer, MetaData, String, Table, Text, func,
)

metadata = MetaData()

patients = Table(
    "patients", metadata,
    Column("patient_id", String(64), primary_key=True),
    Column("external_identifier", String(128), nullable=True),
    Column("display_name", String(120), nullable=False),
    Column("age", Integer, nullable=True),
    Column("sex", String(32), nullable=True),
    Column("unit", String(80), nullable=False, server_default="Demo Ward"),
    Column("bed", String(40), nullable=True),
    Column("active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    Column("deactivated_at", DateTime(timezone=True)),
    UniqueConstraint("external_identifier", name="uq_patients_external_identifier"),
)
Index("idx_patients_active_unit", patients.c.active, patients.c.unit)
Index("idx_patients_updated", patients.c.updated_at.desc())

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(128), nullable=False, unique=True),
    Column("password_hash", String(512), nullable=False),
    Column("role", String(32), nullable=False),
    Column("enabled", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
)
Index("idx_users_enabled_role", users.c.enabled, users.c.role)

