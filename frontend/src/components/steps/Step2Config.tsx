import { useState } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Step2ConfigProps {
  onConfigChange: (config: Step2ConfigData) => void
  defaultConfig?: Step2ConfigData
}

export interface Step2ConfigData {
  provider: string
  model: string
  rewriteThreshold: number
}

const LLM_MODELS = {
  openai: [
    {
      value: 'gpt-4o',
      label: 'GPT-4o (Recommended)',
    },
    {
      value: 'gpt-4o-mini',
      label: 'GPT-4o Mini',
    },
  ],
}

export const Step2Config = ({
  onConfigChange,
  defaultConfig,
}: Step2ConfigProps) => {
  const [provider] = useState(defaultConfig?.provider || 'openai')
  const [model, setModel] = useState(defaultConfig?.model || 'gpt-4o')
  const [threshold, setThreshold] = useState(
    defaultConfig?.rewriteThreshold || 6
  )

  const handleModelChange = (newModel: string) => {
    setModel(newModel)
    onConfigChange({ provider, model: newModel, rewriteThreshold: threshold })
  }

  const handleThresholdChange = (newThreshold: number) => {
    setThreshold(newThreshold)
    onConfigChange({ provider, model, rewriteThreshold: newThreshold })
  }

  return (
    <div className="space-y-6 p-4 bg-gray-50 rounded-lg">
      {/* Model Selection */}
      <div>
        <label className="text-sm font-medium mb-2 block">
          Model Selection
        </label>
        <Select value={model} onValueChange={handleModelChange}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LLM_MODELS[provider as keyof typeof LLM_MODELS].map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Rewrite Threshold Slider */}
      <div>
        <label className="text-sm font-medium mb-2 block">
          Rewrite Threshold: {threshold}/10
        </label>
        <input
          type="range"
          min="1"
          max="10"
          step="1"
          value={threshold}
          onChange={(e) => handleThresholdChange(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Responses scoring ≤ {threshold} will be rewritten by the LLM
        </p>
      </div>

      {/* Configuration Summary */}
      <div className="pt-4 border-t border-gray-200">
        <p className="text-xs font-medium text-gray-700 mb-2">
          Current Configuration:
        </p>
        <div className="text-xs text-gray-600 space-y-1">
          <p>• Provider: {provider.toUpperCase()}</p>
          <p>• Model: {model}</p>
          <p>• Threshold: {threshold}</p>
        </div>
      </div>
    </div>
  )
}
