import { useQuery } from '@tanstack/react-query'
import { listCapabilities } from '../api/client'

export const useCapabilities = (filters?: { repo?: string; category?: string }) =>
  useQuery({
    queryKey: ['capabilities', filters],
    queryFn: () => listCapabilities(filters),
  })
