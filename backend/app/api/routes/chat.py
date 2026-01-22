"""
Chat API routes for testing trained LoRA adapters.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from ...services.adapter_inference import AdapterInferenceService
from ...core.state_manager import state_manager

router = APIRouter()
inference_service = AdapterInferenceService()


class LoadAdapterRequest(BaseModel):
    session_id: str


class SendMessageRequest(BaseModel):
    session_id: str
    message: str


class ClearChatRequest(BaseModel):
    session_id: str


class ChatResponse(BaseModel):
    response: str
    conversation_history: List[Dict[str, str]]


@router.post("/load")
async def load_adapter(request: LoadAdapterRequest):
    """
    Load the trained LoRA adapter for a session.
    """
    session = state_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if Step 4 (Training) is completed
    step_4 = session.steps.get(4)
    if not step_4 or step_4.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Step 4 (Training) must be completed before loading adapter"
        )

    # Get adapter path
    adapter_path = session.temp_dir / "Step-4-Training" / "output"
    if not adapter_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Adapter files not found"
        )

    try:
        # Load the adapter
        await inference_service.load_adapter(
            session_id=request.session_id,
            adapter_path=str(adapter_path)
        )

        return {
            "status": "success",
            "message": "Adapter loaded successfully",
            "adapter_path": str(adapter_path)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load adapter: {str(e)}"
        )


@router.post("/message", response_model=ChatResponse)
async def send_message(request: SendMessageRequest):
    """
    Send a message to the loaded adapter and get a response.
    """
    if not inference_service.is_loaded(request.session_id):
        raise HTTPException(
            status_code=400,
            detail="Adapter not loaded. Call /api/chat/load first"
        )

    try:
        # Generate response
        response = await inference_service.generate_response(
            session_id=request.session_id,
            user_message=request.message
        )

        # Get conversation history
        history = inference_service.get_conversation_history(request.session_id)

        return ChatResponse(
            response=response,
            conversation_history=history
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.post("/clear")
async def clear_chat(request: ClearChatRequest):
    """
    Clear the conversation history for a session.
    """
    if not inference_service.is_loaded(request.session_id):
        raise HTTPException(
            status_code=400,
            detail="Adapter not loaded"
        )

    try:
        inference_service.clear_history(request.session_id)
        return {
            "status": "success",
            "message": "Conversation history cleared"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear history: {str(e)}"
        )
