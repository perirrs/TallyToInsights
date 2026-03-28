import axios from 'axios'
import { useAuthStore } from '../store/authStore'

// Priority order:
//  1. VITE_API_URL set at build time (GitHub Pages pointing at Render backend)
//  2. file:// protocol  → packaged Electron  → localhost:8000
//  3. http(s)://         → dev proxy or same-origin (Electron dev)
const baseURL =
  import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api`
    : typeof window !== 'undefined' && window.location.protocol === 'file:'
    ? 'http://127.0.0.1:8000/api'
    : '/api'

const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default api
