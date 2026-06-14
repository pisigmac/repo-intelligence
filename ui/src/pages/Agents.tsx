import { useState } from 'react'
import { executeAgent } from '../api/client'
import JsonView from '../components/JsonView'

export default function Agents() {
  const [task, setTask] = useState('')
  const [repoId, setRepoId] = useState('')
  const [result, setResult] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await executeAgent({ task, repo_id: repoId || undefined })
      setResult(res)
    } catch (err) {
      setResult({ error: (err as Error).message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Agent Orchestrator</h2>
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow border mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Task</label>
          <input
            type="text"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Add a new protected route to the API"
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Repo ID (optional)</label>
          <input
            type="text"
            value={repoId}
            onChange={(e) => setRepoId(e.target.value)}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Running...' : 'Run Agent'}
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
