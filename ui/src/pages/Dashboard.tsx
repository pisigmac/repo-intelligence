import { useCapabilities } from '../hooks/useCapabilities'
import { usePlaybooks } from '../hooks/usePlaybooks'
import { useApprovals } from '../hooks/useApprovals'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import { GitBranch, Zap, BookOpen, CheckCircle } from 'lucide-react'

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType
  label: string
  value: number
}) {
  return (
    <div className="bg-white p-6 rounded-lg shadow border">
      <div className="flex items-center">
        <div className="p-3 bg-blue-50 rounded-lg">
          <Icon className="w-6 h-6 text-blue-600" />
        </div>
        <div className="ml-4">
          <p className="text-sm text-gray-600">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: capabilities, isLoading: capLoading, error: capError } = useCapabilities()
  const { data: playbooks, isLoading: pbLoading, error: pbError } = usePlaybooks()
  const { data: approvals, isLoading: appLoading, error: appError } = useApprovals()

  if (capLoading || pbLoading || appLoading) return <LoadingState />
  if (capError || pbError || appError)
    return <ErrorState error={(capError || pbError || appError) as Error} />

  const pending = approvals?.filter((a) => a.status === 'pending').length || 0

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard icon={GitBranch} label="Repos" value={0} />
        <StatCard icon={Zap} label="Capabilities" value={capabilities?.length || 0} />
        <StatCard icon={BookOpen} label="Playbooks" value={playbooks?.length || 0} />
        <StatCard icon={CheckCircle} label="Pending Approvals" value={pending} />
      </div>
    </div>
  )
}
