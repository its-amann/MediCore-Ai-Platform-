"""
Chat messaging API routes
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models import Message, SendMessageRequest, MessageType
from ..services.chat_service import ChatService
from ..services.room_service import RoomService
from ..services.ai_integration_service import AIIntegrationService
from ..utils.auth_utils import get_current_user

router = APIRouter(redirect_slashes=False)
security = HTTPBearer()

# Service dependencies - will be injected from integration
async def get_chat_service():
    """Get chat service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Try to initialize if not already done
    if not collaboration_integration.chat_service:
        try:
            # Check if running as part of unified system
            from app.core.database.neo4j_client import neo4j_client
            if neo4j_client and hasattr(neo4j_client, 'driver') and neo4j_client.driver:
                await collaboration_integration.initialize(unified_neo4j_client=neo4j_client)
        except ImportError:
            # Running standalone, initialize without unified client
            await collaboration_integration.initialize()
    
    if not collaboration_integration.chat_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service not available. Collaboration integration may not be initialized."
        )
    return collaboration_integration.chat_service

async def get_room_service():
    """Get room service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Try to initialize if not already done
    if not collaboration_integration.room_service:
        try:
            # Check if running as part of unified system
            from app.core.database.neo4j_client import neo4j_client
            if neo4j_client and hasattr(neo4j_client, 'driver') and neo4j_client.driver:
                await collaboration_integration.initialize(unified_neo4j_client=neo4j_client)
        except ImportError:
            # Running standalone, initialize without unified client
            await collaboration_integration.initialize()
    
    if not collaboration_integration.room_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Room service not available. Collaboration integration may not be initialized."
        )
    return collaboration_integration.room_service

async def get_ai_service():
    """Get AI integration service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Try to initialize if not already done
    if not collaboration_integration.ai_integration_service:
        try:
            # Check if running as part of unified system
            from app.core.database.neo4j_client import neo4j_client
            if neo4j_client and hasattr(neo4j_client, 'driver') and neo4j_client.driver:
                await collaboration_integration.initialize(unified_neo4j_client=neo4j_client)
        except ImportError:
            # Running standalone, initialize without unified client
            await collaboration_integration.initialize()
    
    if not collaboration_integration.ai_integration_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI integration service not available. Collaboration integration may not be initialized."
        )
    return collaboration_integration.ai_integration_service


@router.post("/rooms/{room_id}/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: str,
    request: SendMessageRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service),
    ai_service: AIIntegrationService = Depends(get_ai_service)
):
    """Send a message to a room"""
    # Verify user is in the room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant or not participant.is_active:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    try:
        message = await chat_service.send_message(
            room_id=room_id,
            sender_id=current_user["user_id"],
            sender_name=current_user.get("name", f"User_{current_user['user_id']}"),
            request=request
        )
        
        # Update AI context
        await ai_service.update_conversation_history(room_id, message)
        
        return message
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rooms/{room_id}/messages", response_model=List[Message])
async def get_messages(
    room_id: str,
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return"),
    before: Optional[datetime] = Query(None, description="Get messages before this timestamp"),
    after: Optional[datetime] = Query(None, description="Get messages after this timestamp"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service)
):
    """Get messages from a room"""
    # Verify user has access to room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    room = await room_service.get_room(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if not participant and not room.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await chat_service.get_messages(
        room_id=room_id,
        limit=limit,
        before_timestamp=before,
        after_timestamp=after
    )
    
    return messages


@router.get("/messages/{message_id}", response_model=Message)
async def get_message(
    message_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service)
):
    """Get a specific message"""
    message = await chat_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Verify user has access to the room
    participant = await room_service.get_participant(message.room_id, current_user["user_id"])
    room = await room_service.get_room(message.room_id)
    
    if not participant and not room.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return message


