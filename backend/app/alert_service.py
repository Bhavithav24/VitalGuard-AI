"""Server-authoritative alert lifecycle and audit persistence."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from sqlalchemy import desc,insert,or_,select,update
from sqlalchemy.exc import IntegrityError
from .storage import _engine
from .storage_schema import alerts,audit_events
def _serialize(row):
    item=dict(row)
    for k in ("created_at","acknowledged_at","assigned_at","resolved_at"):
        if item.get(k) is not None and hasattr(item[k],"isoformat"):item[k]=item[k].isoformat()
    item["details"]=json.loads(item.pop("details_json"));return item
def _audit(c,eid,action,actor,details):c.execute(insert(audit_events).values(entity_type="alert",entity_id=str(eid),action=action,actor=actor,details_json=json.dumps(details or {},separators=(",",":"))))
def create_alert(*,patient_id,event_key,severity,title,details):
    engine=_engine()
    try:
        with engine.begin() as c:
            existing=c.execute(select(alerts).where(alerts.c.event_key==event_key)).mappings().first()
            if existing:return _serialize(existing)
            r=c.execute(insert(alerts).values(patient_id=patient_id,event_key=event_key,severity=severity,status="open",title=title,details_json=json.dumps(details,separators=(",",":"))));row=c.execute(select(alerts).where(alerts.c.id==r.inserted_primary_key[0])).mappings().one();_audit(c,row["id"],"created","system",{"severity":severity});return _serialize(row)
    except IntegrityError:
        with engine.connect() as c:row=c.execute(select(alerts).where(alerts.c.event_key==event_key)).mappings().first()
        return _serialize(row) if row else None
    finally:engine.dispose()
def list_alerts(status=None,patient_id=None,limit=50,patient_prefixes=None):
    engine=_engine()
    try:
        q=select(alerts)
        if status:q=q.where(alerts.c.status==status)
        if patient_id:q=q.where(alerts.c.patient_id==patient_id)
        elif patient_prefixes is not None:
            if not patient_prefixes:return []
            q=q.where(or_(*[alerts.c.patient_id.startswith(p,autoescape=True) for p in patient_prefixes]))
        with engine.connect() as c:return [_serialize(r) for r in c.execute(q.order_by(desc(alerts.c.id)).limit(limit)).mappings().all()]
    finally:engine.dispose()
def get_alert(alert_id):
    engine=_engine()
    try:
        with engine.connect() as c:r=c.execute(select(alerts).where(alerts.c.id==alert_id)).mappings().first()
        return _serialize(r) if r else None
    finally:engine.dispose()
def transition_alert(alert_id,action,actor,assignee=None):
    transitions={"acknowledge":("open","acknowledged"),"assign":("acknowledged","assigned"),"resolve":("assigned","resolved")}
    if action not in transitions:raise ValueError("Unsupported alert action")
    old,new=transitions[action];now=datetime.now(timezone.utc);engine=_engine()
    try:
        with engine.begin() as c:
            row=c.execute(select(alerts).where(alerts.c.id==alert_id)).mappings().first()
            if not row:return None
            if row["status"]!=old:return _serialize(row)
            values={"status":new}
            if action=="acknowledge":values.update(acknowledged_by=actor,acknowledged_at=now)
            elif action=="assign":values.update(assigned_to=assignee or actor,assigned_at=now)
            else:values.update(resolved_by=actor,resolved_at=now)
            c.execute(update(alerts).where(alerts.c.id==alert_id).values(**values));_audit(c,alert_id,action,actor,{"assigned_to":assignee} if action=="assign" else {})
            return _serialize(c.execute(select(alerts).where(alerts.c.id==alert_id)).mappings().one())
    finally:engine.dispose()
def list_alert_audit(alert_id):
    engine=_engine()
    try:
        with engine.connect() as c:rows=c.execute(select(audit_events).where(audit_events.c.entity_type=="alert",audit_events.c.entity_id==str(alert_id)).order_by(audit_events.c.id)).mappings().all()
        out=[]
        for r in rows:
            x=dict(r);x["details"]=json.loads(x.pop("details_json"));x["created_at"]=x["created_at"].isoformat();out.append(x)
        return out
    finally:engine.dispose()