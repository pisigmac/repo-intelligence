import { useState } from 'react'
import { useQuerySearch } from '../hooks/useQuerySearch'
import JsonView from '../components/JsonView'

export default function Query() {
  const [q, setQ] = useState('')
  const search = useQuerySearch()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    search.mutate({ query: q, top_k: 5 })
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Natural Language Query</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="How do I add a protected route?"
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          type="submit"
          disabled={search.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Search
        </button>
      </form>
      {search.data && (
        <div className="space-y-4">
          {search.data.map((result) => (
            <div key={result.id} className="bg-white p-4 rounded-lg shadow border">
              <p className="font-medium">{result.id}</p>
              <p className="text-sm text-gray-500">Score: {result.score.toFixed(3)}</p>
              <JsonView data={result.payload} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
