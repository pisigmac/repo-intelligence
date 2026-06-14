import { ReactNode } from 'react'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-slate-900 text-white p-4">Sidebar</aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  )
}
