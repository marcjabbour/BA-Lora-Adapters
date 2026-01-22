import { useEffect, useRef } from 'react'
import { usePipelineStore } from '../store/pipelineStore'
import type { WebSocketMessage } from '../types/pipeline'

const WS_BASE_URL = 'ws://localhost:8000'

export const useWebSocket = (sessionId: string | null) => {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | undefined>(undefined)
  const { updateStepStatus, updateStepProgress, setStepError } = usePipelineStore()

  useEffect(() => {
    if (!sessionId) return

    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_BASE_URL}/ws/pipeline/${sessionId}`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          console.log('WebSocket message:', data)

          switch (data.type) {
            case 'progress':
              if (data.step_id && data.progress !== undefined) {
                updateStepProgress(data.step_id, data.progress)
              }
              break

            case 'status':
              if (data.step_id && data.status) {
                updateStepStatus(data.step_id, data.status)

                // If auto-mode is enabled and step completed, trigger next step
                // This will be handled by the component that's watching the status
              }
              break

            case 'log':
              console.log(`[Step ${data.step_id}]`, data.log)
              break

            case 'error':
              if (data.step_id && data.error) {
                setStepError(data.step_id, data.error)
              }
              console.error(`[Step ${data.step_id}] Error:`, data.error)
              break
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect WebSocket...')
          connectWebSocket()
        }, 3000)
      }
    }

    connectWebSocket()

    // Cleanup
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [sessionId, updateStepStatus, updateStepProgress, setStepError])

  return wsRef
}
