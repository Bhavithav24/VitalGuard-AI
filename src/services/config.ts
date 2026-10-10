export const APP_CONFIG = {
  demoMode: (import.meta.env.VITE_DEMO_MODE ?? 'true') !== 'false',
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000',
  version: (import.meta.env.VITE_APP_VERSION as string) || '0.1.0-demo',
  env: import.meta.env.MODE || 'development',
};
