"""Pipeline state models."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Status of a pipeline step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepState(BaseModel):
    """State of a single pipeline step."""
    step_id: int = Field(..., description="Step number (1-5)")
    name: str = Field(..., description="Human-readable step name")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current status")
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    output_files: List[str] = Field(default_factory=list, description="List of output files")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Step-specific configuration")
    started_at: Optional[datetime] = Field(default=None, description="When step started")
    completed_at: Optional[datetime] = Field(default=None, description="When step completed")


class SessionState(BaseModel):
    """State of a pipeline session."""
    session_id: str = Field(..., description="Unique session identifier")
    temp_dir: Path = Field(..., description="Temporary directory path")
    auto_mode: bool = Field(default=False, description="Auto-execute next step")
    current_step: Optional[int] = Field(default=None, description="Currently executing step")
    steps: Dict[int, StepState] = Field(..., description="State of all steps")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    last_activity: datetime = Field(default_factory=datetime.now, description="Last activity time")

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


class Step2Config(BaseModel):
    """Configuration for Step 2 (LLM Tagging)."""
    llm_provider: str = Field(default="openai", description="LLM provider")
    model: str = Field(default="gpt-4o", description="Model name")
    rewrite_threshold: int = Field(default=6, ge=1, le=10, description="Quality threshold")


class Step4Config(BaseModel):
    """Configuration for Step 4 (Training)."""
    base_model: str = Field(default="Qwen/Qwen2-1.5B-Instruct", description="Base model name")
    epochs: int = Field(default=3, ge=1, le=10, description="Number of training epochs")
    batch_size: int = Field(default=4, ge=1, le=16, description="Training batch size")
    learning_rate: float = Field(default=5e-5, gt=0, description="Learning rate")
