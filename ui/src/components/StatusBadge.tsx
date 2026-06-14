export default function StatusBadge({ status }: { status: string }) {
  const color =
    status === 'analyzed' || status === 'approved'
      ? 'bg-green-100 text-green-800'
      : status === 'pending'
      ? 'bg-yellow-100 text-yellow-800'
      : status === 'failed'
      ? 'bg-red-100 text-red-800'
      : 'bg-gray-100 text-gray-800'

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${color}`}>
      {status}
    </span>
  )
}
