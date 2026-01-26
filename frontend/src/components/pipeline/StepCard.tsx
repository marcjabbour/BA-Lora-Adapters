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
import { GenericFileUpload } from '../shared/GenericFileUpload'

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

const getStepFileInfo = (stepId: number): { extensions: string[], description: string } => {
  const fileInfo: Record<number, { extensions: string[], description: string }> = {
    1: { extensions: ['.json'], description: 'Raw transcript files' },
    2: { extensions: ['.json'], description: 'Sanitized transcript files' },
    3: { extensions: ['.json'], description: 'Tagged transcript files' },
    4: { extensions: ['.json'], description: 'ShareGPT format files' },
  }
  return fileInfo[stepId] || { extensions: ['.json'], description: 'JSON files' }
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
      // Upload files and create session
      const response = await pipelineApi.uploadFiles(files)
      const newSessionId = response.session_id
      usePipelineStore.getState().setSessionId(newSessionId)
      console.log('Files uploaded, session created:', newSessionId)

      // Automatically start Step 1 after upload
      console.log('Starting Step 1 automatically...')
      await pipelineApi.executeStep(newSessionId, 1)
      console.log('Step 1 execution started')
    } catch (error) {
      console.error('Upload or execution failed:', error)
      alert('Failed to upload files or start Step 1. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const handleUploadToStep = async (files: FileList, targetStepId: number) => {
    setUploading(true)
    try {
      // Upload files directly to target step
      const response = await pipelineApi.uploadFilesToStep(files, targetStepId)
      const newSessionId = response.session_id
      usePipelineStore.getState().setSessionId(newSessionId)
      console.log(`Files uploaded to Step ${targetStepId}, session created:`, newSessionId)

      // Automatically start the target step after upload
      console.log(`Starting Step ${targetStepId} automatically...`)
      await pipelineApi.executeStep(newSessionId, targetStepId)
      console.log(`Step ${targetStepId} execution started`)
    } catch (error) {
      console.error('Upload or execution failed:', error)
      alert(`Failed to upload files or start Step ${targetStepId}. Please try again.`)
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
      <Card className={`hover:shadow-lg transition-shadow relative ${
        step.status === 'running' ? 'animate-pulse-border' : ''
      } ${step.status === 'completed' ? 'completed-step' : ''} ${
        step.status === 'skipped' ? 'skipped-step' : ''
      }`}>
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
          {/* Show Run Step button for all steps when they can run */}
          {canRun && (
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
          <div className="space-y-4">
            {!sessionId && (
              <div>
                <p className="text-sm text-gray-600 mb-3">Upload sanitized files directly to skip Step 1:</p>
                <GenericFileUpload
                  stepId={2}
                  acceptedExtensions={getStepFileInfo(2).extensions}
                  description={getStepFileInfo(2).description}
                  onUpload={handleUploadToStep}
                  isUploading={uploading}
                />
              </div>
            )}
            <Step2Config
              onConfigChange={setStep2Config}
              defaultConfig={step2Config}
            />
          </div>
        )}
        {stepId === 3 && (
          <div className="space-y-4">
            {!sessionId && (
              <div>
                <p className="text-sm text-gray-600 mb-3">Upload tagged files directly to skip Steps 1-2:</p>
                <GenericFileUpload
                  stepId={3}
                  acceptedExtensions={getStepFileInfo(3).extensions}
                  description={getStepFileInfo(3).description}
                  onUpload={handleUploadToStep}
                  isUploading={uploading}
                />
              </div>
            )}
            <Step3Preview />
          </div>
        )}
        {stepId === 4 && (
          <div className="space-y-4">
            {!sessionId && (
              <div>
                <p className="text-sm text-gray-600 mb-3">Upload ShareGPT files directly to skip Steps 1-3:</p>
                <GenericFileUpload
                  stepId={4}
                  acceptedExtensions={getStepFileInfo(4).extensions}
                  description={getStepFileInfo(4).description}
                  onUpload={handleUploadToStep}
                  isUploading={uploading}
                />
              </div>
            )}
            <Step4Training
              onConfigChange={setStep4Config}
              onDownload={handleDownloadAdapter}
              isCompleted={step.status === 'completed'}
              defaultConfig={step4Config}
            />
          </div>
        )}
      </CardContent>

      {step.status === 'running' && (
        <CardContent>
          <ProgressBar progress={step.progress} />
          <p className="text-sm text-gray-500 mt-2">
            {stepId === 2 && step.progressMessage
              ? step.progressMessage
              : `${step.progress.toFixed(1)}% complete`
            }
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
