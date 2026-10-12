import {useCallback,useEffect,useMemo,useState,type ReactNode} from 'react';
import {SimCtx} from './simInit.ts';
import type {Patient,RiskSignal,VitalReading,AlertItem} from '../types/index.ts';
import {api} from '../services/api.ts';
import {useLiveEvents} from '../services/useLiveEvents.ts';

function build(ps:any[],os:any[],as:any[]){
  const patients:Patient[]=ps.map(p=>({id:p.patient_id,age:Number(p.age??0),sex:p.sex==='F'?'F':p.sex==='M'?'M':'U',ward:p.unit||'Unassigned',bed:p.bed||'—',updatedAt:p.updated_at||p.created_at||new Date().toISOString()}));
  const histories:Record<string,VitalReading[]>={},latest:Record<string,VitalReading>={},risks:Record<string,RiskSignal>={},groups:Record<string,any[]>={};
  patients.forEach(p=>histories[p.id]=[]);
  const patientIds=new Set(patients.map(p=>p.id));
  os.filter(o=>patientIds.has(o.patient_id)).forEach(o=>(groups[o.patient_id]??=[]).push(o));
  patients.forEach(p=>{
    const rows=(groups[p.id]??[]).slice().sort((a,b)=>new Date(a.observed_at||a.created_at).getTime()-new Date(b.observed_at||b.created_at).getTime());
    const vs=rows.map(o=>({patientId:p.id,timestamp:o.observed_at||o.created_at,heartRate:Number(o.inputs?.heart_rate),spo2:Number(o.inputs?.spo2),systolicBp:Number(o.inputs?.systolic_bp),diastolicBp:Number(o.inputs?.diastolic_bp),temperature:Number(o.inputs?.temperature),respiratoryRate:Number(o.inputs?.respiratory_rate)})).filter(v=>Number.isFinite(v.heartRate));
    histories[p.id]=vs.slice(-40);
    const last=vs[vs.length-1];
    if(last)latest[p.id]=last;
    const lastRow=rows[rows.length-1];
    if(!lastRow) return;
    const score=Number.isFinite(Number(lastRow.prediction?.risk_score))?Number(lastRow.prediction.risk_score):null;
    const scores=rows.map(o=>Number(o.prediction?.risk_score)).filter(Number.isFinite);
    const trend=scores.length<2?'stable':(scores[scores.length-1]-scores[0]>=5?'worsening':scores[scores.length-1]-scores[0]<=-5?'recovering':'stable');
    risks[p.id]={
      patientId:p.id,
      score,
      level:score===null?'unavailable':score>=85?'critical':score>=65?'high':score>=30?'moderate':'low',
      probability:Number.isFinite(Number(lastRow.prediction?.model_probability))?Number(lastRow.prediction.model_probability):null,
      news2:Number.isFinite(Number(lastRow.prediction?.news2))?Number(lastRow.prediction.news2):null,
      trend,
      trajectory:scores.slice(-12),
      trajectoryLabels:rows.filter(o=>Number.isFinite(Number(o.prediction?.risk_score))).slice(-12).map(o=>new Date(o.observed_at||o.created_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})),
      updatedAt:last.timestamp||p.updatedAt,
      sourceMode:lastRow.source_mode==='historical_replay'?'historical_replay':lastRow.source_mode==='live'?'live':'unknown',
      mlAvailable:lastRow.prediction?.ml_available===true,
      demoOnly:lastRow.prediction?.demo_only===true,
      disclaimer:lastRow.prediction?.disclaimer,
      factors:Array.isArray(lastRow.prediction?.factors)?lastRow.prediction.factors.map((f:any)=>({feature:String(f.feature||'unknown'),observedValue:Number(f.observed_value??0),direction:f.direction==='decreases-risk'?'decreases-risk':'increases-risk',explanation:String(f.explanation||'')})):[]
    };
  });
  const alerts=as.filter(a=>patientIds.has(a.patient_id)).map(a=>({id:String(a.id),patientId:a.patient_id,severity:a.severity||'info',title:a.title,description:a.details?.description||a.details?.message||a.title,contributors:Array.isArray(a.details?.contributors)?a.details.contributors:[],status:a.status,createdAt:a.created_at})) as AlertItem[];
  return {patients,latest,risks,histories,alerts};
}
export function SimulationProvider({children}:{children:ReactNode}){
  const [state,setState]=useState(()=>({patients:[],latest:{},risks:{},histories:{},alerts:[]} as ReturnType<typeof build>));
  const [lastRefresh,setLastRefresh]=useState(new Date().toISOString());
  const [theme,setThemeState]=useState<'light'|'dark'>(()=>(localStorage.getItem('vg-theme') as any)||'light');
  const {eventCount,status}=useLiveEvents();
  const load=useCallback(async()=>{try{const[p,o,a]=await Promise.all([api.listPatients(),api.listObservations(undefined,100),api.listAlerts()]);setState(build(p as any[],o.items as any[],a.items as any[]));setLastRefresh(new Date().toISOString())}catch{}},[]);
  useEffect(()=>{void load()},[load]);
  useEffect(()=>{if(eventCount)void load()},[eventCount,load]);
  useEffect(()=>{if(status==='connected')void load()},[status,load]);
  useEffect(()=>{document.documentElement.classList.toggle('dark',theme==='dark')},[theme]);
  const setTheme=useCallback((t:'light'|'dark')=>{setThemeState(t);localStorage.setItem('vg-theme',t)},[]);
  const acknowledge=useCallback((id:string)=>{void api.acknowledgeAlert(id).then(load).catch(()=>undefined)},[load]);
  const value=useMemo(()=>({...state,streamStatus:status,toasts:[],running:false,tick:0,speed:'normal' as const,multiplier:1 as const,lastRefresh,start:()=>undefined,pause:()=>undefined,reset:()=>void load(),refresh:()=>void load(),dismissToast:()=>undefined,setSpeed:()=>undefined,setMultiplier:()=>undefined,acknowledge,undoAcknowledge:()=>undefined,dataSource:'api' as const,setDataSource:()=>undefined,theme,setTheme}),[state,status,lastRefresh,load,acknowledge,theme,setTheme]);
  return <SimCtx.Provider value={value}>{children}</SimCtx.Provider>;
}
