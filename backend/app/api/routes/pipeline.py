"""Pipeline control endpoints."""

import asyncio
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks

from app.models.pipeline import (
    SessionResponse,
    StatusResponse,
    StepExecutionRequest,
    StepExecutionResponse,
    ToggleAutoModeRequest,
)
from app.models.state import StepStatus
from app.services.file_handler import file_handler
from app.services.pipeline_executor import pipeline_executor
from app.services.temp_manager import temp_manager

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/upload", response_model=SessionResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload raw transcript files and create a new session.

    Args:
        files: List of JSON files to upload

    Returns:
        Session information
    """
    # Create new session
    session = await temp_manager.create_session()
    print(f"📁 Created new session: {session.session_id}")

    # Upload files
    count = await file_handler.upload_files(session, files, target_step=1)
    print(f"✅ Uploaded {count} files to session {session.session_id}")
    print(f"💡 Frontend will automatically trigger Step 1 execution.")

    return SessionResponse(
        session_id=session.session_id,
        message=f"Session created. Uploaded {count} files."
    )


@router.post("/upload/step/{step_id}", response_model=SessionResponse)
async def upload_files_to_step(step_id: int, files: List[UploadFile] = File(...)):
    """
    Upload files directly to a specific step, skipping previous steps.

    Args:
        step_id: Target step number (2-4)
        files: List of files to upload

    Returns:
        Session information
    """
    if step_id < 2 or step_id > 4:
        raise HTTPException(
            status_code=400,
            detail="Step ID must be between 2 and 4 for direct upload"
        )

    # Create new session or get existing one
    session = await temp_manager.create_session()
    print(f"📁 Created new session: {session.session_id}")

    # Upload files to target step
    count = await file_handler.upload_files(session, files, target_step=step_id)
    print(f"✅ Uploaded {count} files to step {step_id} for session {session.session_id}")

    # Mark all previous steps as skipped and broadcast status
    from app.core.websocket_manager import ws_manager
    for prev_step_id in range(1, step_id):
        session.steps[prev_step_id].status = StepStatus.SKIPPED
        await ws_manager.broadcast_status(session.session_id, prev_step_id, StepStatus.SKIPPED.value)
        print(f"⏭️  Marked Step {prev_step_id} as skipped")

    return SessionResponse(
        session_id=session.session_id,
        message=f"Session created. Uploaded {count} files to Step {step_id}. Steps 1-{step_id-1} marked as skipped."
    )


@router.post("/step/{step_id}", response_model=StepExecutionResponse)
async def execute_step(
    step_id: int,
    request: StepExecutionRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute a specific pipeline step.

    Args:
        step_id: Step number (1-4)
        request: Execution request with session ID and config
        background_tasks: FastAPI background tasks

    Returns:
        Execution response
    """
    # Get session
    session = await temp_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if step can be executed
    step = session.steps.get(step_id)
    if not step:
        raise HTTPException(status_code=400, detail=f"Invalid step_id: {step_id}")

    if step.status == StepStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Step is already running")

    # Check if previous step is completed or skipped (except for step 1)
    if step_id > 1:
        prev_step = session.steps.get(step_id - 1)
        if prev_step.status not in [StepStatus.COMPLETED, StepStatus.SKIPPED]:
            raise HTTPException(
                status_code=400,
                detail=f"Previous step must be completed or skipped first"
            )

    # Execute step in background
    print(f"🚀 Starting Step {step_id} execution for session {session.session_id}")
    background_tasks.add_task(
        pipeline_executor.execute_step,
        session,
        step_id,
        request.config
    )

    return StepExecutionResponse(
        message=f"Step {step_id} execution started",
        step_id=step_id,
        status=StepStatus.RUNNING
    )


@router.post("/toggle-auto")
async def toggle_auto_mode(request: ToggleAutoModeRequest):
    """
    Toggle auto mode for automatic step execution.

    Args:
        request: Toggle request with session ID and enabled flag

    Returns:
        Success message
    """
    session = await temp_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.auto_mode = request.enabled

    return {
        "message": f"Auto mode {'enabled' if request.enabled else 'disabled'}",
        "auto_mode": session.auto_mode
    }


@router.get("/status", response_model=StatusResponse)
async def get_status(session_id: str):
    """
    Get current pipeline status.

    Args:
        session_id: Session identifier

    Returns:
        Pipeline status
    """
    session = await temp_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Convert steps to dict format
    steps_dict = {
        step_id: {
            "step_id": step.step_id,
            "name": step.name,
            "status": step.status.value,
            "progress_percent": step.progress_percent,
            "output_files": file_handler.get_step_output_files(session, step_id),
            "error_message": step.error_message,
        }
        for step_id, step in session.steps.items()
    }

    return StatusResponse(
        session_id=session.session_id,
        auto_mode=session.auto_mode,
        current_step=session.current_step,
        steps=steps_dict
    )


@router.post("/reset")
async def reset_pipeline(session_id: str):
    """
    Reset pipeline and clear all temporary data.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    deleted = await temp_manager.cleanup_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Pipeline reset successfully"}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete session and cleanup temporary files.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    deleted = await temp_manager.cleanup_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session deleted successfully"}
