import axios from 'axios'
import type { StatusResponse, FilePreviewResponse, Step2Config, Step4Config } from '../types/pipeline'

const API_BASE_URL = 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Pipeline Control Endpoints
export const pipelineApi = {
  // Upload files and create session
  uploadFiles: async (files: FileList) => {
    const formData = new FormData()
    Array.from(files).forEach(file => {
      formData.append('files', file)
    })

    const response = await api.post('/api/pipeline/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Execute a specific step
  executeStep: async (sessionId: string, stepId: number, config?: Step2Config | Step4Config) => {
    const response = await api.post(`/api/pipeline/step/${stepId}`, {
      session_id: sessionId,
      config,
    })
    return response.data
  },

  // Toggle auto mode
  toggleAutoMode: async (sessionId: string, enabled: boolean) => {
    const response = await api.post('/api/pipeline/toggle-auto', {
      session_id: sessionId,
      auto_mode: enabled,
    })
    return response.data
  },

  // Get current pipeline status
  getStatus: async (sessionId: string): Promise<StatusResponse> => {
    const response = await api.get('/api/pipeline/status', {
      params: { session_id: sessionId },
    })
    return response.data
  },

  // Reset pipeline
  resetPipeline: async (sessionId: string) => {
    const response = await api.post('/api/pipeline/reset', {
      session_id: sessionId,
    })
    return response.data
  },

  // Delete session
  deleteSession: async (sessionId: string) => {
    const response = await api.delete(`/api/pipeline/session/${sessionId}`)
    return response.data
  },
}

// File Operations Endpoints
export const filesApi = {
  // Preview step output
  previewStep: async (sessionId: string, stepId: number): Promise<FilePreviewResponse> => {
    const response = await api.get(`/api/files/preview/${stepId}`, {
      params: { session_id: sessionId },
    })
    return response.data
  },

  // Download adapter as zip
  downloadAdapter: async (sessionId: string) => {
    const response = await api.get('/api/files/download/adapter', {
      params: { session_id: sessionId },
      responseType: 'blob',
    })

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'lora-adapter.zip')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  // Download specific file
  downloadFile: async (sessionId: string, stepId: number, filename: string) => {
    const response = await api.get(`/api/files/download/step/${stepId}/${filename}`, {
      params: { session_id: sessionId },
      responseType: 'blob',
    })

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

// Health check
export const healthApi = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}
