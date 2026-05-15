import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  userId: number | null
  name: string | null
  isAdmin: boolean
  login: (token: string, userId: number, name: string, isAdmin: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      name: null,
      isAdmin: false,
      login: (token, userId, name, isAdmin) => set({ token, userId, name, isAdmin }),
      logout: () => set({ token: null, userId: null, name: null, isAdmin: false }),
    }),
    { name: 'auth-storage' },
  ),
)
