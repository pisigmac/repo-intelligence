import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import api from '../api/client'

export default function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      navigate('/login')
      return
    }

    // Set token temporarily to fetch user profile
    localStorage.setItem('ri_token', token)

    api.get('/auth/me')
      .then((res) => {
        login(token, res.data)
        navigate('/')
      })
      .catch(() => {
        localStorage.removeItem('ri_token')
        navigate('/login')
      })
  }, [searchParams, navigate, login])

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-slate-600 font-medium">Authenticating with GitHub...</p>
      </div>
    </div>
  )
}
