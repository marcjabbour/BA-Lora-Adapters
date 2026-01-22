import { useState } from 'react'
import { useChatStore } from '../../store/chatStore'
import { usePipelineStore } from '../../store/pipelineStore'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { Button } from '../ui/button'
import { Alert, AlertDescription } from '../ui/alert'
import { Loader2, Trash2, AlertTriangle } from 'lucide-react'

export const ChatInterface = () => {
  const { messages, isLoading, loadAdapter, sendMessage, clearChat, adapterLoaded, error } = useChatStore()
  const { steps, sessionId } = usePipelineStore()
  const [loadingAdapter, setLoadingAdapter] = useState(false)

  const step4Completed = steps[4].status === 'completed'

  const handleLoadAdapter = async () => {
    if (!sessionId) return
    setLoadingAdapter(true)
    try {
      await loadAdapter(sessionId)
    } catch (err) {
      console.error('Failed to load adapter:', err)
    } finally {
      setLoadingAdapter(false)
    }
  }

  const handleSendMessage = async (message: string) => {
    if (!sessionId) return
    try {
      await sendMessage(sessionId, message)
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center p-6 pb-4 border-b bg-white">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Test Adapter
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Multi-turn conversation with your trained LoRA adapter
          </p>
        </div>
        <div className="flex gap-3">
          {!adapterLoaded && step4Completed && sessionId && (
            <Button onClick={handleLoadAdapter} disabled={loadingAdapter}>
              {loadingAdapter ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Loading Adapter...
                </>
              ) : (
                'Load Adapter'
              )}
            </Button>
          )}
          {adapterLoaded && messages.length > 0 && (
            <Button variant="outline" onClick={clearChat}>
              <Trash2 className="mr-2 h-4 w-4" />
              Clear Chat
            </Button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto bg-gray-50">
        {!step4Completed ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-lg font-medium">Complete Step 4 (Training) First</p>
              <p className="text-sm mt-2">
                You need to train a LoRA adapter before you can test it
              </p>
            </div>
          </div>
        ) : !sessionId ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-lg font-medium">No Active Session</p>
              <p className="text-sm mt-2">
                Please start a pipeline session first
              </p>
            </div>
          </div>
        ) : !adapterLoaded ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <Loader2 className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-lg font-medium">Adapter Not Loaded</p>
              <p className="text-sm mt-2">
                Click "Load Adapter" to start chatting
              </p>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

      {/* Input Area */}
      <MessageInput
        onSend={handleSendMessage}
        disabled={!adapterLoaded || isLoading}
      />
    </div>
  )
}
