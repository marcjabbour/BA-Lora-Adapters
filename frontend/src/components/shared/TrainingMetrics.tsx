import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface TrainingMetricsData {
  lossHistory: Array<{ step: number; loss: number }>
  finalLoss: number
  epochs: number
  totalSteps: number
}

interface TrainingMetricsProps {
  data?: TrainingMetricsData
}

export const TrainingMetrics = ({ data }: TrainingMetricsProps) => {
  if (!data) {
    return (
      <div className="space-y-4 p-4 border rounded-lg bg-gray-50">
        <p className="text-sm text-gray-500">No training metrics available yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium mb-2">Training Loss</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data.lossHistory}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="step"
              label={{ value: 'Step', position: 'insideBottom', offset: -5 }}
            />
            <YAxis
              label={{ value: 'Loss', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="loss"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-gray-500 text-xs">Final Loss</p>
          <p className="text-lg font-semibold">{data.finalLoss.toFixed(4)}</p>
        </div>
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-gray-500 text-xs">Epochs</p>
          <p className="text-lg font-semibold">{data.epochs}</p>
        </div>
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-gray-500 text-xs">Total Steps</p>
          <p className="text-lg font-semibold">{data.totalSteps}</p>
        </div>
      </div>
    </div>
  )
}
