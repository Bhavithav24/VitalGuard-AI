import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { APP_CONFIG } from '../services/config.ts';

export type UserRole = 'admin' | 'operator' | 'viewer';
type AuthState = { token: string; username: string; role: UserRole; expiresAt: number };
type AuthContextValue = {
  token: string | null;
  username: string | null;
  role: UserRole | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};
const STORAGE_KEY = 'vitalguard.operator.session';
const AuthContext = createContext<AuthContextValue | null>(null);

function readSession(): AuthState | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<AuthState>;
    if (!value.token || !value.username || !value.role || !value.expiresAt || value.expiresAt <= Date.now()) {
      sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
    if (!['admin', 'operator', 'viewer'].includes(value.role)) {
      sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return value as AuthState;
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthState | null>(() => readSession());

  const logout = useCallback(() => {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
    setSession(null);
    if (!raw) return;
    try {
      const saved = JSON.parse(raw) as { token?: string };
      if (saved.token) {
        void fetch(`${APP_CONFIG.apiBaseUrl}/api/v1/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${saved.token}` },
          keepalive: true,
        }).catch(() => undefined);
      }
    } catch { /* local logout already completed */ }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const response = await fetch(`${APP_CONFIG.apiBaseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) {
      if (response.status === 429) throw new Error('Too many login attempts. Please wait a minute and try again.');
      if (response.status === 503) throw new Error('Authentication is not configured on the server.');
      if (response.status === 401) throw new Error('Incorrect username or password.');
      throw new Error(`Login failed (${response.status}). Please try again.`);
    }

    const result = await response.json() as { access_token: string; expires_in: number; role: UserRole };
    if (!result.access_token || !result.role || !['admin', 'operator', 'viewer'].includes(result.role)) {
      throw new Error('The server returned an invalid authentication response.');
    }

    const next: AuthState = {
      token: result.access_token,
      username: username.trim(),
      role: result.role,
      expiresAt: Date.now() + result.expires_in * 1000,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const value = useMemo(() => {
    const active = session && session.expiresAt > Date.now() ? session : null;
    return {
      token: active?.token ?? null,
      username: active?.username ?? null,
      role: active?.role ?? null,
      login,
      logout,
    };
  }, [session, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}

export function useOptionalAuth() {
  return useContext(AuthContext);
}
