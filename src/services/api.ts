import { APP_CONFIG } from './config.ts';
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${APP_CONFIG.apiBaseUrl}${path}`, { signal: AbortSignal.timeout(4000) });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<T>;
}
export const api = {
  listPatients: () => get('/api/v1/patients'),
  getPatient: (id: string) => get(`/api/v1/patients/${id}`),
  getVitals: (id: string) => get(`/api/v1/patients/${id}/vitals`),
  getLatestVitals: (id: string) => get(`/api/v1/patients/${id}/vitals/latest`),
};
