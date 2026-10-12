import { APP_CONFIG } from './config.ts';
import { getOperatorAccessToken, authorizedFetch } from './authenticatedFetch.ts';

export interface LiveObservationEvent {
  type: 'observation.created';
  event_id: number;
  patient_id: string;
  observed_at?: string;
  created_at?: string;
  observation: Record<string, number>;
  prediction: {
    risk_score: number | null;
    risk_level: string;
    model_probability: number | null;
    model_version?: string;
    ml_available?: boolean;
    demo_only?: boolean;
    news2?: number | null;
    disclaimer?: string;
  };
  source_system?: string;
  source_mode?: 'live' | 'historical_replay';
}
export interface LiveAlertEvent {
  type: 'alert.created';
  event_id: number;
  alert: { id: number; patient_id: string; title: string; severity: string; status: string; created_at: string };
  demo_only?: boolean;
  source_mode?: 'live' | 'historical_replay';
}
export type LiveEvent = LiveObservationEvent | LiveAlertEvent | { type: 'connected' | 'pong'; demo_only?: boolean; transport?: string };

export function createLiveSocket(onEvent: (event: LiveEvent) => void, onStatus: (status: 'connecting' | 'connected' | 'reconnecting' | 'offline') => void) {
  let socket: WebSocket | null = null;
  let stopped = false;
  let retry = 0;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let heartbeat: ReturnType<typeof setInterval> | undefined;

  const connect = async () => {
    if (stopped) return;
    onStatus(retry === 0 ? 'connecting' : 'reconnecting');
    const base = APP_CONFIG.apiBaseUrl;
    const wsBase = base.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
    try {
      const token = getOperatorAccessToken();
      if (!token) { onStatus('offline'); return; }
      const ticketResponse = await authorizedFetch(base + '/api/v1/auth/ws-ticket', {method:'POST',signal:AbortSignal.timeout(8000)});
      if (!ticketResponse.ok) { if(ticketResponse.status===401){onStatus('offline');return;} throw new Error('WebSocket ticket request failed'); }
      const {ticket}=await ticketResponse.json() as {ticket?:string};
      if(!ticket)throw new Error('WebSocket ticket missing');
      socket=new WebSocket(wsBase + '/api/v1/live?ticket=' + encodeURIComponent(ticket));
    } catch { scheduleRetry(); return; }
    socket.onopen=()=>{retry=0;onStatus('connected');heartbeat=setInterval(()=>{if(socket?.readyState===WebSocket.OPEN)socket.send('ping')},25000)};
    socket.onmessage=(message)=>{try{onEvent(JSON.parse(String(message.data)) as LiveEvent)}catch{}};
    socket.onerror=()=>socket?.close();
    socket.onclose=()=>{if(heartbeat)clearInterval(heartbeat);heartbeat=undefined;if(!stopped)scheduleRetry()};
  };
  const scheduleRetry=()=>{if(stopped)return;retry+=1;onStatus(retry>5?'offline':'reconnecting');const delay=Math.min(30000,1000*2**Math.min(retry-1,5));retryTimer=setTimeout(connect,delay)};
  connect();
  return ()=>{stopped=true;if(retryTimer)clearTimeout(retryTimer);if(heartbeat)clearInterval(heartbeat);socket?.close()};
}
