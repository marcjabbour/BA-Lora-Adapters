import { create } from 'zustand'
import type { StepState, StepStatus } from '../types/pipeline'

interface PipelineStore {
  sessionId: string | null
  autoMode: boolean
  currentStep: number | null
  steps: Record<number, StepState>

  // Actions
  setSessionId: (id: string) => void
  setAutoMode: (enabled: boolean) => void
  updateStepStatus: (stepId: number, status: StepStatus) => void
  updateStepProgress: (stepId: number, progress: number, message?: string) => void
  updateStepOutputFiles: (stepId: number, files: string[]) => void
  setStepError: (stepId: number, error: string) => void
  resetPipeline: () => void
  deleteSession: () => void
}

const initialSteps: Record<number, StepState> = {
  1: { stepId: 1, name: 'Sanitization', status: 'pending', progress: 0, outputFiles: [] },
  2: { stepId: 2, name: 'Tagging', status: 'pending', progress: 0, outputFiles: [] },
  3: { stepId: 3, name: 'Exporting', status: 'pending', progress: 0, outputFiles: [] },
  4: { stepId: 4, name: 'Training', status: 'pending', progress: 0, outputFiles: [] },
  5: { stepId: 5, name: 'Serving (Future)', status: 'pending', progress: 0, outputFiles: [] },
}

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  sessionId: null,
  autoMode: false,
  currentStep: null,
  steps: initialSteps,

  setSessionId: (id: string) => set({ sessionId: id }),

  setAutoMode: (enabled: boolean) => set({ autoMode: enabled }),

  updateStepStatus: (stepId: number, status: StepStatus) => set((state) => ({
    steps: {
      ...state.steps,
      [stepId]: { ...state.steps[stepId], status }
    },
    currentStep: status === 'running' ? stepId : state.currentStep
  })),

  updateStepProgress: (stepId: number, progress: number, message?: string) => set((state) => ({
    steps: {
      ...state.steps,
      [stepId]: { ...state.steps[stepId], progress, progressMessage: message }
    }
  })),

  updateStepOutputFiles: (stepId: number, files: string[]) => set((state) => ({
    steps: {
      ...state.steps,
      [stepId]: { ...state.steps[stepId], outputFiles: files }
    }
  })),

  setStepError: (stepId: number, error: string) => set((state) => ({
    steps: {
      ...state.steps,
      [stepId]: {
        ...state.steps[stepId],
        status: 'failed',
        errorMessage: error
      }
    }
  })),

  resetPipeline: () => {
    const sessionId = get().sessionId
    if (sessionId) {
      // API call will be handled by the component
      fetch(`http://localhost:8000/api/pipeline/session/${sessionId}`, {
        method: 'DELETE'
      }).catch(console.error)
    }
    set({
      sessionId: null,
      currentStep: null,
      steps: { ...initialSteps }
    })
  },

  deleteSession: () => {
    const sessionId = get().sessionId
    if (sessionId) {
      fetch(`http://localhost:8000/api/pipeline/session/${sessionId}`, {
        method: 'DELETE'
      }).catch(console.error)
    }
    set({
      sessionId: null,
      currentStep: null,
      steps: { ...initialSteps }
    })
  }
}))
