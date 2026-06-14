export default function JsonView({ data }: { data: unknown }) {
  return (
    <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-auto text-sm">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}
