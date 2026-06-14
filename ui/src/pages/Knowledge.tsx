import { useState } from 'react'
import { searchKnowledge } from '../api/client'
import JsonView from '../components/JsonView'

export default function Knowledge() {
  const [q, setQ] = useState('')
  const [language, setLanguage] = useState('')
  const [results, setResults] = useState<unknown[]>([])
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await searchKnowledge({ query: q, language })
      setResults(res)
    } catch (err) {
      setResults([{ error: (err as Error).message }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Global Knowledge</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search cross-repo knowledge..."
          className="flex-1 border rounded px-3 py-2"
        />
        <input
          type="text"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          placeholder="Language (optional)"
          className="w-40 border rounded px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Search
        </button>
      </form>
      <div className="space-y-4">
        {results.map((result, idx) => (
          <div key={idx} className="bg-white p-4 rounded-lg shadow border">
            <JsonView data={result} />
          </div>
        ))}
      </div>
    </div>
  )
}
