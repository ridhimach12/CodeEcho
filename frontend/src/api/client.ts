export const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')

export function apiFetch(endpoint: string, options?: RequestInit): Promise<Response> {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const fullUrl = endpoint.startsWith('http') ? endpoint : `${API_BASE}${cleanEndpoint}`
  return fetch(fullUrl, options)
}