@router.put("/messages/{message_id}", response_model=Message)
async def update_message(
    message_id: str,
    content: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Update (edit) a message"""
    try:
        message = await chat_service.update_message(
            message_id=message_id,
            user_id=current_user["user_id"],
            new_content=content
        )
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        return message
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Delete a message"""
    try:
        success = await chat_service.delete_message(
            message_id=message_id,
            user_id=current_user["user_id"]
        )
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/messages/{message_id}/reactions/{emoji}")
async def add_reaction(
    message_id: str,
    emoji: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Add a reaction to a message"""
    # Validate emoji (basic validation)
    if len(emoji) > 2:
        raise HTTPException(status_code=400, detail="Invalid emoji")
    
    success = await chat_service.add_reaction(
        message_id=message_id,
        user_id=current_user["user_id"],
        emoji=emoji
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message": "Reaction added"}


@router.delete("/messages/{message_id}/reactions/{emoji}")
async def remove_reaction(
    message_id: str,
    emoji: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Remove a reaction from a message"""
    success = await chat_service.remove_reaction(
        message_id=message_id,
        user_id=current_user["user_id"],
        emoji=emoji
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Reaction not found")
    
    return {"message": "Reaction removed"}


@router.get("/rooms/{room_id}/messages/search", response_model=List[Message])
async def search_messages(
    room_id: str,
    query: str = Query(..., description="Search query"),
    sender_id: Optional[str] = Query(None, description="Filter by sender"),
    message_type: Optional[MessageType] = Query(None, description="Filter by message type"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service)
):
    """Search messages in a room"""
    # Verify user has access to room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    room = await room_service.get_room(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if not participant and not room.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await chat_service.search_messages(
        room_id=room_id,
        query=query,
        sender_id=sender_id,
        message_type=message_type
    )
    
    return messages


@router.get("/messages/{message_id}/thread", response_model=List[Message])
async def get_thread(
    message_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service)
):
    """Get all replies to a message (thread)"""
    # Get parent message to verify access
    parent = await chat_service.get_message(message_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Verify user has access to the room
    participant = await room_service.get_participant(parent.room_id, current_user["user_id"])
    room = await room_service.get_room(parent.room_id)
    
    if not participant and not room.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    thread_messages = await chat_service.get_thread_messages(message_id)
    return thread_messages


@router.post("/rooms/{room_id}/messages/read")
async def mark_messages_read(
    room_id: str,
    up_to_timestamp: datetime,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service)
):
    """Mark messages as read up to a timestamp"""
    # Verify user is in room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    count = await chat_service.mark_messages_as_read(
        room_id=room_id,
        user_id=current_user["user_id"],
        up_to_timestamp=up_to_timestamp
    )
    
    return {"messages_marked": count}


@router.get("/rooms/{room_id}/messages/unread-count")
async def get_unread_count(
    room_id: str,
    last_read: datetime = Query(..., description="Last read timestamp"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service)
):
    """Get count of unread messages"""
    # Verify user is in room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    count = await chat_service.get_unread_count(
        room_id=room_id,
        user_id=current_user["user_id"],
        last_read_timestamp=last_read
    )
    
    return {"unread_count": count}


@router.get("/rooms/{room_id}/messages/export")
async def export_chat_history(
    room_id: str,
    format: str = Query("json", description="Export format (json, csv, txt)"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    room_service: RoomService = Depends(get_room_service)
):
    """Export chat history"""
    # Verify user is in room and has appropriate permissions
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    # Only hosts and co-hosts can export
    if participant.user_role not in ["HOST", "CO_HOST"]:
        raise HTTPException(status_code=403, detail="Only hosts can export chat history")
    
    try:
        export_data = await chat_service.export_chat_history(
            room_id=room_id,
            format=format
        )
        return export_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# AI Integration endpoints

@router.post("/rooms/{room_id}/ai/suggestions")
async def get_ai_suggestions(
    room_id: str,
    query: str = Query(..., description="Query for AI suggestions"),
    suggestion_type: str = Query("general", description="Type of suggestions needed"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    ai_service: AIIntegrationService = Depends(get_ai_service)
):
    """Get AI suggestions based on conversation context"""
    # Verify user is in room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    suggestions = await ai_service.get_ai_suggestions(
        room_id=room_id,
        query=query,
        suggestion_type=suggestion_type
    )
    
    return suggestions


@router.get("/rooms/{room_id}/ai/analysis")
async def analyze_conversation(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    ai_service: AIIntegrationService = Depends(get_ai_service)
):
    """Analyze conversation for insights"""
    # Verify user is in room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    analysis = await ai_service.analyze_conversation(room_id)
    return analysis


@router.get("/rooms/{room_id}/ai/summary")
async def generate_summary(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    ai_service: AIIntegrationService = Depends(get_ai_service)
):
    """Generate conversation summary"""
    # Verify user is in room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    summary = await ai_service.generate_summary(room_id)
    return summary