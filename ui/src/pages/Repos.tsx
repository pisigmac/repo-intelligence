import { useState } from 'react'
import { useIngestRepo } from '../hooks/useRepos'
import { Link } from 'react-router-dom'

export default function Repos() {
  const [url, setUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const ingest = useIngestRepo()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    ingest.mutate({ git_url: url, branch })
    setUrl('')
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Repositories</h2>

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow border mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo.git"
            className="flex-1 border rounded px-3 py-2"
            required
          />
          <input
            type="text"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            placeholder="main"
            className="w-32 border rounded px-3 py-2"
          />
          <button
            type="submit"
            disabled={ingest.isPending}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {ingest.isPending ? 'Ingesting...' : 'Ingest'}
          </button>
        </div>
        {ingest.isSuccess && (
          <p className="mt-3 text-green-600">
            Repo queued. Job ID: {ingest.data.job_id}.{' '}
            <Link to={`/repos/${ingest.data.repo_id}`} className="underline">
              View repo
            </Link>
          </p>
        )}
      </form>

      <p className="text-gray-600">
        A backend list-repos endpoint is not exposed yet. Ingest a repo to see its details.
      </p>
    </div>
  )
}
