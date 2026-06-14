import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listApprovals, getApprovalDiff, submitApprovalDecision } from '../api/client'

export const useApprovals = (filters?: { status?: string }) =>
  useQuery({
    queryKey: ['approvals', filters],
    queryFn: () => listApprovals(filters),
  })

export const useApprovalDiff = (id: string) =>
  useQuery({
    queryKey: ['approval-diff', id],
    queryFn: () => getApprovalDiff(id),
    enabled: !!id,
  })

export const useApprovalDecision = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'approved' | 'rejected' }) =>
      submitApprovalDecision(id, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
    },
  })
}
