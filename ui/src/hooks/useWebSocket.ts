import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export const useApprovalWebSocket = () => {
  const queryClient = useQueryClient()

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/approvals'
    const ws = new WebSocket(wsUrl)

    ws.onmessage = () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
    }

    return () => {
      ws.close()
    }
  }, [queryClient])
}
