# React + FastAPI Web Dashboard for LoRA Training Pipeline

## Overview

Build a comprehensive web dashboard to orchestrate the 5-step LoRA training pipeline with visual progress tracking, file previews, and an integrated chatbot for testing adapters.

## Key Requirements

### Core Features
- Upload folder of raw transcripts to start pipeline
- Visual progress tracking with loaders, status bars, and animated pipeline diagram
- Preview generated files after each step completes
- Auto mode toggle (default OFF) - automatically trigger next step or require manual trigger
- Download trained LoRA adapters
- Multi-turn chatbot interface to test loaded adapters

### Architecture Principles
1. **Self-contained frontend**: All frontend code in `/frontend` directory
2. **Temporary file system**: All pipeline data stored in temporary directories, deleted on session end
3. **User responsibility**: Files must be explicitly saved/downloaded or they're lost
4. **Single pipeline**: No concurrent execution support needed
5. **Real-time updates**: WebSocket-based progress tracking

### Visual Design
- Animated green/grey wires connecting pipeline steps
- Active step has blinking green light indicator
- Clean, fluid, intuitive interface
- GPU warnings for large models
- JSON file preview with syntax highlighting

## Technology Stack

### Frontend (`/frontend`)
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (Radix UI + Tailwind)
- **State**: Zustand (lightweight state management)
- **Animations**: Framer Motion (animated wires, blinking indicators)
- **Real-time**: Native WebSocket API
- **Charts**: Recharts (training loss visualization)
- **JSON Preview**: react-json-view

### Backend (`/backend`)
- **Framework**: FastAPI
- **Async Runtime**: asyncio for subprocess management
- **WebSocket**: FastAPI WebSocket support
- **File Storage**: Temporary directories with cleanup handlers

## Implementation Plan

### Phase 1: Backend Foundation

**1.1 Project Setup**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, routing, CORS, WebSocket
│   ├── config.py                  # Configuration & temp directory management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── pipeline.py            # Pydantic models for API
│   │   └── state.py               # Pipeline state models
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── pipeline.py        # Pipeline execution endpoints
│   │       ├── files.py           # Upload/download/preview
│   │       └── chat.py            # Chatbot endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pipeline_executor.py   # Execute steps via subprocess
│   │   ├── file_handler.py        # Handle uploads/previews/downloads
│   │   ├── temp_manager.py        # Temporary directory lifecycle
│   │   └── adapter_inference.py   # Load adapters for chatbot
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state_manager.py       # In-memory pipeline state
│   │   └── websocket_manager.py   # WebSocket broadcasting
│   └── utils/
│       ├── __init__.py
│       └── logging.py
├── requirements.txt
└── .env.example
```

**1.2 Temporary File System Design**

Create session-based temporary workspace:
```
/tmp/lora-pipeline-{session_id}/
├── raw/                           # Uploaded files
├── Step-1-Sanitization/output/
├── Step-2-Tagging/output/
├── Step-3-Exporting/output/
└── Step-4-Training/output/
```

- Session ID generated on first upload
- All pipeline operations work in this temp directory
- Cleanup on:
  - Explicit reset/clear action
  - Session timeout (configurable, default 24h)
  - Server restart (graceful cleanup)
- Adapters stored in temp space - user must download before closing

**1.3 Core API Endpoints**

```python
# Pipeline Control
POST   /api/pipeline/upload           # Upload raw data, create session
POST   /api/pipeline/step/{step_id}   # Execute specific step
POST   /api/pipeline/toggle-auto      # Toggle auto mode
GET    /api/pipeline/status           # Get current state
POST   /api/pipeline/reset            # Clear all temp data
DELETE /api/pipeline/session          # Delete session and cleanup

# WebSocket
WS     /ws/pipeline/{session_id}      # Real-time progress updates

# File Operations
GET    /api/files/preview/{step_id}              # Preview step output
GET    /api/files/download/adapter                # Download adapter as .zip
GET    /api/files/download/step/{step_id}/{file}  # Download specific file

