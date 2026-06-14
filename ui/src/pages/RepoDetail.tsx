import { useParams } from 'react-router-dom'
import { useRepo, useParse } from '../hooks/useRepos'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import JsonView from '../components/JsonView'
import StatusBadge from '../components/StatusBadge'

export default function RepoDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: repo, isLoading, error } = useRepo(id!)
  const { data: parse } = useParse(id!)

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState error={error as Error} />
  if (!repo) return <div>Repo not found</div>

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">{repo.url}</h2>
      <div className="bg-white p-6 rounded-lg shadow border mb-6 space-y-2">
        <p><strong>ID:</strong> {repo.id}</p>
        <p><strong>Branch:</strong> {repo.branch}</p>
        <p>
          <strong>Status:</strong> <StatusBadge status={repo.status} />
        </p>
        <p><strong>Commit:</strong> {repo.commit_hash || '-'}</p>
      </div>
      {parse && (
        <div>
          <h3 className="text-lg font-semibold mb-2">Parsed Output</h3>
          <JsonView data={parse} />
        </div>
      )}
    </div>
  )
}
