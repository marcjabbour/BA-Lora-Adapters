"""
Global state management for pipeline sessions.

Maintains in-memory state for all active sessions.
"""

from typing import Dict, Optional
from ..models.state import SessionState


class StateManager:
    """Manages state for all active pipeline sessions."""

    def __init__(self):
        """Initialize the state manager."""
        self.sessions: Dict[str, SessionState] = {}

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get session state by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session state or None if not found
        """
        return self.sessions.get(session_id)

    def set_session(self, session_id: str, session: SessionState) -> None:
        """
        Store or update session state.

        Args:
            session_id: Session identifier
            session: Session state object
        """
        self.sessions[session_id] = session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session state.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_all_session_ids(self) -> list[str]:
        """
        Get list of all active session IDs.

        Returns:
            List of session IDs
        """
        return list(self.sessions.keys())


# Global state manager instance
state_manager = StateManager()
