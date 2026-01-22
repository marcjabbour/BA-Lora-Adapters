# LoRA Training Pipeline - Backend API

FastAPI backend for orchestrating the LoRA training pipeline with real-time WebSocket updates.

## Features

- **Session Management**: Create temporary workspaces for pipeline execution
- **Pipeline Execution**: Execute all 5 pipeline steps via subprocess
- **Real-time Updates**: WebSocket-based progress tracking
- **File Operations**: Upload, preview, and download pipeline artifacts
- **Auto Mode**: Automatic sequential step execution
- **Temporary Storage**: All files stored in temporary directories with automatic cleanup

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=your-actual-key-here
ANTHROPIC_API_KEY=your-actual-key-here
```

### 3. Run the Server

```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## API Endpoints

### Pipeline Control

- `POST /api/pipeline/upload` - Upload raw transcript files and create session
- `POST /api/pipeline/step/{step_id}` - Execute a specific step
- `POST /api/pipeline/toggle-auto` - Toggle auto mode
- `GET /api/pipeline/status` - Get current pipeline status
- `POST /api/pipeline/reset` - Reset pipeline and clear temp data
- `DELETE /api/pipeline/session/{session_id}` - Delete session

### File Operations

- `GET /api/files/preview/{step_id}` - Preview step output files
- `GET /api/files/download/adapter` - Download trained adapter as zip
- `GET /api/files/download/step/{step_id}/{filename}` - Download specific file

### WebSocket

- `WS /ws/pipeline/{session_id}` - Real-time progress updates

## Architecture

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, WebSocket
│   ├── config.py                  # Configuration settings
│   ├── models/
│   │   ├── pipeline.py            # API request/response models
│   │   └── state.py               # Pipeline state models
│   ├── api/routes/
│   │   ├── pipeline.py            # Pipeline execution endpoints
│   │   └── files.py               # File upload/download/preview
│   ├── services/
│   │   ├── pipeline_executor.py   # Execute steps via subprocess
│   │   ├── file_handler.py        # File operations
│   │   └── temp_manager.py        # Temporary directory lifecycle
│   └── core/
│       └── websocket_manager.py   # WebSocket broadcasting
├── requirements.txt
└── .env.example
```

## Temporary File Structure

Each session creates a temporary workspace:

```
/tmp/lora-pipeline-{session_id}/
├── raw/                           # Uploaded files
├── Step-1-Sanitization/output/
├── Step-2-Tagging/output/
├── Step-3-Exporting/output/
└── Step-4-Training/output/
```

Sessions are automatically cleaned up after 24 hours of inactivity (configurable).

## WebSocket Message Format

The WebSocket sends JSON messages with the following types:

### Progress Update
```json
{
  "type": "progress",
  "step_id": 1,
  "progress": 45.5,
  "message": "Processing file 5/10",
  "timestamp": "2026-01-22T10:30:00"
}
```

### Status Change
```json
{
  "type": "status",
  "step_id": 1,
  "status": "completed",
  "timestamp": "2026-01-22T10:30:00"
}
```

### Log Message
```json
{
  "type": "log",
  "step_id": 1,
  "log": "Sanitizing transcript 5 of 10...",
  "timestamp": "2026-01-22T10:30:00"
}
```

### Error
```json
{
  "type": "error",
  "step_id": 1,
  "error": "Failed to parse file: invalid JSON",
  "timestamp": "2026-01-22T10:30:00"
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Type checking
mypy app/

# Linting
ruff check app/
```

## Notes

- All file uploads must be JSON format
- Maximum upload size: 500MB (configurable)
- Sessions expire after 24 hours of inactivity
- Server restart triggers cleanup of all temp directories
- Pipeline steps must be executed sequentially (step N requires step N-1 to complete)
