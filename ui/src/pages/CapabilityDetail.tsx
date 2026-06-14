import { useParams } from 'react-router-dom'
import { useCapabilities } from '../hooks/useCapabilities'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import JsonView from '../components/JsonView'

export default function CapabilityDetail() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, error } = useCapabilities()
  const cap = data?.find((c) => c.id === id)

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error as Error} />
  if (!cap) return <div>Capability not found</div>

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">{cap.name}</h2>
      <p className="text-gray-600 mb-6">{cap.description}</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-lg shadow border">
          <h3 className="font-semibold mb-2">Entry Points</h3>
          <ul className="space-y-2">
            {cap.entry_points.map((ep, idx) => (
              <li key={idx} className="text-sm">
                <span className="font-medium">{ep.method || 'fn'}</span>{' '}
                {ep.path || ep.file}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <h3 className="font-semibold mb-2">Dependencies</h3>
          <div className="flex flex-wrap gap-2">
            {cap.dependencies.map((dep) => (
              <span key={dep} className="px-2 py-1 bg-gray-100 rounded text-sm">
                {dep}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <h3 className="font-semibold mb-2">Interfaces</h3>
        <JsonView data={cap.interfaces} />
      </div>
    </div>
  )
}
