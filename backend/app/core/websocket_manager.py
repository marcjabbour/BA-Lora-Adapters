"""WebSocket connection and message broadcasting."""

from datetime import datetime
from typing import Dict, List

from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections and broadcasts messages."""

    def __init__(self):
        """Initialize the WebSocket manager."""
        # Map session_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """
        Accept and register a WebSocket connection.

        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []

        self.active_connections[session_id].append(websocket)
        print(f"WebSocket connected for session {session_id}")

    async def disconnect(self, session_id: str, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)

            # Clean up empty list
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

        print(f"WebSocket disconnected for session {session_id}")

    async def broadcast_progress(
        self,
        session_id: str,
        step_id: int,
        progress: float,
        message: str = ""
    ):
        """
        Broadcast progress update to all connections for a session.

        Args:
            session_id: Session identifier
            step_id: Step number
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        payload = {
            "type": "progress",
            "step_id": step_id,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_to_session(session_id, payload)

    async def broadcast_status(
        self,
        session_id: str,
        step_id: int,
        status: str
    ):
        """
        Broadcast status change to all connections for a session.

        Args:
            session_id: Session identifier
            step_id: Step number
            status: New status (pending, running, completed, failed)
        """
        payload = {
            "type": "status",
            "step_id": step_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_to_session(session_id, payload)

    async def broadcast_log(
        self,
        session_id: str,
        step_id: int,
        log: str
    ):
        """
        Broadcast log message to all connections for a session.

        Args:
            session_id: Session identifier
            step_id: Step number
            log: Log message
        """
        payload = {
            "type": "log",
            "step_id": step_id,
            "log": log,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_to_session(session_id, payload)

    async def broadcast_error(
        self,
        session_id: str,
        step_id: int,
        error: str
    ):
        """
        Broadcast error message to all connections for a session.

        Args:
            session_id: Session identifier
            step_id: Step number
            error: Error message
        """
        payload = {
            "type": "error",
            "step_id": step_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_to_session(session_id, payload)

    async def _broadcast_to_session(self, session_id: str, payload: dict):
        """
        Send message to all connections for a session.

        Args:
            session_id: Session identifier
            payload: Message payload
        """
        if session_id not in self.active_connections:
            return

        # Send to all connections, removing stale ones
        stale_connections = []

        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_json(payload)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                stale_connections.append(websocket)

        # Clean up stale connections
        for websocket in stale_connections:
            await self.disconnect(session_id, websocket)


# Global instance
ws_manager = WebSocketManager()
