import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  Zap,
  BookOpen,
  Search,
  Play,
  CheckCircle,
  BarChart2,
  Globe,
  Bot,
} from 'lucide-react'
import { useUIStore } from '../store/uiStore'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/repos', label: 'Repos', icon: GitBranch },
  { to: '/capabilities', label: 'Capabilities', icon: Zap },
  { to: '/playbooks', label: 'Playbooks', icon: BookOpen },
  { to: '/query', label: 'Query', icon: Search },
  { to: '/execute', label: 'Execute', icon: Play },
  { to: '/approvals', label: 'Approvals', icon: CheckCircle },
  { to: '/feedback', label: 'Feedback', icon: BarChart2 },
  { to: '/knowledge', label: 'Knowledge', icon: Globe },
  { to: '/agents', label: 'Agents', icon: Bot },
]

export default function Sidebar() {
  const { sidebarOpen } = useUIStore()

  return (
    <aside
      className={`${
        sidebarOpen ? 'w-64' : 'w-16'
      } bg-slate-900 text-white transition-all duration-200 flex flex-col`}
    >
      <div className="h-16 flex items-center px-4 font-bold text-lg">
        {sidebarOpen ? 'Repo Intel' : 'RI'}
      </div>
      <nav className="flex-1 py-4 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `flex items-center px-4 py-2 hover:bg-slate-800 ${
                isActive ? 'bg-slate-800 border-r-4 border-blue-500' : ''
              }`
            }
          >
            <link.icon className="w-5 h-5" />
            {sidebarOpen && <span className="ml-3">{link.label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
