from fastapi import APIRouter, Query, Depends
from .storage import list_observations
from .trends import summarize_observation_trends
from .auth import authenticate_principal, require_patient_access

router = APIRouter(prefix="/api/v1/observations", tags=["observation-trends"], dependencies=[Depends(authenticate_principal)])

@router.get("/trends")
def observation_trends(patient_id: str = Query(min_length=1, max_length=64),
                       limit: int = Query(default=50, ge=2, le=100), principal: dict = Depends(authenticate_principal)):
    require_patient_access(patient_id, principal)
    """Summarize recent stored observations for one fictional patient."""
    records = list_observations(patient_id=patient_id, limit=limit)
    return summarize_observation_trends(patient_id, records)
