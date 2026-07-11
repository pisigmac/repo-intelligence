import { create } from 'zustand'

export interface User {
  sub: string
  name: string | null
  avatar_url: string | null
  exp: number
}

interface AuthState {
  token: string | null
  user: User | null
  login: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('ri_token') || null,
  user: localStorage.getItem('ri_user') ? JSON.parse(localStorage.getItem('ri_user') as string) : null,
  login: (token, user) => {
    localStorage.setItem('ri_token', token)
    localStorage.setItem('ri_user', JSON.stringify(user))
    set({ token, user })
  },
  logout: () => {
    localStorage.removeItem('ri_token')
    localStorage.removeItem('ri_user')
    set({ token: null, user: null })
  },
}))
