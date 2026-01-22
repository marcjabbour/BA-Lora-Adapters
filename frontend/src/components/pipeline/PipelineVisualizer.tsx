import { usePipelineStore } from '../../store/pipelineStore'
import { useWebSocket } from '../../hooks/useWebSocket'
import { StepCard } from './StepCard'
import { AnimatedWire } from './AnimatedWire'
import { SessionWarning } from '../layout/SessionWarning'
import { Button } from '../ui/button'

export const PipelineVisualizer = () => {
  const { steps, autoMode, setAutoMode, sessionId, resetPipeline } = usePipelineStore()

  // Connect WebSocket for real-time updates
  useWebSocket(sessionId)

  return (
    <div className="container mx-auto p-8 max-w-6xl">
      {/* Controls */}
      <div className="flex justify-end items-center gap-6 mb-6">
        <label className="flex items-center gap-3 cursor-pointer">
          <span className="text-sm font-medium">Auto Mode</span>
          <input
            type="checkbox"
            checked={autoMode}
            onChange={(e) => setAutoMode(e.target.checked)}
            className="w-10 h-6 bg-gray-300 rounded-full relative cursor-pointer appearance-none transition-colors checked:bg-blue-600
                     before:absolute before:w-4 before:h-4 before:bg-white before:rounded-full before:top-1 before:left-1
                     before:transition-transform checked:before:translate-x-4"
            disabled={!sessionId}
          />
        </label>
        <Button variant="destructive" onClick={resetPipeline} disabled={!sessionId}>
          Reset Pipeline
        </Button>
      </div>

      {/* Warning Banner */}
      {sessionId && <SessionWarning />}

      {/* Session Info */}
      {sessionId && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            <strong>Session ID:</strong> <code className="bg-gray-200 px-2 py-1 rounded">{sessionId}</code>
          </p>
        </div>
      )}

      {/* Pipeline Steps */}
      <div className="relative space-y-6">
        {[1, 2, 3, 4, 5].map((stepId) => (
          <div key={stepId}>
            <StepCard stepId={stepId} step={steps[stepId]} />

            {/* Animated Wire */}
            {stepId < 5 && (
              <div className="flex justify-center my-4">
                <AnimatedWire
                  active={steps[stepId].status === 'completed'}
                  blinking={steps[stepId + 1].status === 'running'}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
