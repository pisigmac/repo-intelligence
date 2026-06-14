import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ingestRepo, getRepo, getParse } from '../api/client'
import { IngestRequest } from '../types'

export const useRepos = () =>
  useQuery({
    queryKey: ['repos'],
    queryFn: async () => {
      // Note: the gateway does not expose a list-repos endpoint yet.
      // The Repos page works around this by showing the ingest form and a link to the new repo.
      return []
    },
  })

export const useRepo = (id: string) =>
  useQuery({
    queryKey: ['repo', id],
    queryFn: () => getRepo(id),
    enabled: !!id,
  })

export const useParse = (id: string) =>
  useQuery({
    queryKey: ['parse', id],
    queryFn: () => getParse(id),
    enabled: !!id,
  })

export const useIngestRepo = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (req: IngestRequest) => ingestRepo(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos'] })
    },
  })
}
