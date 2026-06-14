import { useParams } from 'react-router-dom'
import { usePlaybooks } from '../hooks/usePlaybooks'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import JsonView from '../components/JsonView'

export default function PlaybookDetail() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, error } = usePlaybooks()
  const pb = data?.find((p) => p.id === id)

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error as Error} />
  if (!pb) return <div>Playbook not found</div>

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">{pb.name}</h2>
      <p className="text-gray-600 mb-6">{pb.description}</p>

      <h3 className="text-lg font-semibold mb-2">Steps</h3>
      <div className="space-y-3 mb-6">
        {pb.steps.map((step) => (
          <div key={step.id} className="bg-white p-4 rounded-lg shadow border">
            <div className="flex justify-between">
              <span className="font-medium">{step.id}</span>
              <span className="text-sm text-gray-500">{step.type}</span>
            </div>
            <p className="text-sm text-gray-600 mt-1">Target: {step.target}</p>
            <JsonView data={step.payload} />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-4 rounded-lg shadow border">
          <h3 className="font-semibold mb-2">Validation</h3>
          <JsonView data={pb.validation} />
        </div>
        <div className="bg-white p-4 rounded-lg shadow border">
          <h3 className="font-semibold mb-2">Rollback</h3>
          <JsonView data={pb.rollback} />
        </div>
        <div className="bg-white p-4 rounded-lg shadow border">
          <h3 className="font-semibold mb-2">Observability</h3>
          <JsonView data={pb.observability} />
        </div>
      </div>
    </div>
  )
}
