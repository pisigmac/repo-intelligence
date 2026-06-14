import { useParams } from 'react-router-dom'
import { useApprovalDiff, useApprovalDecision } from '../hooks/useApprovals'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

export default function ApprovalDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: diff, isLoading, error } = useApprovalDiff(id!)
  const decision = useApprovalDecision()

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error as Error} />

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Approval {id}</h2>
      <div className="bg-white p-6 rounded-lg shadow border mb-6">
        <h3 className="font-semibold mb-2">Proposed Diff</h3>
        <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-auto text-sm">{diff}</pre>
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => decision.mutate({ id: id!, decision: 'approved' })}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Approve
        </button>
        <button
          onClick={() => decision.mutate({ id: id!, decision: 'rejected' })}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Reject
        </button>
      </div>
    </div>
  )
}
