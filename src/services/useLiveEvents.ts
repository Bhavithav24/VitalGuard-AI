import { useEffect, useState } from 'react';
import { createLiveSocket, type LiveEvent } from './liveEvents.ts';

export function useLiveEvents() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'offline'>('connecting');
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const [patientIds, setPatientIds] = useState<Set<string>>(() => new Set());

  useEffect(() => createLiveSocket((event) => {
    if (event.type === 'connected') {
      setLastEvent(event);
      return;
    }
    if (event.type === 'observation.created' || event.type === 'alert.created') {
      setLastEvent(event);
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

  return { status, lastEvent, eventCount: patientIds.size, patientCount: patientIds.size };
}
