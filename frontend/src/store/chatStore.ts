import { create } from 'zustand'
import { chatApi } from '../services/api'

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

interface ChatStore {
  messages: Message[]
  isLoading: boolean
  adapterLoaded: boolean
  error: string | null

  // Actions
  loadAdapter: (sessionId: string) => Promise<void>
  sendMessage: (sessionId: string, message: string) => Promise<void>
  clearChat: () => void
  setError: (error: string | null) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isLoading: false,
  adapterLoaded: false,
  error: null,

  loadAdapter: async (sessionId: string) => {
    set({ isLoading: true, error: null })
    try {
      await chatApi.loadAdapter(sessionId)
      set({ adapterLoaded: true, isLoading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to load adapter'
      set({ error: errorMessage, isLoading: false })
      throw error
    }
  },

  sendMessage: async (sessionId: string, message: string) => {
    // Add user message immediately
    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }

    set({
      messages: [...get().messages, userMessage],
      isLoading: true,
      error: null
    })

    try {
      // Send to backend and get response
      const response = await chatApi.sendMessage(sessionId, message)

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      }

      set({
        messages: [...get().messages, assistantMessage],
        isLoading: false
      })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to send message'
      set({ error: errorMessage, isLoading: false })

      // Remove the user message if the request failed
      set({ messages: get().messages.slice(0, -1) })
      throw error
    }
  },

  clearChat: () => {
    set({
      messages: [],
      error: null
    })
  },

  setError: (error: string | null) => {
    set({ error })
  }
}))
