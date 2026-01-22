import { Alert, AlertDescription } from '../ui/alert'
import { AlertTriangle } from 'lucide-react'

export const SessionWarning = () => {
  return (
    <Alert variant="warning" className="mb-4">
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>
        All files are temporary and will be deleted when you close this session.
        <strong> Download your adapters before leaving!</strong>
      </AlertDescription>
    </Alert>
  )
}
