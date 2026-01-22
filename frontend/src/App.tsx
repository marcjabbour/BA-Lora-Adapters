import { useState } from 'react'
import { PipelineVisualizer } from './components/pipeline/PipelineVisualizer'
import { ChatInterface } from './components/chat/ChatInterface'
import { Header } from './components/layout/Header'
import './index.css'

function App() {
  const [view, setView] = useState<'pipeline' | 'chat'>('pipeline')

  return (
    <div className="min-h-screen bg-gray-50">
      <Header currentView={view} onViewChange={setView} />
      {view === 'pipeline' ? <PipelineVisualizer /> : <ChatInterface />}
    </div>
  )
}

export default App
