import { useState } from 'react'
import { getFeedbackMetrics } from '../api/client'
import JsonView from '../components/JsonView'

export default function Feedback() {
  const [playbookId, setPlaybookId] = useState('')
  const [metrics, setMetrics] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await getFeedbackMetrics(playbookId)
      setMetrics(res)
    } catch (err) {
      setMetrics({ error: (err as Error).message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Feedback Metrics</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
        <input
          type="text"
          value={playbookId}
          onChange={(e) => setPlaybookId(e.target.value)}
          placeholder="Playbook ID"
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Load
        </button>
      </form>
      {metrics !== null && <JsonView data={metrics} />}
    </div>
  )
}
