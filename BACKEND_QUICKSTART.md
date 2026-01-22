# Backend Quick Start Guide

This guide will help you get the FastAPI backend running in minutes.

## Prerequisites

- Python 3.9 or higher
- pip package manager
- OpenAI API key (for Step 2 - LLM Tagging)

## Setup Steps

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- FastAPI and Uvicorn (web framework)
- WebSocket support
- Pydantic (data validation)
- Existing project dependencies (transformers, torch, etc.)

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys:
```env
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

Optional settings (defaults are fine for most cases):
```env
API_HOST=0.0.0.0
API_PORT=8000
SESSION_CLEANUP_HOURS=24
```

### 5. Start the Server
```bash
python -m app.main
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using watchfiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
Starting LoRA Pipeline API...
INFO:     Application startup complete.
```

### 6. Verify It's Running

Open your browser and go to:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Testing the API

### Using the Interactive Docs

1. Go to http://localhost:8000/docs
2. Try the `/health` endpoint (click "Try it out" → "Execute")
3. You should see:
```json
{
  "status": "healthy",
  "active_sessions": 0
}
```

### Using cURL

Test the health endpoint:
```bash
curl http://localhost:8000/health
```

### Upload Files and Create Session

From the interactive docs:
1. Click on `POST /api/pipeline/upload`
2. Click "Try it out"
3. Upload your JSON transcript files
4. Click "Execute"
5. Note the `session_id` in the response

## WebSocket Testing

To test WebSocket connections, you can use a tool like `websocat`:

```bash
# Install websocat (on macOS)
brew install websocat

# Connect to WebSocket (replace SESSION_ID)
websocat ws://localhost:8000/ws/pipeline/SESSION_ID
```

Or use the browser console:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/pipeline/YOUR_SESSION_ID');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
ws.send('ping'); // Should receive 'pong'
```

## Common Issues

### Port Already in Use
If port 8000 is already taken:
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

Or update `.env`:
```env
API_PORT=8001
```

### Missing API Keys
If you see errors about missing API keys during Step 2:
1. Make sure `.env` file exists
2. Check `OPENAI_API_KEY` is set correctly
3. Restart the server

### Module Not Found
If you get import errors:
```bash
# Make sure you're in the backend directory
cd backend

# Reinstall dependencies
pip install -r requirements.txt
```

## Development Mode

The server runs in development mode by default with:
- Auto-reload on code changes
- Detailed error messages
- Interactive API documentation

## Next Steps

Once the backend is running:
1. ✅ Test the health endpoint
2. ✅ Explore the interactive API docs
3. ⏳ Build the frontend (Phase 2)
4. ⏳ Connect frontend to backend via WebSocket
5. ⏳ Test end-to-end pipeline execution

## Architecture Overview

```
Frontend (Phase 2)  →  Backend API  →  Pipeline Scripts
    ↓                      ↓              ↓
  React              FastAPI         Subprocess
  WebSocket          WebSocket       (Python scripts)
  State (Zustand)    State Manager   File Operations
```

## Useful Commands

```bash
# Start server
python -m app.main

# Start with custom host/port
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Check active sessions
curl http://localhost:8000/health

# View logs
# (logs print to console where you started the server)
```

## API Endpoints Reference

### Pipeline Control
- `POST /api/pipeline/upload` - Create session & upload files
- `POST /api/pipeline/step/{step_id}` - Execute a step
- `GET /api/pipeline/status?session_id=XXX` - Get status
- `POST /api/pipeline/toggle-auto` - Toggle auto mode
- `POST /api/pipeline/reset` - Reset pipeline
- `DELETE /api/pipeline/session/{session_id}` - Delete session

### Files
- `GET /api/files/preview/{step_id}?session_id=XXX` - Preview outputs
- `GET /api/files/download/adapter?session_id=XXX` - Download adapter
- `GET /api/files/download/step/{step_id}/{filename}?session_id=XXX` - Download file

### WebSocket
- `WS /ws/pipeline/{session_id}` - Real-time updates

## Support

For issues or questions:
1. Check the [Backend README](backend/README.md)
2. Review the [FULLSTACK_PLAN](FULLSTACK_PLAN.md)
3. Open an issue in the project repository

---

**Status**: Backend Phase 1 Complete ✅

**Next**: Frontend Phase 2 → See [FULLSTACK_PLAN.md](FULLSTACK_PLAN.md)
