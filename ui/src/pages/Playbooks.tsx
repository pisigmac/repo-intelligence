import { Link } from 'react-router-dom'
import { usePlaybooks } from '../hooks/usePlaybooks'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import StatusBadge from '../components/StatusBadge'

export default function Playbooks() {
  const { data, isLoading, error } = usePlaybooks()

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error as Error} />

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Playbooks</h2>
      <div className="space-y-4">
        {data?.map((pb) => (
          <Link
            key={pb.id}
            to={`/playbooks/${pb.id}`}
            className="block bg-white p-4 rounded-lg shadow border hover:shadow-md"
          >
            <div className="flex justify-between items-start">
              <h3 className="font-semibold text-lg">{pb.name}</h3>
              <StatusBadge status={pb.status} />
            </div>
            <p className="text-gray-600 mt-2">{pb.description}</p>
            <p className="text-sm text-gray-500 mt-2">{pb.steps.length} steps</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
