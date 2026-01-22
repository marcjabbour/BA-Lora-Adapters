"""Pipeline API request/response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .state import StepStatus


class SessionResponse(BaseModel):
    """Response after creating a session."""
    session_id: str
    message: str


class StatusResponse(BaseModel):
    """Pipeline status response."""
    session_id: Optional[str]
    auto_mode: bool
    current_step: Optional[int]
    steps: Dict[int, Dict[str, Any]]


class StepExecutionRequest(BaseModel):
    """Request to execute a step."""
    session_id: str
    config: Optional[Dict[str, Any]] = None


class StepExecutionResponse(BaseModel):
    """Response after starting step execution."""
    message: str
    step_id: int
    status: StepStatus


class ToggleAutoModeRequest(BaseModel):
    """Request to toggle auto mode."""
    session_id: str
    enabled: bool


class FilePreviewResponse(BaseModel):
    """Response with file preview data."""
    step_id: int
    files: List[Dict[str, Any]]
    total_files: int


class ChatLoadRequest(BaseModel):
    """Request to load adapter for chatbot."""
    session_id: str


class ChatMessageRequest(BaseModel):
    """Chat message request."""
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    """Chat message response."""
    role: str
    content: str


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # "progress", "status", "log", "error"
    step_id: Optional[int] = None
    progress: Optional[float] = None
    status: Optional[str] = None
    message: Optional[str] = None
    timestamp: str
