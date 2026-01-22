import { Card, CardHeader, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { StatusIndicator } from '../shared/StatusIndicator'
import { ProgressBar } from '../shared/ProgressBar'
import { Alert, AlertDescription } from '../ui/alert'
import { Download, Eye, Upload } from 'lucide-react'
import type { StepState } from '../../types/pipeline'
import { usePipelineStore } from '../../store/pipelineStore'
import { pipelineApi, filesApi } from '../../services/api'
import { useState } from 'react'

interface StepCardProps {
  stepId: number
  step: StepState
}

const getStepDescription = (stepId: number): string => {
  const descriptions: Record<number, string> = {
    1: 'Clean and sanitize raw transcript files',
    2: 'Evaluate conversations and rewrite poor responses',
    3: 'Convert to ShareGPT format for training',
    4: 'Train LoRA adapter on processed data',
    5: 'Serve adapter with vLLM (Coming Soon)',
  }
  return descriptions[stepId] || ''
}

export const StepCard = ({ stepId, step }: StepCardProps) => {
  const { sessionId, steps } = usePipelineStore()
  const [uploading, setUploading] = useState(false)
  const [executing, setExecuting] = useState(false)

  // Check if previous step is completed (for steps 2-5)
  const previousStepCompleted = stepId === 1 || steps[stepId - 1]?.status === 'completed'
  const canRun = step.status === 'pending' && previousStepCompleted && sessionId

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return

    setUploading(true)
    try {
      const response = await pipelineApi.uploadFiles(files)
      usePipelineStore.getState().setSessionId(response.session_id)
      console.log('Files uploaded, session created:', response.session_id)
    } catch (error) {
      console.error('Upload failed:', error)
      alert('Failed to upload files. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const handleExecute = async () => {
    if (!sessionId) return

    setExecuting(true)
    try {
      await pipelineApi.executeStep(sessionId, stepId)
      console.log(`Step ${stepId} execution started`)
    } catch (error) {
      console.error(`Step ${stepId} execution failed:`, error)
      alert(`Failed to execute step ${stepId}. Please try again.`)
    } finally {
      setExecuting(false)
    }
  }

  const handlePreview = async () => {
    if (!sessionId) return

    try {
      const data = await filesApi.previewStep(sessionId, stepId)
      console.log('Preview data:', data)
      // For now, just log to console. We'll add a modal later
      alert('Preview data logged to console')
    } catch (error) {
      console.error('Preview failed:', error)
      alert('Failed to preview files. Please try again.')
    }
  }

  const handleDownloadAdapter = async () => {
    if (!sessionId) return

    try {
      await filesApi.downloadAdapter(sessionId)
      console.log('Adapter downloaded')
    } catch (error) {
      console.error('Download failed:', error)
      alert('Failed to download adapter. Please try again.')
    }
  }

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-4">
          <StatusIndicator status={step.status} />
          <div>
            <h3 className="text-2xl font-semibold">
              Step {stepId}: {step.name}
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              {getStepDescription(stepId)}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {stepId === 1 && !sessionId && (
            <label htmlFor="file-upload" className="cursor-pointer">
              <input
                id="file-upload"
                type="file"
                multiple
                accept=".json"
                onChange={(e) => handleUpload(e.target.files)}
                className="hidden"
                disabled={uploading}
              />
              <Button disabled={uploading} asChild>
                <span>
                  <Upload className="h-4 w-4 mr-2" />
                  {uploading ? 'Uploading...' : 'Upload Files'}
                </span>
              </Button>
            </label>
          )}

          {canRun && stepId !== 1 && (
            <Button onClick={handleExecute} disabled={executing}>
              {executing ? 'Starting...' : 'Run Step'}
            </Button>
          )}

          {step.status === 'completed' && (
            <>
              <Button variant="outline" size="icon" onClick={handlePreview}>
                <Eye className="h-4 w-4" />
              </Button>
              {stepId === 4 && (
                <Button variant="outline" size="icon" onClick={handleDownloadAdapter}>
                  <Download className="h-4 w-4" />
                </Button>
              )}
            </>
          )}
        </div>
      </CardHeader>

      {step.status === 'running' && (
        <CardContent>
          <ProgressBar progress={step.progress} />
          <p className="text-sm text-gray-500 mt-2">
            {step.progress.toFixed(1)}% complete
          </p>
        </CardContent>
      )}

      {step.errorMessage && (
        <CardContent>
          <Alert variant="destructive">
            <AlertDescription>{step.errorMessage}</AlertDescription>
          </Alert>
        </CardContent>
      )}
    </Card>
  )
}
