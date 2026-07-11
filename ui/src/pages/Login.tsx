import { useState } from 'react'
import { Github } from 'lucide-react'
import api from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const loginStore = useAuthStore((state) => state.login)
  const navigate = useNavigate()

  const handleGithubLogin = () => {
    window.location.href = `${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/github/login`
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isSignUp) {
        // Register
        await api.post('/auth/register', { email, password })
        // After register, automatically log in
      }
      
      // Login using OAuth2 form data as expected by FastAPI AuthRouter
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)
      
      const tokenRes = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      
      const token = tokenRes.data.access_token
      
      // Fetch user profile
      localStorage.setItem('ri_token', token)
      const userRes = await api.get('/auth/me')
      
      loginStore(token, userRes.data)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please try again.')
      localStorage.removeItem('ri_token')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="max-w-md w-full p-8 bg-white rounded-xl shadow-lg border border-slate-100 text-center">
        <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <Github className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome to Repo Intel</h2>
        <p className="text-slate-600 mb-8">Sign in or create an account to access the dashboard.</p>
        
        {error && <div className="mb-4 text-red-500 text-sm font-medium">{error}</div>}

        <form onSubmit={handleSubmit} className="mb-6 space-y-4 text-left">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Processing...' : isSignUp ? 'Sign Up' : 'Sign In'}
          </button>
        </form>

        <div className="flex items-center my-6">
          <div className="flex-grow border-t border-slate-200"></div>
          <span className="px-4 text-sm text-slate-500">or</span>
          <div className="flex-grow border-t border-slate-200"></div>
        </div>

        <button
          type="button"
          onClick={handleGithubLogin}
          className="w-full flex items-center justify-center gap-3 bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 px-4 rounded-lg transition-colors mb-4"
        >
          <Github className="w-5 h-5" />
          Continue with GitHub
        </button>

        <p className="text-sm text-slate-600">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button 
            type="button" 
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-blue-600 hover:underline font-medium"
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  )
}
