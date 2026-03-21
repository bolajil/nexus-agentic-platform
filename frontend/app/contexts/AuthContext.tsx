'use client';
import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  id:    string;
  name:  string;
  email: string;
  role:  string;
}

interface AuthContextType {
  user:           User | null;
  loading:        boolean;
  login:          (email: string, password: string) => Promise<void>;
  register:       (name: string, email: string, password: string) => Promise<void>;
  logout:         () => void;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const API = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') ?? 'http://localhost:8003';

function setAuthCookie(value: string) {
  document.cookie = `nexus_logged_in=${value}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

function clearAuthCookie() {
  document.cookie = 'nexus_logged_in=; path=/; max-age=0';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]       = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Restore session on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('nexus_user');
      const token  = localStorage.getItem('nexus_access_token');
      if (stored && token) {
        setUser(JSON.parse(stored));
      }
    } catch {
      localStorage.removeItem('nexus_user');
      localStorage.removeItem('nexus_access_token');
      localStorage.removeItem('nexus_refresh_token');
    } finally {
      setLoading(false);
    }
  }, []);

  const _saveSession = (data: { access_token: string; refresh_token: string; user: User }) => {
    localStorage.setItem('nexus_access_token',  data.access_token);
    localStorage.setItem('nexus_refresh_token', data.refresh_token);
    localStorage.setItem('nexus_user',          JSON.stringify(data.user));
    setAuthCookie('1');
    setUser(data.user);
  };

  const _authFetch = async (path: string, body: object, token?: string) => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API}${path}`, {
      method: 'POST',
      headers,
      body:   JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? 'Request failed');
    return data;
  };

  const login = useCallback(async (email: string, password: string) => {
    const data = await _authFetch('/api/auth/login', { email, password });
    _saveSession(data);
    // If the account requires a password change on first login, redirect there
    if (data.force_password_change) {
      router.push('/change-password');
    } else {
      router.push('/');
    }
  }, [router]);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const data = await _authFetch('/api/auth/register', { name, email, password });
    _saveSession(data);
    router.push('/');
  }, [router]);

  const logout = useCallback(() => {
    const refresh = localStorage.getItem('nexus_refresh_token');
    if (refresh) {
      fetch(`${API}/api/auth/logout`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ refresh_token: refresh }),
      }).catch(() => {});
    }
    localStorage.removeItem('nexus_access_token');
    localStorage.removeItem('nexus_refresh_token');
    localStorage.removeItem('nexus_user');
    clearAuthCookie();
    setUser(null);
    router.push('/login');
  }, [router]);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const token = localStorage.getItem('nexus_access_token');
    await _authFetch(
      '/api/auth/change-password',
      { current_password: currentPassword, new_password: newPassword },
      token ?? undefined,
    );
    router.push('/');
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, changePassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
