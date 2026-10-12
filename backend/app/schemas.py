from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
class VitalInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    patient_id:str=Field(min_length=1,max_length=64);age:int=Field(ge=0,le=130);heart_rate:float=Field(ge=20,le=250);spo2:float=Field(ge=50,le=100);systolic_bp:float=Field(ge=50,le=280);diastolic_bp:float=Field(ge=20,le=180);temperature:float=Field(ge=30,le=45);respiratory_rate:float=Field(ge=3,le=70);consciousness:Literal["alert","new_confusion","voice","pain","unresponsive"]|None=None;supplemental_oxygen:bool=False;spo2_scale:Literal[1,2]=1;scale2_authorized:bool=False
    @model_validator(mode="after")
    def validate_blood_pressure(self):
        if self.diastolic_bp>=self.systolic_bp:raise ValueError("diastolic_bp must be lower than systolic_bp")
        return self
class RiskFactor(BaseModel):
    feature:str;observed_value:float;direction:Literal["increases-risk","decreases-risk"];explanation:str
class RiskPrediction(BaseModel):
    patient_id:str;observation_id:int|None=None;created_at:str|None=None
    risk_score:int|None=Field(default=None,ge=0,le=100)
    risk_level:Literal["low","moderate","high","critical","unavailable"]="unavailable"
    model_probability:float|None=Field(default=None,ge=0,le=1)
    factors:list[RiskFactor]=Field(default_factory=list)
    model_version:str
    news2:int|None=None
    demo_only:bool=False
    ml_available:bool=False
    disclaimer:str="Risk output is decision support only; it is not a diagnosis or treatment recommendation."
class NEWS2Input(BaseModel):
    model_config=ConfigDict(extra="forbid")
    patient_id:str=Field(min_length=1,max_length=64);respiratory_rate:int=Field(ge=1,le=100);spo2:int=Field(ge=50,le=100);systolic_bp:int=Field(ge=20,le=300);heart_rate:int=Field(ge=1,le=250);temperature:float=Field(ge=30,le=45);consciousness:Literal["alert","new_confusion","voice","pain","unresponsive"]="alert";supplemental_oxygen:bool=False;spo2_scale:Literal[1,2]=1;scale2_authorized:bool=False
    @model_validator(mode="after")
    def validate_scale_2_authorization(self):
        if self.spo2_scale==2 and not self.scale2_authorized:raise ValueError("SpO2 Scale 2 requires an explicit clinician-authorization assertion")
        return self