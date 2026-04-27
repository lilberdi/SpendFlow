import axios from 'axios'

/**
 * Local dev: FastAPI on port 8000.
 * Production (Docker nginx): same origin — use `/api/v1` relative to the page host.
 */
function resolveApiBase(): string {
  if (import.meta.env.VITE_API_BASE) {
    return String(import.meta.env.VITE_API_BASE).replace(/\/$/, '')
  }
  if (import.meta.env.DEV) {
    return 'http://localhost:8000/api/v1'
  }
  return `${window.location.origin}/api/v1`
}

export const axiosInstance = axios.create({
  baseURL: resolveApiBase(),
  timeout: 30_000,
  headers: { Accept: 'application/json' },
})
