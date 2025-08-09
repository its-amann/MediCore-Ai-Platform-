"""
Chat routes for collaboration microservice
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import datetime

from app.microservices.collaboration.models import Message, MessageType
from app.api.routes.auth import get_current_active_user
from app.core.database.models import User

router = APIRouter(tags=["collaboration-chat"])
security = HTTPBearer()

# Service dependencies
async def get_chat_service():
    """Get chat service from collaboration integration"""
    from app.microservices.collaboration.integration import collaboration_integration
    
    if not collaboration_integration.chat_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service not available"
        )
    return collaboration_integration.chat_service


async def get_room_service():
    """Get room service from collaboration integration"""
    from app.microservices.collaboration.integration import collaboration_integration
    
    if not collaboration_integration.room_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Room service not available"
        )
    return collaboration_integration.room_service


@router.get("/rooms/{room_id}/messages", response_model=List[Message])
async def get_room_messages(
    room_id: str,
    limit: int = Query(50, ge=1, le=100),
    before_timestamp: Optional[datetime.datetime] = None,
    current_user: User = Depends(get_current_active_user),
    chat_service = Depends(get_chat_service),
    room_service = Depends(get_room_service)
):
    """Get messages for a room"""
    # Verify user has access to room
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    participant = await room_service.get_participant(room_id, current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    messages = await chat_service.get_messages(
        room_id=room_id,
        limit=limit,
        before_timestamp=before_timestamp
    )
    return messages


@router.post("/rooms/{room_id}/messages")
async def send_message(
    room_id: str,
    content: str = Form(...),
    message_type: MessageType = Form(MessageType.TEXT),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user),
    chat_service = Depends(get_chat_service),
    room_service = Depends(get_room_service)
):
    """Send a message to a room"""
    from app.microservices.collaboration.models import SendMessageRequest
    
    # Verify user has access to room
    participant = await room_service.get_participant(room_id, current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Handle file upload if present
    attachments = []
    if file:
        attachments.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(await file.read())
        })
    
    # Create SendMessageRequest
    request = SendMessageRequest(
        content=content,
        message_type=message_type,
        attachments=attachments
    )
    
    message = await chat_service.send_message(
        room_id=room_id,
        sender_id=current_user.user_id,
        sender_name=current_user.username,
        request=request
    )
    
    return message


@router.put("/messages/{message_id}")
async def update_message(
    message_id: str,
    content: str,
    current_user: User = Depends(get_current_active_user),
    chat_service = Depends(get_chat_service)
):
    """Update a message"""
    success = await chat_service.update_message(
        message_id=message_id,
        user_id=current_user.user_id,
        new_content=content
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or access denied"
        )
    
    return {"message": "Message updated successfully"}


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_active_user),
    chat_service = Depends(get_chat_service)
):
    """Delete a message"""
    success = await chat_service.delete_message(
        message_id=message_id,
        user_id=current_user.user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or access denied"
        )
    
    return {"message": "Message deleted successfully"}


@router.post("/rooms/{room_id}/typing")
async def send_typing_indicator(
    room_id: str,
    current_user: User = Depends(get_current_active_user),
    chat_service = Depends(get_chat_service),
    room_service = Depends(get_room_service)
):
    """Send typing indicator"""
    # Verify user has access to room
    participant = await room_service.get_participant(room_id, current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    await chat_service.send_typing_indicator(room_id, current_user.user_id)
    return {"message": "Typing indicator sent"}