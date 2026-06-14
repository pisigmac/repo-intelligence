import { Link } from 'react-router-dom'
import { useCapabilities } from '../hooks/useCapabilities'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import StatusBadge from '../components/StatusBadge'

export default function Capabilities() {
  const { data, isLoading, error } = useCapabilities()

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error as Error} />

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Capabilities</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data?.map((cap) => (
          <Link
            key={cap.id}
            to={`/capabilities/${cap.id}`}
            className="bg-white p-4 rounded-lg shadow border hover:shadow-md"
          >
            <div className="flex justify-between items-start">
              <h3 className="font-semibold text-lg">{cap.name}</h3>
              <StatusBadge status={cap.category} />
            </div>
            <p className="text-gray-600 mt-2">{cap.description}</p>
            <p className="text-sm text-gray-500 mt-2">{cap.entry_points.length} entry points</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
