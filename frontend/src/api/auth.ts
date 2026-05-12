const API_BASE_URL = 'http://localhost:8000';

export type User = {
  id: number;
  name: string;
  email: string;
  work_role: string;
  created_at: string;
  updated_at: string;
};

export type ApiError = {
  detail?: string;
};

async function parseResponse<T>(response: Response): Promise<T> {
  const data = (await response.json()) as T | ApiError;

  if (!response.ok) {
    const message = (data as ApiError).detail ?? 'Request failed';
    throw new Error(message);
  }

  return data as T;
}

export async function signup(payload: { name: string; email: string; password: string; work_role: string }): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  return parseResponse<User>(response);
}

export async function login(payload: { email: string; password: string }): Promise<{ access_token: string; token_type: string; user: User }> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  return parseResponse<{ access_token: string; token_type: string; user: User }>(response);
}

export async function me(token: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  return parseResponse<User>(response);
}

export async function forgotPassword(payload: { email: string }): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  return parseResponse<{ message: string }>(response);
}
