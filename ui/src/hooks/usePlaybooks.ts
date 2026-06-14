import { useQuery } from '@tanstack/react-query'
import { listPlaybooks, listPlaybookVersions, transferPlaybook } from '../api/client'
import { useMutation, useQueryClient } from '@tanstack/react-query'

export const usePlaybooks = (filters?: { repo?: string; capability_id?: string }) =>
  useQuery({
    queryKey: ['playbooks', filters],
    queryFn: () => listPlaybooks(filters),
  })

export const usePlaybookVersions = (id: string) =>
  useQuery({
    queryKey: ['playbook-versions', id],
    queryFn: () => listPlaybookVersions(id),
    enabled: !!id,
  })

export const useTransferPlaybook = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, repo }: { id: string; repo: string }) =>
      transferPlaybook(id, { repo }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] })
    },
  })
}
