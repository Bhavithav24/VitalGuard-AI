import { useEffect, useState } from 'react';
import { createLiveSocket, type LiveEvent } from './liveEvents.ts';

export function useLiveEvents() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'offline'>('connecting');
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const [eventCount, setEventCount] = useState(0);
  const [patientIds, setPatientIds] = useState<Set<string>>(() => new Set());

  useEffect(() => createLiveSocket((event) => {
    if (event.type === 'connected') {
      setLastEvent(event);
      return;
    }
    if (event.type === 'observation.created' || event.type === 'alert.created') {
      setLastEvent(event);
      setEventCount((count) => count + 1);
      if ('patient_id' in event && event.patient_id) {
        setPatientIds((current) => {
          if (current.has(event.patient_id)) return current;
          const next = new Set(current);
          next.add(event.patient_id);
          return next;
        });
      }
    }
  }, setStatus), []);

  return { status, lastEvent, eventCount, patientCount: patientIds.size };
}
