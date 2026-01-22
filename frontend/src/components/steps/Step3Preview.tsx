import { Info } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

export const Step3Preview = () => {
  return (
    <div className="space-y-4">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          This step exports the tagged transcripts into ShareGPT format for
          training. Once complete, you can preview the generated training data.
        </AlertDescription>
      </Alert>

      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-xs font-medium text-gray-700 mb-2">
          Export Configuration:
        </p>
        <div className="text-xs text-gray-600 space-y-1">
          <p>• Format: ShareGPT JSON</p>
          <p>• Cumulative conversation history included</p>
          <p>• Ready for LlamaFactory training</p>
        </div>
      </div>
    </div>
  )
}
