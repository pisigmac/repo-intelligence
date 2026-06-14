import { Link } from 'react-router-dom'
import { useApprovals, useApprovalDecision } from '../hooks/useApprovals'
import { useApprovalWebSocket } from '../hooks/useWebSocket'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import StatusBadge from '../components/StatusBadge'

export default function Approvals() {
  const { data, isLoading, error } = useApprovals()
  const decision = useApprovalDecision()
  useApprovalWebSocket()

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error as Error} />

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Approvals</h2>
      <div className="space-y-4">
        {data?.map((approval) => (
          <div
            key={approval.id}
            className="bg-white p-4 rounded-lg shadow border flex justify-between items-center"
          >
            <div>
              <Link
                to={`/approvals/${approval.id}`}
                className="font-semibold text-lg text-blue-600"
              >
                {approval.playbook_id}
              </Link>
              <p className="text-sm text-gray-500">Proposed by {approval.proposed_by}</p>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={approval.status} />
              {approval.status === 'pending' && (
                <>
                  <button
                    onClick={() => decision.mutate({ id: approval.id, decision: 'approved' })}
                    className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => decision.mutate({ id: approval.id, decision: 'rejected' })}
                    className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    Reject
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
