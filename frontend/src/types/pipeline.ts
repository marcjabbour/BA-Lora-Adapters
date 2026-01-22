export type StepStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface StepState {
  stepId: number
  name: string
  status: StepStatus
  progress: number
  outputFiles: string[]
  errorMessage?: string
}

export interface SessionState {
  sessionId: string | null
  autoMode: boolean
  currentStep: number | null
  steps: Record<number, StepState>
}

export interface Step2Config {
  provider: string
  model: string
  rewriteThreshold: number
}

export interface Step4Config {
  baseModel: string
  epochs?: number
  batchSize?: number
  learningRate?: number
}

export interface WebSocketMessage {
  type: 'progress' | 'status' | 'log' | 'error'
  step_id?: number
  progress?: number
  message?: string
  status?: StepStatus
  log?: string
  error?: string
  timestamp: string
}

export interface FilePreviewResponse {
  files: Array<{
    filename: string
    content: any
  }>
  totalRecords?: number
  sample?: any
  adapterSizeMb?: number
}

export interface StatusResponse {
  session_id: string
  auto_mode: boolean
  current_step: number | null
  steps: Record<number, StepState>
}