# Chatbot
POST   /api/chat/load                 # Load adapter for testing
POST   /api/chat/message              # Send message, get response
POST   /api/chat/clear                # Clear conversation history
```

**1.4 State Management**

Single in-memory state object per session:
```python
class SessionState:
    session_id: str
    temp_dir: Path
    auto_mode: bool = False
    current_step: Optional[int] = None
    steps: Dict[int, StepState]
    created_at: datetime
    last_activity: datetime

class StepState:
    step_id: int
    name: str
    status: Enum["pending", "running", "completed", "failed"]
    progress_percent: float
    output_files: List[str]
    error_message: Optional[str]
    config: Optional[Dict[str, Any]]  # Step-specific config
```

**1.5 Pipeline Executor Service**

Execute each step via subprocess:
```python
async def execute_step_1(session_dir: Path) -> AsyncGenerator[str, None]:
    """Sanitization: Clean raw transcripts"""
    cmd = [
        "python", "scripts/sanitize_transcripts.py",
        "--input", str(session_dir / "raw"),
        "--output", str(session_dir / "Step-1-Sanitization/output"),
        "--verbose"
    ]
    async for line in run_subprocess(cmd):
        yield line  # Stream to WebSocket

async def execute_step_2(session_dir: Path, config: Step2Config) -> AsyncGenerator:
    """Tagging: LLM-based evaluation"""
    env = os.environ.copy()
    env["REWRITE_THRESHOLD"] = str(config.rewrite_threshold)

    cmd = [
        "python", "scripts/tag_transcripts.py",
        "--input", str(session_dir / "Step-1-Sanitization/output"),
        "--output", str(session_dir / "Step-2-Tagging/output"),
        "--provider", config.llm_provider,
        "--model", config.model,
        "--verbose"
    ]
    async for line in run_subprocess(cmd, env=env):
        yield line

