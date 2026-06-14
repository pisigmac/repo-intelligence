import { useMutation } from '@tanstack/react-query'
import { query } from '../api/client'
import { QueryRequest } from '../types'

export const useQuerySearch = () =>
  useMutation({
    mutationFn: (req: QueryRequest) => query(req),
  })
