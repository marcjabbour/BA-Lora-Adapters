import { motion } from 'framer-motion'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'
import type { StepStatus } from '../../types/pipeline'

interface StatusIndicatorProps {
  status: StepStatus
}

export const StatusIndicator = ({ status }: StatusIndicatorProps) => {
  const statusConfig = {
    pending: { icon: Circle, color: 'text-gray-400', animate: false },
    running: { icon: Loader2, color: 'text-blue-500', animate: true },
    completed: { icon: CheckCircle2, color: 'text-green-500', animate: false },
    failed: { icon: XCircle, color: 'text-red-500', animate: false }
  }

  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <motion.div
      animate={config.animate ? { rotate: 360 } : {}}
      transition={config.animate ? { duration: 2, repeat: Infinity, ease: 'linear' } : {}}
    >
      <Icon className={`w-8 h-8 ${config.color}`} />
    </motion.div>
  )
}
