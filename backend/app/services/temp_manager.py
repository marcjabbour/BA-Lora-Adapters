"""Temporary directory lifecycle management."""

import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from app.config import settings
from app.models.state import SessionState, StepState, StepStatus


class TempManager:
    """Manages temporary directories for pipeline sessions."""

    def __init__(self):
        """Initialize the temporary directory manager."""
        self.sessions: Dict[str, SessionState] = {}
        self.cleanup_threshold = timedelta(hours=settings.session_cleanup_hours)

    async def create_session(self) -> SessionState:
        """
        Create a new session with temporary directory structure.

        Returns:
            SessionState: The created session state
        """
        session_id = str(uuid.uuid4())
        temp_dir = settings.temp_base_dir / f"lora-pipeline-{session_id}"

        # Create directory structure
        temp_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / "raw").mkdir(exist_ok=True)

        # Create output directories for each step
        for i in range(1, 5):
            step_names = {
                1: "Step-1-Sanitization",
                2: "Step-2-Tagging",
                3: "Step-3-Exporting",
                4: "Step-4-Training"
            }
            (temp_dir / step_names[i] / "output").mkdir(parents=True, exist_ok=True)

        # Initialize session state
        steps = {
            1: StepState(step_id=1, name="Sanitization"),
            2: StepState(step_id=2, name="Tagging"),
            3: StepState(step_id=3, name="Exporting"),
            4: StepState(step_id=4, name="Training"),
            5: StepState(step_id=5, name="Serving (Future)"),
        }

        session = SessionState(
            session_id=session_id,
            temp_dir=temp_dir,
            steps=steps,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )

        self.sessions[session_id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get session by ID and update last activity time.

        Args:
            session_id: Session identifier

        Returns:
            SessionState if found, None otherwise
        """
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session

    async def cleanup_session(self, session_id: str) -> bool:
        """
        Delete all temporary files for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        # Delete temporary directory
        if session.temp_dir.exists():
            shutil.rmtree(session.temp_dir, ignore_errors=True)

        # Remove from sessions dict
        del self.sessions[session_id]
        return True

    async def cleanup_expired_sessions(self):
        """Background task to cleanup old sessions."""
        now = datetime.now()
        expired = [
            sid for sid, state in self.sessions.items()
            if now - state.last_activity > self.cleanup_threshold
        ]

        for sid in expired:
            await self.cleanup_session(sid)

        if expired:
            print(f"Cleaned up {len(expired)} expired session(s)")

    def get_step_input_dir(self, session: SessionState, step_id: int) -> Path:
        """
        Get input directory for a step.

        Args:
            session: Session state
            step_id: Step number

        Returns:
            Path to input directory
        """
        if step_id == 1:
            return session.temp_dir / "raw"
        elif step_id == 2:
            return session.temp_dir / "Step-1-Sanitization" / "output"
        elif step_id == 3:
            return session.temp_dir / "Step-2-Tagging" / "output"
        elif step_id == 4:
            return session.temp_dir / "Step-3-Exporting" / "output"
        else:
            raise ValueError(f"Invalid step_id: {step_id}")

    def get_step_output_dir(self, session: SessionState, step_id: int) -> Path:
        """
        Get output directory for a step.

        Args:
            session: Session state
            step_id: Step number

        Returns:
            Path to output directory
        """
        step_names = {
            1: "Step-1-Sanitization",
            2: "Step-2-Tagging",
            3: "Step-3-Exporting",
            4: "Step-4-Training"
        }

        if step_id not in step_names:
            raise ValueError(f"Invalid step_id: {step_id}")

        return session.temp_dir / step_names[step_id] / "output"


# Global instance
temp_manager = TempManager()
