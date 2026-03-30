import axios from 'axios'
import { useAuthStore } from '../store/authStore'

// Priority:
//  1. VITE_API_URL at build time  → GitHub Pages pointing at Railway backend
//  2. file:// protocol            → packaged Electron → localhost:8000
//  3. otherwise                   → Vite dev proxy at /api
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
      window.location.href = `${import.meta.env.BASE_URL}login`
    }
    return Promise.reject(err)
  },
)

export default api
