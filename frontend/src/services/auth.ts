import api from './api';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
  tenantSlug?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_id?: string;
  role: string;
}

export interface UserInfo {
  id: string;
  email: string;
  name?: string;
  tenantId?: string;
  role: string;
  isPlatformAdmin: boolean;
  createdAt: string;
  lastLogin?: string;
}

const TOKEN_KEY = 'auth_token';
const REFRESH_KEY = 'auth_refresh_token';

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/**
 * Try to refresh access token. Returns new token or null on failure.
 * Used by SSE fetch calls that bypass the Axios interceptor.
 */
export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken });
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

export const authService = {
  async login(request: LoginRequest): Promise<AuthResponse> {
    const { data } = await api.post('/auth/login', request);
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async register(request: RegisterRequest): Promise<AuthResponse> {
    const { data } = await api.post('/auth/register', {
      email: request.email,
      password: request.password,
      name: request.name,
      tenant_slug: request.tenantSlug,
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async refresh(): Promise<AuthResponse | null> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken });
      setTokens(data.access_token, data.refresh_token);
      return data;
    } catch {
      clearTokens();
      return null;
    }
  },

  async getMe(): Promise<UserInfo | null> {
    try {
      const { data } = await api.get('/auth/me');
      return {
        id: data.id,
        email: data.email,
        name: data.name,
        tenantId: data.tenant_id,
        role: data.role || 'member',
        isPlatformAdmin: data.is_platform_admin || false,
        createdAt: data.created_at,
        lastLogin: data.last_login,
      };
    } catch {
      return null;
    }
  },

  logout() {
    clearTokens();
  },

  isAuthenticated(): boolean {
    return !!getAuthToken();
  },
};
