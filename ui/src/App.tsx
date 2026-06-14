import { Routes, Route } from 'react-router-dom'
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

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repos" element={<Repos />} />
        <Route path="/repos/:id" element={<RepoDetail />} />
        <Route path="/capabilities" element={<Capabilities />} />
        <Route path="/capabilities/:id" element={<CapabilityDetail />} />
        <Route path="/playbooks" element={<Playbooks />} />
        <Route path="/playbooks/:id" element={<PlaybookDetail />} />
        <Route path="/query" element={<Query />} />
        <Route path="/execute" element={<Execute />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/approvals/:id" element={<ApprovalDetail />} />
        <Route path="/feedback" element={<Feedback />} />
        <Route path="/knowledge" element={<Knowledge />} />
        <Route path="/agents" element={<Agents />} />
      </Routes>
    </Layout>
  )
}

export default App
