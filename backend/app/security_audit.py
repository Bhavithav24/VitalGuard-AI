"""Best-effort security audit recording for the synthetic demo.

Security audit writes never block authentication or protected requests. The
audit table is append-only through application code: there are no update/delete
routes for audit events.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import insert

from .storage import _engine
from .storage_schema import audit_events


def record_security_event(action: str, actor: str = "anonymous", details: dict[str, Any] | None = None) -> None:
    engine = _engine()
    try:
        with engine.begin() as connection:
            connection.execute(insert(audit_events).values(
                entity_type="security",
                entity_id=actor[:160],
                action=action[:80],
                actor=actor[:120],
                details_json=json.dumps(details or {}, separators=(",", ":"), sort_keys=True),
            ))
    except Exception:
        return
    finally:
        engine.dispose()
