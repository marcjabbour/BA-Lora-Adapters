import { Card, CardHeader, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { StatusIndicator } from '../shared/StatusIndicator'
import { ProgressBar } from '../shared/ProgressBar'
import { Alert, AlertDescription } from '../ui/alert'
import { Download, Eye } from 'lucide-react'
import type { StepState } from '../../types/pipeline'
import { usePipelineStore } from '../../store/pipelineStore'
import { pipelineApi, filesApi } from '../../services/api'
import { useState } from 'react'
import { Step1Upload } from '../steps/Step1Upload'
import { Step2Config, type Step2ConfigData } from '../steps/Step2Config'
import { Step3Preview } from '../steps/Step3Preview'
import { Step4Training, type Step4ConfigData } from '../steps/Step4Training'
import { FilePreview } from '../shared/FilePreview'

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
  const [previewOpen, setPreviewOpen] = useState(false)
  const [step2Config, setStep2Config] = useState<Step2ConfigData>({
    provider: 'openai',
    model: 'gpt-4o',
    rewriteThreshold: 6,
  })
  const [step4Config, setStep4Config] = useState<Step4ConfigData>({
    baseModel: 'Qwen/Qwen2-1.5B-Instruct',
  })

  // Check if previous step is completed (for steps 2-5)
  const previousStepCompleted = stepId === 1 || steps[stepId - 1]?.status === 'completed'
  const canRun = step.status === 'pending' && previousStepCompleted && sessionId

  const handleUpload = async (files: FileList) => {
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
      // Pass configuration for step 2
      if (stepId === 2) {
        await pipelineApi.executeStep(sessionId, stepId, step2Config)
      }
      // Pass configuration for step 4
      else if (stepId === 4) {
        await pipelineApi.executeStep(sessionId, stepId, step4Config)
      } else {
        await pipelineApi.executeStep(sessionId, stepId)
      }
      console.log(`Step ${stepId} execution started`)
    } catch (error) {
      console.error(`Step ${stepId} execution failed:`, error)
      alert(`Failed to execute step ${stepId}. Please try again.`)
    } finally {
      setExecuting(false)
    }
  }

  const handlePreview = () => {
    setPreviewOpen(true)
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
    <>
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

      {/* Step-specific configuration UI */}
      <CardContent>
        {stepId === 1 && (
          <Step1Upload onUpload={handleUpload} isUploading={uploading} />
        )}
        {stepId === 2 && (
          <Step2Config
            onConfigChange={setStep2Config}
            defaultConfig={step2Config}
          />
        )}
        {stepId === 3 && <Step3Preview />}
        {stepId === 4 && (
          <Step4Training
            onConfigChange={setStep4Config}
            onDownload={handleDownloadAdapter}
            isCompleted={step.status === 'completed'}
            defaultConfig={step4Config}
          />
        )}
      </CardContent>

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

      {/* File Preview Modal */}
      {sessionId && (
        <FilePreview
          stepId={stepId}
          sessionId={sessionId}
          isOpen={previewOpen}
          onClose={() => setPreviewOpen(false)}
        />
      )}
    </>
  )
}
