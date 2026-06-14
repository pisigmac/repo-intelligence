export default function ErrorState({ error }: { error: Error | null }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded">
      <p className="font-semibold">Something went wrong</p>
      <p className="text-sm">{error?.message || 'Unknown error'}</p>
    </div>
  )
}
