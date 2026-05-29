import { APIError } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Get token from localStorage
function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

// Set token in localStorage
export function setToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('auth_token', token);
  }
}

// Clear token
export function clearToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
}

// Base fetch wrapper with auth
async function apiFetch(
  endpoint: string,
  options: Omit<RequestInit, 'headers'> & { headers?: Record<string, string> } = {}
): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }

  const url = `${API_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  return response;
}

// Helper to parse response
async function handleResponse<T>(response: Response): Promise<T | APIError> {
  if (!response.ok) {
    const error: APIError = {};
    try {
      const data = await response.json();
      return data as APIError;
    } catch {
      error.error = `HTTP ${response.status}: ${response.statusText}`;
      return error;
    }
  }

  try {
    return (await response.json()) as T;
  } catch {
    return {} as T;
  }
}

// GET request
export async function get<T>(endpoint: string): Promise<T | APIError> {
  const response = await apiFetch(endpoint, {
    method: 'GET',
  });
  return handleResponse<T>(response);
}

// POST request
export async function post<T>(
  endpoint: string,
  data?: Record<string, any>
): Promise<T | APIError> {
  const response = await apiFetch(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
  return handleResponse<T>(response);
}

// POST with FormData (for file uploads)
export async function postForm<T>(
  endpoint: string,
  formData: FormData
): Promise<T | APIError> {
  const token = getToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }

  const url = `${API_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });

  return handleResponse<T>(response);
}

// PATCH request
export async function patch<T>(
  endpoint: string,
  data?: Record<string, any>
): Promise<T | APIError> {
  const response = await apiFetch(endpoint, {
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  });
  return handleResponse<T>(response);
}

// PUT request
export async function put<T>(
  endpoint: string,
  data?: Record<string, any>
): Promise<T | APIError> {
  const response = await apiFetch(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
  return handleResponse<T>(response);
}

// DELETE request
export async function del<T>(endpoint: string): Promise<T | APIError> {
  const response = await apiFetch(endpoint, {
    method: 'DELETE',
  });
  return handleResponse<T>(response);
}

// Auth helpers
export async function login(email: string, password: string): Promise<string | APIError> {
  // api-token-auth is NOT under /api/, so use absolute URL
  const response = await fetch(`${API_URL.replace('/api', '')}/api-token-auth/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: email, password }),
  });

  if (!response.ok) {
    return { error: 'Invalid credentials' };
  }

  const data = (await response.json()) as { token: string };
  setToken(data.token);
  return data.token;
}

export function logout(): void {
  clearToken();
}

export function isLoggedIn(): boolean {
  return !!getToken();
}
