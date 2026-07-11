import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Repos from './pages/Repos'
import RepoDetail from './pages/RepoDetail'
import Capabilities from './pages/Capabilities'
import CapabilityDetail from './pages/CapabilityDetail'
import Playbooks from './pages/Playbooks'
import PlaybookDetail from './pages/PlaybookDetail'
import Query from './pages/Query'
import Execute from './pages/Execute'
import Approvals from './pages/Approvals'
import ApprovalDetail from './pages/ApprovalDetail'
import Feedback from './pages/Feedback'
import Knowledge from './pages/Knowledge'
import Agents from './pages/Agents'
import Login from './pages/Login'
import AuthCallback from './pages/AuthCallback'
import { useAuthStore } from './store/authStore'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.token)
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <Layout>{children}</Layout>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/repos" element={<ProtectedRoute><Repos /></ProtectedRoute>} />
      <Route path="/repos/:id" element={<ProtectedRoute><RepoDetail /></ProtectedRoute>} />
      <Route path="/capabilities" element={<ProtectedRoute><Capabilities /></ProtectedRoute>} />
      <Route path="/capabilities/:id" element={<ProtectedRoute><CapabilityDetail /></ProtectedRoute>} />
      <Route path="/playbooks" element={<ProtectedRoute><Playbooks /></ProtectedRoute>} />
      <Route path="/playbooks/:id" element={<ProtectedRoute><PlaybookDetail /></ProtectedRoute>} />
      <Route path="/query" element={<ProtectedRoute><Query /></ProtectedRoute>} />
      <Route path="/execute" element={<ProtectedRoute><Execute /></ProtectedRoute>} />
      <Route path="/approvals" element={<ProtectedRoute><Approvals /></ProtectedRoute>} />
      <Route path="/approvals/:id" element={<ProtectedRoute><ApprovalDetail /></ProtectedRoute>} />
      <Route path="/feedback" element={<ProtectedRoute><Feedback /></ProtectedRoute>} />
      <Route path="/knowledge" element={<ProtectedRoute><Knowledge /></ProtectedRoute>} />
      <Route path="/agents" element={<ProtectedRoute><Agents /></ProtectedRoute>} />
    </Routes>
  )
}

export default App
