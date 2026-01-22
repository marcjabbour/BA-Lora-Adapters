"""FastAPI main application."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import files, pipeline, chat
from app.config import settings
from app.core.websocket_manager import ws_manager
from app.services.temp_manager import temp_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Handles startup and shutdown tasks.
    """
    # Startup
    print("Starting LoRA Pipeline API...")

    # Start background task for cleaning up expired sessions
    cleanup_task = asyncio.create_task(cleanup_expired_sessions_task())

    yield

    # Shutdown
    print("Shutting down LoRA Pipeline API...")

    # Cancel cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Cleanup all active sessions
    for session_id in list(temp_manager.sessions.keys()):
        await temp_manager.cleanup_session(session_id)


async def cleanup_expired_sessions_task():
    """Background task to periodically cleanup expired sessions."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            await temp_manager.cleanup_expired_sessions()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in cleanup task: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pipeline.router)
app.include_router(files.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LoRA Training Pipeline API",
        "version": settings.api_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(temp_manager.sessions)
    }


@app.websocket("/ws/pipeline/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time pipeline updates.

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    # Verify session exists
    session = await temp_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Connect
    await ws_manager.connect(session_id, websocket)

    try:
        # Keep connection alive and listen for client messages
        while True:
            # Wait for any message from client (ping/pong)
            data = await websocket.receive_text()

            # Echo back if needed (for ping/pong)
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await ws_manager.disconnect(session_id, websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
