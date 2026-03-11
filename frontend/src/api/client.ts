const API_BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export interface User {
  id: number
  display_name: string
  avatar_url: string | null
  is_admin: boolean
  is_active: boolean
  onboarding_completed: boolean
  created_at: string | null
}

export interface UserProfile {
  id: number
  display_name: string
  avatar_url: string | null
  is_admin: boolean
  onboarding_completed: boolean
  hidden_gem_openness: number
  darkness_tolerance: number
  min_quality_threshold: number
  preferred_runtime_max: number | null
  trakt_connected: boolean
  genre_preferences: { genre_id: number; genre_name: string; preference: string }[]
  watch_history_count: number
  watchlist_count: number
}

export const api = {
  getUsers: () => request<User[]>('/users'),

  createUser: (data: { display_name: string; avatar_url?: string; is_admin?: boolean }) =>
    request<User>('/users', { method: 'POST', body: JSON.stringify(data) }),

  updateUser: (id: number, data: Partial<User>) =>
    request<User>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  selectUser: (id: number) =>
    request<User>(`/users/${id}/select`, { method: 'POST' }),

  getProfile: (id: number) =>
    request<UserProfile>(`/users/${id}/profile`),

  healthCheck: () => request<{ status: string }>('/health'),
}
