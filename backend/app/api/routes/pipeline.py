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

    # Upload files
    count = await file_handler.upload_files(session, files)

    return SessionResponse(
        session_id=session.session_id,
        message=f"Session created. Uploaded {count} files."
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

    # Check if previous step is completed (except for step 1)
    if step_id > 1:
        prev_step = session.steps.get(step_id - 1)
        if prev_step.status != StepStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Previous step must be completed first"
            )

    # Execute step in background
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
