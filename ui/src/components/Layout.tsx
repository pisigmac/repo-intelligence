import { ReactNode } from 'react'
import { Menu } from 'lucide-react'
import Sidebar from './Sidebar'
import { useUIStore } from '../store/uiStore'

export default function Layout({ children }: { children: ReactNode }) {
  const { toggleSidebar } = useUIStore()

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b flex items-center px-4">
          <button onClick={toggleSidebar} className="p-2 hover:bg-gray-100 rounded">
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="ml-4 text-lg font-semibold">Repo Intelligence Dashboard</h1>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}
