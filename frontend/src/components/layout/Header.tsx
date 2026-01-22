import { Button } from '../ui/button'

interface HeaderProps {
  currentView: 'pipeline' | 'chat'
  onViewChange: (view: 'pipeline' | 'chat') => void
}

export const Header = ({ currentView, onViewChange }: HeaderProps) => {
  return (
    <header className="border-b bg-white">
      <div className="container mx-auto px-8 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              LoRA Training Pipeline
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Build and test custom LoRA adapters from customer transcripts
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant={currentView === 'pipeline' ? 'default' : 'outline'}
              onClick={() => onViewChange('pipeline')}
            >
              Pipeline
            </Button>
            <Button
              variant={currentView === 'chat' ? 'default' : 'outline'}
              onClick={() => onViewChange('chat')}
            >
              Test Chat
            </Button>
          </div>
        </div>
      </div>
    </header>
  )
}
