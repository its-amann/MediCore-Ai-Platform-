"""
Chat routes for real-time messaging
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, Optional
import logging

from ...models.chat_models import MessageCreate, ChatMessage
from ...core.dependencies import get_storage_service, get_chat_service
from ...core.exceptions import CaseNotFoundError, DoctorServiceError
from ...services.chat.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/send", response_model=ChatMessage)
async def send_message(
    message: MessageCreate,
    stream: bool = False,
    chat_service: MessageProcessor = Depends(get_chat_service)
) -> ChatMessage:
    """
    Send a message and get AI response
    
    Args:
        message: Message to send
        stream: Whether to stream the response
        
    Returns:
        AI response message
    """
    try:
        if stream:
            # For streaming, we'll return the first chunk
            # Real streaming should use WebSocket
            response = await chat_service.process_message_stream(message)
            return response
        else:
            response = await chat_service.process_message(message)
            return response
            
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {message.case_id} not found"
        )
    except DoctorServiceError as e:
        logger.error(f"Doctor service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.post("/typing", response_model=Dict[str, Any])
async def send_typing_indicator(
    case_id: str,
    user_id: str,
    is_typing: bool = True,
    chat_service: MessageProcessor = Depends(get_chat_service)
) -> Dict[str, Any]:
    """
    Send typing indicator
    
    Args:
        case_id: Case ID
        user_id: User who is typing
        is_typing: Whether user is typing
        
    Returns:
        Success status
    """
    try:
        await chat_service.send_typing_indicator(case_id, user_id, is_typing)
        return {"status": "sent", "case_id": case_id, "user_id": user_id, "is_typing": is_typing}
        
    except Exception as e:
        logger.error(f"Error sending typing indicator: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send typing indicator"
        )