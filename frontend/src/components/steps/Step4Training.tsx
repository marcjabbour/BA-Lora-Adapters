import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { AlertTriangle, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Step4TrainingProps {
  onConfigChange: (config: Step4ConfigData) => void
  onDownload: () => void
  isCompleted: boolean
  defaultConfig?: Step4ConfigData
}

export interface Step4ConfigData {
  baseModel: string
  epochs?: number
  batchSize?: number
  learningRate?: number
}

const MODELS = [
  {
    name: 'Qwen/Qwen2-1.5B-Instruct',
    size: '1.5B',
    gpuRequired: false,
    estimatedTime: '2-6 hours on CPU',
    recommended: true,
    description: 'Lightweight model, CPU-friendly, good for testing',
  },
  {
    name: 'Qwen/Qwen2-7B-Instruct',
    size: '7B',
    gpuRequired: true,
    estimatedTime: '24+ hours on CPU, 2-4 hours on GPU',
    recommended: false,
    description: 'Larger model, requires GPU for reasonable training time',
  },
]

export const Step4Training = ({
  onConfigChange,
  onDownload,
  isCompleted,
  defaultConfig,
}: Step4TrainingProps) => {
  const [selectedModel, setSelectedModel] = useState(
    defaultConfig?.baseModel || MODELS[0].name
  )

  const model = MODELS.find((m) => m.name === selectedModel) || MODELS[0]

  const handleModelChange = (newModel: string) => {
    setSelectedModel(newModel)
    onConfigChange({ baseModel: newModel })
  }

  return (
    <div className="space-y-4">
      {/* Model Selection */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Base Model</label>
        <Select value={selectedModel} onValueChange={handleModelChange}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MODELS.map((m) => (
              <SelectItem key={m.name} value={m.name}>
                <span className="flex items-center gap-2">
                  {m.name} ({m.size})
                  {m.recommended && <span className="text-yellow-500">⭐</span>}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500">{model.description}</p>
      </div>

      {/* GPU Warning */}
      {model.gpuRequired && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>GPU Required:</strong> This model is large and training on
            CPU will be extremely slow ({model.estimatedTime}). A GPU is
            highly recommended.
          </AlertDescription>
        </Alert>
      )}

      {/* Training Time Estimate */}
      {!model.gpuRequired && (
        <Alert>
          <AlertDescription>
            <strong>Estimated Training Time:</strong> {model.estimatedTime}
          </AlertDescription>
        </Alert>
      )}

      {/* Configuration Summary */}
      <div className="pt-4 border-t border-gray-200">
        <p className="text-xs font-medium text-gray-700 mb-2">
          Training Configuration:
        </p>
        <div className="text-xs text-gray-600 space-y-1">
          <p>• Base Model: {model.name}</p>
          <p>• Model Size: {model.size}</p>
          <p>• GPU Required: {model.gpuRequired ? 'Yes' : 'No'}</p>
        </div>
      </div>

      {/* Download Adapter Button */}
      {isCompleted && (
        <div className="pt-4 border-t border-gray-200">
          <Button onClick={onDownload} className="w-full">
            <Download className="mr-2 h-4 w-4" />
            Download Adapter (.zip)
          </Button>
        </div>
      )}
    </div>
  )
}
