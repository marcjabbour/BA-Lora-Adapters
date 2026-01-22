"""File operations endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.pipeline import FilePreviewResponse
from app.services.file_handler import file_handler
from app.services.temp_manager import temp_manager

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/preview/{step_id}", response_model=FilePreviewResponse)
async def preview_step_output(session_id: str, step_id: int, limit: int = 5):
    """
    Preview output files from a completed step.

    Args:
        session_id: Session identifier
        step_id: Step number
        limit: Maximum number of files to preview

    Returns:
        File preview data
    """
    session = await temp_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    preview_data = await file_handler.preview_step_output(session, step_id, limit)

    return FilePreviewResponse(**preview_data)


@router.get("/download/adapter")
async def download_adapter(session_id: str):
    """
    Download trained adapter as a zip file.

    Args:
        session_id: Session identifier

    Returns:
        Zip file with adapter files
    """
    session = await temp_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if step 4 is completed
    step4 = session.steps[4]
    if step4.status.value != "completed":
        raise HTTPException(
            status_code=400,
            detail="Training not completed yet"
        )

    # Create zip file
    zip_path = await file_handler.download_adapter(session)

    return FileResponse(
        path=zip_path,
        filename="lora_adapter.zip",
        media_type="application/zip"
    )


@router.get("/download/step/{step_id}/{filename}")
async def download_step_file(session_id: str, step_id: int, filename: str):
    """
    Download a specific file from step output.

    Args:
        session_id: Session identifier
        step_id: Step number
        filename: Filename to download

    Returns:
        The requested file
    """
    session = await temp_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        file_path = await file_handler.download_step_file(session, step_id, filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/json"
    )
