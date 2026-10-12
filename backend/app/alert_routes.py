"""Server-authoritative alert workflow endpoints."""
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,ConfigDict,Field
from .alert_service import get_alert,list_alerts,list_alert_audit,transition_alert
from .auth import authenticate_principal,patient_scope_prefixes,require_roles,require_patient_access
router=APIRouter(prefix="/api/v1/alerts",tags=["alerts"],dependencies=[Depends(authenticate_principal)])
class AlertAction(BaseModel):
    model_config=ConfigDict(extra="forbid")
    actor:str=Field(default="current-user",min_length=1,max_length=120)
@router.get("")
def get_alerts(status:Literal["open","acknowledged","assigned","resolved"]|None=None,patient_id:str|None=Query(default=None,min_length=1,max_length=64),limit:int=Query(default=50,ge=1,le=100),principal:dict=Depends(authenticate_principal)):
    if patient_id:require_patient_access(patient_id,principal)
    items=list_alerts(status=status,patient_id=patient_id,limit=limit,patient_prefixes=patient_scope_prefixes(principal));return {"items":items,"count":len(items)}
@router.get("/escalation-preview")
def escalation_preview(principal:dict=Depends(authenticate_principal)):
    """Return active alerts ranked for review using server-side priority rules."""
    items=list_alerts(limit=100,patient_prefixes=patient_scope_prefixes(principal))
    active=[item for item in items if item["status"] in {"open","acknowledged","assigned"}]
    severity={"critical":4,"high":3,"medium":2,"low":1,"info":0}
    status={"open":3,"acknowledged":2,"assigned":1}
    active.sort(key=lambda item:(severity.get(item.get("severity","info"),0),status.get(item.get("status","open"),0),item.get("created_at","")),reverse=True)
    return {"items":[{"alert_id":item["id"],"patient_id":item["patient_id"],"severity":item["severity"],"status":item["status"],"title":item["title"]} for item in active]}

@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id:int,payload:AlertAction,principal:dict=Depends(require_roles("admin","clinician","nurse"))):
    alert=get_alert(alert_id)
    if alert is None:raise HTTPException(status_code=404,detail="Alert not found")
    require_patient_access(alert["patient_id"],principal);return {"item":transition_alert(alert_id,"acknowledge",principal["sub"])}
@router.post("/{alert_id}/assign")
def assign_alert(alert_id:int,payload:AlertAction,principal:dict=Depends(require_roles("admin","clinician","nurse"))):
    alert=get_alert(alert_id)
    if alert is None:raise HTTPException(status_code=404,detail="Alert not found")
    require_patient_access(alert["patient_id"],principal);return {"item":transition_alert(alert_id,"assign",principal["sub"],payload.actor)}
@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id:int,payload:AlertAction,principal:dict=Depends(require_roles("admin","clinician","nurse"))):
    alert=get_alert(alert_id)
    if alert is None:raise HTTPException(status_code=404,detail="Alert not found")
    require_patient_access(alert["patient_id"],principal);return {"item":transition_alert(alert_id,"resolve",principal["sub"])}
@router.get("/{alert_id}/audit")
def get_alert_audit(alert_id:int,principal:dict=Depends(authenticate_principal)):
    alert=get_alert(alert_id)
    if alert is None:raise HTTPException(status_code=404,detail="Alert not found")
    require_patient_access(alert["patient_id"],principal);items=list_alert_audit(alert_id);return {"items":items,"count":len(items)}