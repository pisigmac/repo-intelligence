import { Github } from 'lucide-react'

export default function Login() {
  const handleLogin = () => {
    window.location.href = `${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/github/login`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="max-w-md w-full p-8 bg-white rounded-xl shadow-lg border border-slate-100 text-center">
        <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <Github className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome to Repo Intel</h2>
        <p className="text-slate-600 mb-8">Sign in with GitHub to access the dashboard and orchestrate AI agents.</p>
        
        <button
          onClick={handleLogin}
          className="w-full flex items-center justify-center gap-3 bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 px-4 rounded-lg transition-colors"
        >
          <Github className="w-5 h-5" />
          Sign in with GitHub
        </button>
      </div>
    </div>
  )
}
