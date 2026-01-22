import { useState, useEffect } from 'react'
import { filesApi } from '@/services/api'
import type { FilePreviewResponse } from '@/types/pipeline'

export const useFilePreview = (stepId: number, sessionId: string, isOpen: boolean) => {
  const [data, setData] = useState<FilePreviewResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !sessionId) {
      return
    }

    const fetchPreview = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await filesApi.previewStep(sessionId, stepId)
        setData(response)
      } catch (err: any) {
        console.error('Error fetching preview:', err)
        setError(err.response?.data?.detail || 'Failed to load preview')
      } finally {
        setIsLoading(false)
      }
    }

    fetchPreview()
  }, [stepId, sessionId, isOpen])

  return { data, isLoading, error }
}
