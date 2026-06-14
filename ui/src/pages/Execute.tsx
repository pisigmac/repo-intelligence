import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { executePlaybook } from '../api/client'
import JsonView from '../components/JsonView'

export default function Execute() {
  const [params] = useSearchParams()
  const [playbookId, setPlaybookId] = useState(params.get('playbook_id') || '')
  const [contextJson, setContextJson] = useState('{}')
  const [result, setResult] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const context = JSON.parse(contextJson)
      const res = await executePlaybook({ playbook_id: playbookId, context })
      setResult(res)
    } catch (err) {
      setResult({ error: (err as Error).message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Execute Playbook</h2>
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow border mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Playbook ID</label>
          <input
            type="text"
            value={playbookId}
            onChange={(e) => setPlaybookId(e.target.value)}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Context (JSON)</label>
          <textarea
            value={contextJson}
            onChange={(e) => setContextJson(e.target.value)}
            rows={6}
            className="w-full border rounded px-3 py-2 font-mono text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Running...' : 'Execute'}
        </button>
      </form>
      {result !== null && (
        <div>
          <h3 className="font-semibold mb-2">Result</h3>
          <JsonView data={result} />
        </div>
      )}
    </div>
  )
}