# Similar for steps 3, 4, 5
```

**1.6 WebSocket Manager**

Real-time updates to frontend:
```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def broadcast_progress(self, session_id: str, step_id: int,
                                 progress: float, message: str):
        payload = {
            "type": "progress",
            "step_id": step_id,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_to_session(session_id, payload)

    async def broadcast_status(self, session_id: str, step_id: int, status: str):
        payload = {"type": "status", "step_id": step_id, "status": status}
        await self._broadcast_to_session(session_id, payload)

    async def broadcast_log(self, session_id: str, step_id: int, log: str):
        payload = {"type": "log", "step_id": step_id, "log": log}
        await self._broadcast_to_session(session_id, payload)
```

**1.7 Progress Tracking Strategy**

Parse subprocess stdout to calculate progress:

- **Step 1**: Count files processed from logs
- **Step 2**: Parse tqdm output (`Processing file 5/98`)
- **Step 3**: Count records generated
- **Step 4**: Parse LlamaFactory training logs (`[Epoch 1/3] [Step 100/303]`)
  - Progress = ((epoch-1) * steps_per_epoch + step) / total_steps * 100

**1.8 Temporary Directory Cleanup**

```python
class TempManager:
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        self.cleanup_threshold = timedelta(hours=24)

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        temp_dir = Path(f"/tmp/lora-pipeline-{session_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (temp_dir / "raw").mkdir()
        for i in range(1, 5):
            (temp_dir / f"Step-{i}-*/output").mkdir(parents=True)

        self.sessions[session_id] = SessionState(
            session_id=session_id,
            temp_dir=temp_dir,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        return session_id

    async def cleanup_session(self, session_id: str):
        """Delete all temp files for session"""
        if session_id in self.sessions:
            shutil.rmtree(self.sessions[session_id].temp_dir, ignore_errors=True)
            del self.sessions[session_id]

    async def cleanup_expired_sessions(self):
        """Background task to cleanup old sessions"""
        now = datetime.now()
        expired = [
            sid for sid, state in self.sessions.items()
            if now - state.last_activity > self.cleanup_threshold
        ]
        for sid in expired:
            await self.cleanup_session(sid)
```

### Phase 2: Frontend Foundation

**2.1 Project Setup**
```
frontend/
├── public/
├── src/
│   ├── main.tsx                   # Entry point
│   ├── App.tsx                    # Root component with routing
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Layout.tsx
│   │   │   └── SessionWarning.tsx     # "All files temporary" banner
│   │   ├── pipeline/
│   │   │   ├── PipelineVisualizer.tsx # Main pipeline view
│   │   │   ├── StepCard.tsx           # Individual step
│   │   │   ├── AnimatedWire.tsx       # Wire connections
│   │   │   └── StatusIndicator.tsx    # Blinking green/grey dot
│   │   ├── steps/
│   │   │   ├── Step1Upload.tsx        # File upload
│   │   │   ├── Step2Config.tsx        # LLM config
│   │   │   ├── Step3Preview.tsx       # ShareGPT preview
│   │   │   ├── Step4Training.tsx      # Model selection + GPU warning
│   │   │   └── Step5Placeholder.tsx   # Future
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx      # Chatbot UI
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── MessageInput.tsx
│   │   ├── shared/
│   │   │   ├── FilePreview.tsx        # JSON prettifier
│   │   │   ├── ProgressBar.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── TrainingMetrics.tsx    # Loss curve chart
│   ├── hooks/
│   │   ├── usePipelineState.ts        # Pipeline state hook
│   │   ├── useWebSocket.ts            # WebSocket connection
│   │   ├── useStepExecution.ts        # Execute steps
│   │   └── useFilePreview.ts          # Preview files
│   ├── services/
│   │   ├── api.ts                     # Axios API client
│   │   └── websocket.ts               # WebSocket client
│   ├── store/
│   │   ├── pipelineStore.ts           # Zustand pipeline state
│   │   ├── chatStore.ts               # Zustand chat state
│   │   └── sessionStore.ts            # Session ID management
│   ├── types/
│   │   ├── pipeline.ts                # TypeScript interfaces
│   │   └── chat.ts
│   ├── lib/
│   │   └── utils.ts                   # shadcn utils
│   └── styles/
│       └── globals.css                # Tailwind + custom styles
├── components.json                     # shadcn config
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

**2.2 State Management (Zustand)**

```typescript
// src/store/pipelineStore.ts
interface StepState {
  stepId: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  outputFiles: string[]
  errorMessage?: string
}

interface PipelineStore {
  sessionId: string | null
  autoMode: boolean
  currentStep: number | null
  steps: Record<number, StepState>

  // Actions
  setSessionId: (id: string) => void
  setAutoMode: (enabled: boolean) => void
  updateStepStatus: (stepId: number, status: string) => void
  updateStepProgress: (stepId: number, progress: number) => void
  resetPipeline: () => void
  deleteSession: () => void
}

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  sessionId: null,
  autoMode: false,
  currentStep: null,
  steps: {
    1: { stepId: 1, name: 'Sanitization', status: 'pending', progress: 0, outputFiles: [] },
    2: { stepId: 2, name: 'Tagging', status: 'pending', progress: 0, outputFiles: [] },
    3: { stepId: 3, name: 'Exporting', status: 'pending', progress: 0, outputFiles: [] },
    4: { stepId: 4, name: 'Training', status: 'pending', progress: 0, outputFiles: [] },
    5: { stepId: 5, name: 'Serving (Future)', status: 'pending', progress: 0, outputFiles: [] },
  },

  setSessionId: (id) => set({ sessionId: id }),
  setAutoMode: (enabled) => set({ autoMode: enabled }),

  updateStepStatus: (stepId, status) => set((state) => ({
    steps: {
      ...state.steps,
      [stepId]: { ...state.steps[stepId], status }
    },
    currentStep: status === 'running' ? stepId : state.currentStep
  })),

  updateStepProgress: (stepId, progress) => set((state) => ({
    steps: {
      ...state.steps,
      [stepId]: { ...state.steps[stepId], progress }
    }
  })),

  resetPipeline: () => {
    const sessionId = get().sessionId
    if (sessionId) {
      // Call API to delete session
      fetch(`/api/pipeline/session/${sessionId}`, { method: 'DELETE' })
    }
    set({
      sessionId: null,
      currentStep: null,
      steps: Object.fromEntries(
        Object.entries(get().steps).map(([id, step]) => [
          id,
          { ...step, status: 'pending', progress: 0, errorMessage: undefined }
        ])
      )
    })
  }
}))
```

**2.3 WebSocket Hook**

```typescript
// src/hooks/useWebSocket.ts
export const useWebSocket = (sessionId: string | null) => {
  const wsRef = useRef<WebSocket | null>(null)
  const { updateStepStatus, updateStepProgress } = usePipelineStore()

  useEffect(() => {
    if (!sessionId) return

    const ws = new WebSocket(`ws://localhost:8000/ws/pipeline/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => console.log('WebSocket connected')

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'progress':
          updateStepProgress(data.step_id, data.progress)
          break
        case 'status':
          updateStepStatus(data.step_id, data.status)
          // If auto-mode and step completed, trigger next step
          if (data.status === 'completed' && usePipelineStore.getState().autoMode) {
            triggerNextStep(data.step_id)
          }
          break
        case 'log':
          console.log(`[Step ${data.step_id}]`, data.log)
          break
      }
    }

    ws.onerror = (error) => console.error('WebSocket error:', error)
    ws.onclose = () => console.log('WebSocket disconnected')

    return () => ws.close()
  }, [sessionId])

  return wsRef
}
```

**2.4 Session Warning Component**

```typescript
// src/components/layout/SessionWarning.tsx
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertTriangle } from 'lucide-react'

