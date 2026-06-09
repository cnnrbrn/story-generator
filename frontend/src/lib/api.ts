// Base URL for the FastAPI backend. Vite exposes env vars prefixed with VITE_
// on import.meta.env (its equivalent of process.env). Falls back to localhost.
export const API_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Thin fetch wrapper: prefixes the API base and throws on non-2xx responses.
export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`)
  }
  return res.json() as Promise<T>
}
