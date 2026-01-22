import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Loader2 } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { TrainingMetrics } from './TrainingMetrics'
import { useFilePreview } from '@/hooks/useFilePreview'

interface FilePreviewProps {
  stepId: number
  sessionId: string
  isOpen: boolean
  onClose: () => void
}

export const FilePreview = ({ stepId, sessionId, isOpen, onClose }: FilePreviewProps) => {
  const { data, isLoading, error } = useFilePreview(stepId, sessionId, isOpen)

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <span className="ml-3 text-gray-600">Loading preview...</span>
        </div>
      )
    }

    if (error) {
      return (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )
    }

    if (!data) {
      return (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-gray-600 text-sm">No preview data available.</p>
        </div>
      )
    }

    // Steps 1 & 2: Multiple JSON files with tabs
    if ((stepId === 1 || stepId === 2) && data.files) {
      return (
        <Tabs defaultValue="0" className="w-full">
          <TabsList className="w-full justify-start overflow-x-auto">
            {data.files.map((file, idx) => (
              <TabsTrigger key={idx} value={String(idx)}>
                {file.filename}
              </TabsTrigger>
            ))}
          </TabsList>
          {data.files.map((file, idx) => (
            <TabsContent key={idx} value={String(idx)} className="mt-4">
              <div className="max-h-[500px] overflow-y-auto rounded-lg border">
                <SyntaxHighlighter
                  language="json"
                  style={tomorrow}
                  customStyle={{
                    margin: 0,
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem',
                  }}
                >
                  {JSON.stringify(file.content, null, 2)}
                </SyntaxHighlighter>
              </div>
            </TabsContent>
          ))}
        </Tabs>
      )
    }

    // Step 3: ShareGPT export preview
    if (stepId === 3) {
      return (
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900">
              <strong>Total training records:</strong> {data.totalRecords || 0}
            </p>
            <p className="text-xs text-blue-700 mt-1">
              This file is in ShareGPT format, ready for LlamaFactory training.
            </p>
          </div>
          {data.sample && (
            <div>
              <h4 className="text-sm font-medium mb-2">Sample Record:</h4>
              <div className="max-h-[400px] overflow-y-auto rounded-lg border">
                <SyntaxHighlighter
                  language="json"
                  style={tomorrow}
                  customStyle={{
                    margin: 0,
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem',
                  }}
                >
                  {JSON.stringify(data.sample, null, 2)}
                </SyntaxHighlighter>
              </div>
            </div>
          )}
        </div>
      )
    }

    // Step 4: Training metrics
    if (stepId === 4) {
      return (
        <div className="space-y-4">
          {data.trainingMetrics && <TrainingMetrics data={data.trainingMetrics} />}
          {data.adapterSizeMb !== undefined && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-900">
                <strong>Adapter size:</strong> {data.adapterSizeMb.toFixed(2)} MB
              </p>
              {data.files && data.files.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs text-green-800 font-medium">Files:</p>
                  <ul className="list-disc list-inside text-xs text-green-700 mt-1">
                    {data.files.map((file, idx) => (
                      <li key={idx}>{typeof file === 'string' ? file : file.filename}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )
    }

    return null
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Step {stepId} Output Preview</DialogTitle>
        </DialogHeader>
        <div className="mt-4">{renderContent()}</div>
      </DialogContent>
    </Dialog>
  )
}