export const SessionWarning = () => {
  return (
    <Alert variant="warning" className="mb-4">
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>
        ⚠️ All files are temporary and will be deleted when you close this session.
        <strong> Download your adapters before leaving!</strong>
      </AlertDescription>
    </Alert>
  )
}
```

### Phase 3: Pipeline Visualization

**3.1 Main Pipeline Visualizer**

```typescript
// src/components/pipeline/PipelineVisualizer.tsx
import { usePipelineStore } from '@/store/pipelineStore'
import { StepCard } from './StepCard'
import { AnimatedWire } from './AnimatedWire'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { SessionWarning } from '../layout/SessionWarning'

export const PipelineVisualizer = () => {
  const { steps, autoMode, setAutoMode, sessionId, resetPipeline } = usePipelineStore()

  return (
    <div className="container mx-auto p-8 max-w-6xl">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600
                       bg-clip-text text-transparent">
          LoRA Training Pipeline
        </h1>
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-3 cursor-pointer">
            <span className="text-sm font-medium">Auto Mode</span>
            <Switch checked={autoMode} onCheckedChange={setAutoMode} />
          </label>
          <Button variant="destructive" onClick={resetPipeline}>
            Reset Pipeline
          </Button>
        </div>
      </div>

      {/* Warning Banner */}
      {sessionId && <SessionWarning />}

      {/* Pipeline Steps */}
      <div className="relative space-y-6">
        {[1, 2, 3, 4, 5].map((stepId) => (
          <div key={stepId}>
            <StepCard stepId={stepId} step={steps[stepId]} />

            {/* Animated Wire */}
            {stepId < 5 && (
              <div className="flex justify-center my-4">
                <AnimatedWire
                  active={steps[stepId].status === 'completed'}
                  blinking={steps[stepId + 1].status === 'running'}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

**3.2 Animated Wire Component**

```typescript
// src/components/pipeline/AnimatedWire.tsx
import { motion } from 'framer-motion'

interface Props {
  active: boolean      // Green if previous step completed
  blinking: boolean    // Blinking if current step running
}

export const AnimatedWire = ({ active, blinking }: Props) => {
  return (
    <motion.div
      className={`w-1 h-16 rounded-full transition-colors duration-500 ${
        active ? 'bg-green-500' : 'bg-gray-300'
      }`}
      animate={blinking ? { opacity: [1, 0.3, 1] } : { opacity: 1 }}
      transition={blinking ? { duration: 1.5, repeat: Infinity } : {}}
    />
  )
}
```

**3.3 Status Indicator Component**

```typescript
// src/components/pipeline/StatusIndicator.tsx
import { motion } from 'framer-motion'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

interface Props {
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export const StatusIndicator = ({ status }: Props) => {
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
```

**3.4 Step Card Component**

```typescript
// src/components/pipeline/StepCard.tsx
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StatusIndicator } from './StatusIndicator'
import { ProgressBar } from '../shared/ProgressBar'
import { Download, Eye } from 'lucide-react'

interface Props {
  stepId: number
  step: StepState
}

export const StepCard = ({ stepId, step }: Props) => {
  const { executeStep, previewFiles, downloadFiles } = useStepExecution()
  const canRun = step.status === 'pending' && (stepId === 1 || previousStepCompleted)

  return (
    <Card className="hover:shadow-lg transition-shadow">
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
          {canRun && (
            <Button onClick={() => executeStep(stepId)}>
              Run Step
            </Button>
          )}
          {step.status === 'completed' && (
            <>
              <Button variant="outline" size="icon" onClick={() => previewFiles(stepId)}>
                <Eye className="h-4 w-4" />
              </Button>
              {stepId === 4 && (
                <Button variant="outline" size="icon" onClick={() => downloadFiles(stepId)}>
                  <Download className="h-4 w-4" />
                </Button>
              )}
            </>
          )}
        </div>
      </CardHeader>

      {step.status === 'running' && (
        <CardContent>
          <ProgressBar progress={step.progress} />
          <p className="text-sm text-gray-500 mt-2">
            {step.progress.toFixed(1)}% complete
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

      {/* Step-specific configuration UI */}
      <CardContent>
        {renderStepConfig(stepId, step)}
      </CardContent>
    </Card>
  )
}
```

### Phase 4: Step-Specific Components

**4.1 Step 1: File Upload**

```typescript
// src/components/steps/Step1Upload.tsx
import { useState } from 'react'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'

export const Step1Upload = () => {
  const [files, setFiles] = useState<FileList | null>(null)
  const { uploadFiles } = useStepExecution()

  const handleUpload = async () => {
    if (!files) return

    const formData = new FormData()
    Array.from(files).forEach(file => formData.append('files', file))

    await uploadFiles(formData)
  }

  return (
    <div className="space-y-4 p-4 border-2 border-dashed border-gray-300 rounded-lg">
      <div className="flex items-center justify-center">
        <label className="cursor-pointer">
          <input
            type="file"
            multiple
            accept=".json"
            onChange={(e) => setFiles(e.target.files)}
            className="hidden"
          />
          <div className="flex flex-col items-center gap-2 text-gray-500 hover:text-gray-700">
            <Upload className="w-12 h-12" />
            <span className="text-sm font-medium">
              Click to upload raw transcript files (.json)
            </span>
          </div>
        </label>
      </div>

      {files && (
        <div className="text-center">
          <p className="text-sm text-gray-600">{files.length} files selected</p>
          <Button onClick={handleUpload} className="mt-2">
            Upload & Start Pipeline
          </Button>
        </div>
      )}
    </div>
  )
}
```

**4.2 Step 2: LLM Configuration**

```typescript
// src/components/steps/Step2Config.tsx
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { useState } from 'react'

const LLM_MODELS = {
  openai: [
    { value: 'gpt-4o', label: 'GPT-4o (Recommended)', cost: '~$5-10 per run' }
  ]
}

export const Step2Config = () => {
  const [provider] = useState('openai')
  const [model, setModel] = useState('gpt-4o')
  const [threshold, setThreshold] = useState(6)

  return (
    <div className="space-y-6 p-4 bg-gray-50 rounded-lg">
      <div>
        <label className="text-sm font-medium mb-2 block">Model Selection</label>
        <Select value={model} onValueChange={setModel}>
          <SelectTrigger>
            <span>{model}</span>
          </SelectTrigger>
          <SelectContent>
            {LLM_MODELS[provider].map(m => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500 mt-1">
          {LLM_MODELS[provider].find(m => m.value === model)?.cost}
        </p>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">
          Rewrite Threshold: {threshold}/10
        </label>
        <Slider
          min={1}
          max={10}
          step={1}
          value={[threshold]}
          onValueChange={([v]) => setThreshold(v)}
          className="w-full"
        />
        <p className="text-xs text-gray-500 mt-1">
          Responses scoring ≤ {threshold} will be rewritten by the LLM
        </p>
      </div>
    </div>
  )
}
```

**4.3 Step 4: Training Configuration**

```typescript
// src/components/steps/Step4Training.tsx
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select } from '@/components/ui/select'
import { AlertTriangle, Download } from 'lucide-react'
import { TrainingMetrics } from '../shared/TrainingMetrics'

const MODELS = [
  {
    name: 'Qwen/Qwen2-1.5B-Instruct',
    size: '1.5B',
    gpuRequired: false,
    estimatedTime: '2-6 hours on CPU',
    recommended: true
  },
  {
    name: 'Qwen/Qwen2-7B-Instruct',
    size: '7B',
    gpuRequired: true,
    estimatedTime: '24+ hours on CPU, 2-4 hours on GPU'
  }
]

export const Step4Training = ({ step }: { step: StepState }) => {
  const [selectedModel, setSelectedModel] = useState(MODELS[0].name)
  const model = MODELS.find(m => m.name === selectedModel)!
  const { downloadAdapter } = useStepExecution()

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">Base Model</label>
        <Select value={selectedModel} onValueChange={setSelectedModel}>
          <SelectTrigger>
            <span>{model.name} ({model.size})</span>
          </SelectTrigger>
          <SelectContent>
            {MODELS.map(m => (
              <SelectItem key={m.name} value={m.name}>
                {m.name} ({m.size}) {m.recommended && '⭐'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {model.gpuRequired && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>GPU Required:</strong> {model.estimatedTime}
          </AlertDescription>
        </Alert>
      )}

      {step.status === 'completed' && (
        <div className="space-y-4 pt-4 border-t">
          <TrainingMetrics />
          <Button onClick={() => downloadAdapter(4)} className="w-full">
            <Download className="mr-2 h-4 w-4" />
            Download Adapter (.zip)
          </Button>
        </div>
      )}
    </div>
  )
}
```

### Phase 5: Chatbot Interface

**5.1 Chat Interface Component**

```typescript
// src/components/chat/ChatInterface.tsx
import { useState, useEffect } from 'react'
import { useChatStore } from '@/store/chatStore'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'

export const ChatInterface = () => {
  const { messages, isLoading, loadAdapter, sendMessage, clearChat, adapterLoaded } = useChatStore()
  const { steps } = usePipelineStore()
  const [loading, setLoading] = useState(false)

  const step4Completed = steps[4].status === 'completed'

  const handleLoadAdapter = async () => {
    setLoading(true)
    await loadAdapter()
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b">
        <div>
          <h2 className="text-3xl font-bold">Test Adapter</h2>
          <p className="text-sm text-gray-500 mt-1">
            Multi-turn conversation with your trained LoRA adapter
          </p>
        </div>
        <div className="flex gap-3">
          {!adapterLoaded && step4Completed && (
            <Button onClick={handleLoadAdapter} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Loading...
                </>
              ) : (
                'Load Adapter'
              )}
            </Button>
          )}
          {adapterLoaded && (
            <Button variant="outline" onClick={clearChat}>
              Clear Chat
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto mb-4">
        {!step4Completed ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            Complete Step 4 (Training) to test your adapter
          </div>
        ) : !adapterLoaded ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            Click "Load Adapter" to start chatting
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

      {/* Input */}
      <MessageInput
        onSend={sendMessage}
        disabled={!adapterLoaded || isLoading}
      />
    </div>
  )
}
```

**5.2 Message Components**

```typescript
// src/components/chat/MessageList.tsx
import { MessageBubble } from './MessageBubble'

export const MessageList = ({ messages }: { messages: Message[] }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="space-y-4">
      {messages.map((msg, idx) => (
        <MessageBubble key={idx} message={msg} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  )
}

// src/components/chat/MessageBubble.tsx
export const MessageBubble = ({ message }: { message: Message }) => {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[70%] rounded-lg px-4 py-2 ${
        isUser
          ? 'bg-blue-500 text-white'
          : 'bg-gray-100 text-gray-900'
      }`}>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  )
}

// src/components/chat/MessageInput.tsx
import { useState } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Send } from 'lucide-react'

export const MessageInput = ({ onSend, disabled }: Props) => {
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) return
    onSend(input)
    setInput('')
  }

  return (
    <div className="flex gap-2">
      <Textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
          }
        }}
        placeholder="Type your message..."
        disabled={disabled}
        rows={2}
        className="resize-none"
      />
      <Button onClick={handleSend} disabled={disabled || !input.trim()}>
        <Send className="h-4 w-4" />
      </Button>
    </div>
  )
}
```

### Phase 6: File Preview & Download

**6.1 File Preview Modal**

```typescript
// src/components/shared/FilePreview.tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import ReactJson from 'react-json-view'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export const FilePreview = ({ stepId, isOpen, onClose }: Props) => {
  const { data, isLoading } = useFilePreview(stepId)

  if (isLoading) return <LoadingSpinner />

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Step {stepId} Output Preview</DialogTitle>
        </DialogHeader>

        {stepId <= 2 && (
          <Tabs defaultValue="0">
            <TabsList>
              {data.files.map((file, idx) => (
                <TabsTrigger key={idx} value={String(idx)}>
                  {file.filename}
                </TabsTrigger>
              ))}
            </TabsList>
            {data.files.map((file, idx) => (
              <TabsContent key={idx} value={String(idx)}>
                <ReactJson
                  src={file.content}
                  collapsed={1}
                  displayDataTypes={false}
                  theme="rjv-default"
                />
              </TabsContent>
            ))}
          </Tabs>
        )}

        {stepId === 3 && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Total training records: {data.totalRecords}
            </p>
            <ReactJson
              src={data.sample}
              collapsed={2}
              displayDataTypes={false}
            />
          </div>
        )}

        {stepId === 4 && (
          <div className="space-y-4">
            <TrainingMetrics />
            <div className="text-sm text-gray-600">
              <p>Adapter size: {data.adapterSizeMb.toFixed(2)} MB</p>
              <p className="mt-2">Files:</p>
              <ul className="list-disc list-inside">
                {data.files.map(f => <li key={f}>{f}</li>)}
              </ul>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
```

**6.2 Training Metrics Visualization**

```typescript
// src/components/shared/TrainingMetrics.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export const TrainingMetrics = () => {
  const { data } = useTrainingMetrics()

  if (!data) return null

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium mb-2">Training Loss</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data.lossHistory}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="step" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="loss" stroke="#3b82f6" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <p className="text-gray-500">Final Loss</p>
          <p className="text-lg font-semibold">{data.finalLoss.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-gray-500">Epochs</p>
          <p className="text-lg font-semibold">{data.epochs}</p>
        </div>
        <div>
          <p className="text-gray-500">Total Steps</p>
          <p className="text-lg font-semibold">{data.totalSteps}</p>
        </div>
      </div>
    </div>
  )
}
```

### Phase 7: Testing & Polish

**7.1 Error Handling**

- Display error messages in step cards when subprocess fails
- Show toast notifications for upload/download success
- Graceful WebSocket reconnection on connection drop
- Validation for file uploads (JSON only, max file size)

**7.2 Loading States**

- Skeleton loaders for file previews
- Spinner for adapter loading in chatbot
- Progress bars with percentage text
- Disabled buttons during operations

**7.3 Responsive Design**

- Mobile-friendly layout (stack step cards vertically)
- Responsive typography and spacing
- Touch-friendly button sizes
- Collapsible step configurations on mobile

**7.4 Accessibility**

- ARIA labels for all interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader announcements for status changes

## Critical Files to Create

### Backend
1. `backend/app/main.py` - FastAPI app, routes, CORS, WebSocket endpoints
2. `backend/app/services/pipeline_executor.py` - Subprocess execution for all 5 steps
3. `backend/app/services/temp_manager.py` - Temporary directory lifecycle management
4. `backend/app/core/websocket_manager.py` - Real-time progress broadcasting
5. `backend/app/services/adapter_inference.py` - Load adapter and run inference for chatbot
6. `backend/requirements.txt` - All Python dependencies

### Frontend
1. `frontend/src/components/pipeline/PipelineVisualizer.tsx` - Main pipeline UI
2. `frontend/src/components/pipeline/StepCard.tsx` - Individual step cards
3. `frontend/src/components/pipeline/AnimatedWire.tsx` - Animated wire connections
4. `frontend/src/components/chat/ChatInterface.tsx` - Chatbot UI
5. `frontend/src/store/pipelineStore.ts` - Zustand state management
6. `frontend/src/hooks/useWebSocket.ts` - WebSocket integration
7. `frontend/src/services/api.ts` - API client with all endpoints
8. `frontend/package.json` - Dependencies (React, Tailwind, shadcn, etc.)

### Configuration
1. `backend/.env.example` - Environment variables template
2. `frontend/components.json` - shadcn/ui configuration
3. `frontend/tailwind.config.js` - Tailwind customization
4. `docker-compose.yml` - Optional Docker setup

## Verification Steps

After implementation, verify:

1. **File Upload**: Upload raw JSON files, see session created
2. **Step 1**: Execute sanitization, see real-time progress, preview sanitized outputs
3. **Step 2**: Configure LLM (GPT-4o), execute tagging, see progress, preview tagged outputs
4. **Step 3**: Execute exporting, preview ShareGPT format
5. **Step 4**: Select model (Qwen), execute training, see loss curve, download adapter
6. **Auto Mode**: Toggle on, verify steps execute sequentially without manual trigger
7. **Chatbot**: Load adapter, send messages, verify multi-turn conversation works
8. **Cleanup**: Reset pipeline, verify all temp files deleted
9. **Session Warning**: Verify warning banner appears when session active

## Dependencies

### Backend (`backend/requirements.txt`)
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
websockets>=12.0
python-multipart>=0.0.6
pydantic>=2.5.0
python-dotenv>=1.0.0
aiofiles>=23.2.1

# Existing dependencies
pyyaml>=6.0.0
transformers>=4.41.0
torch>=2.0.0
peft>=0.11.0
accelerate>=0.30.0
```

### Frontend (`frontend/package.json`)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.4.7",
    "framer-motion": "^10.18.0",
    "recharts": "^2.10.3",
    "react-json-view": "^1.21.3",
    "lucide-react": "^0.303.0",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-select": "^2.0.0",
    "@radix-ui/react-switch": "^1.0.3",
    "@radix-ui/react-tabs": "^1.0.4",
    "@radix-ui/react-slider": "^1.1.2",
    "axios": "^1.6.5"
  },
  "devDependencies": {
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.11",
    "tailwindcss": "^3.4.1",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.16"
  }
}
```

## Summary

This plan creates a comprehensive web dashboard that:

✅ Orchestrates all 5 pipeline steps with visual progress tracking
✅ Uses temporary file storage with automatic cleanup
✅ Provides animated pipeline visualization with status indicators
✅ Allows file preview and adapter download
✅ Includes multi-turn chatbot for testing adapters
✅ Supports auto mode for sequential execution
✅ Warns users about temporary nature of files
✅ Integrates with existing CLI scripts via subprocess execution
✅ Uses modern tech stack (React, FastAPI, WebSocket for real-time updates)

The implementation preserves all existing CLI functionality while adding a polished, intuitive web interface for the entire training pipeline.
