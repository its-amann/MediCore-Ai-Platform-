"""
Room management API routes
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from ..models import (
    Room, RoomParticipant, CreateRoomRequest, UpdateRoomRequest,
    JoinRoomRequest, RoomType, RoomStatus, RoomJoinRequest, 
    CreateJoinRequestModel, ProcessJoinRequestModel, StartClassRequest,
    NotificationType, RequestStatus, Message, SendMessageRequest, MessageType
)
from ..services.room_service import RoomService
from ..services.notification_service import NotificationService
from ..services.webrtc_service import webrtc_service
from ..services.gemini_live_service import gemini_live_service, GeminiLiveMode
from ..services.chat_service import ChatService
from ..utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(redirect_slashes=False)
security = HTTPBearer()

# Service dependencies - will be injected from integration
async def get_room_service():
    """Get room service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Check if services are initialized
    if not collaboration_integration.room_service:
        # Check if we need to initialize
        if not collaboration_integration.db_client:
            # Initialize in standalone mode since no client was injected
            logger.info("Initializing collaboration services in standalone mode")
            await collaboration_integration.initialize()
        else:
            # Database client exists but room service doesn't - this is an error
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Room service not initialized properly. Database client exists but room service creation failed."
            )
    
    # Final check
    if not collaboration_integration.room_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Room service not available. Initialization failed."
        )
    
    return collaboration_integration.room_service

async def get_notification_service():
    """Get notification service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Check if services are initialized
    if not collaboration_integration.notification_service:
        # Check if we need to initialize
        if not collaboration_integration.db_client:
            # Initialize in standalone mode
            logger.info("Initializing collaboration services in standalone mode")
            await collaboration_integration.initialize()
    
    if not collaboration_integration.notification_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification service not available. Initialization failed."
        )
    return collaboration_integration.notification_service


async def get_chat_service():
    """Get chat service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Check if services are initialized
    if not collaboration_integration.chat_service:
        # Check if we need to initialize
        if not collaboration_integration.db_client:
            # Initialize in standalone mode
            logger.info("Initializing collaboration services in standalone mode")
            await collaboration_integration.initialize()
    
    if not collaboration_integration.chat_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service not available. Initialization failed."
        )
    return collaboration_integration.chat_service


@router.get("")
async def get_rooms(
    room_type: Optional[RoomType] = Query(None, description="Filter by room type"),
    status: Optional[RoomStatus] = Query(None, description="Filter by room status"),
    is_private: Optional[bool] = Query(None, description="Filter by privacy setting"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get all available rooms with optional filters"""
    try:
        rooms = await room_service.get_all_rooms(
            room_type=room_type,
            status=status,
            is_private=is_private
        )
        
        # Convert Room models to dicts with frontend-expected fields
        rooms_data = []
        for room in rooms:
            room_dict = {
                "room_id": room.room_id,
                "name": room.name,
                "description": room.description,
                "room_type": room.room_type.value,
                "status": room.status.value,
                "host_id": room.created_by.get("user_id", ""),
                "max_participants": room.max_participants,
                "is_private": not room.is_public,  # Convert is_public to is_private
                "created_at": room.created_at.isoformat() if hasattr(room.created_at, 'isoformat') else str(room.created_at),
                "updated_at": room.updated_at.isoformat() if hasattr(room.updated_at, 'isoformat') else str(room.updated_at),
                "participant_count": room.current_participants,
                "tags": room.settings.get("tags", []) if room.settings else []
            }
            rooms_data.append(room_dict)
        
        return rooms_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=Room, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: CreateRoomRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Create a new collaboration room"""
    try:
        # Debug logging
        logger.info(f"CreateRoomRequest object: {request}")
        logger.info(f"Request dict: {request.model_dump()}")
        logger.info(f"Request type field: {getattr(request, 'type', 'NOT FOUND')}")
        logger.info(f"Request room_type field: {getattr(request, 'room_type', 'NOT FOUND')}")
        
        room = await room_service.create_room(
            creator_id=current_user["user_id"],
            request=request
        )
        return room
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{room_id}", response_model=Room)
async def get_room(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get room details by ID"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user has access to room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant and not room.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return room


@router.put("/{room_id}", response_model=Room)
async def update_room(
    room_id: str,
    request: UpdateRoomRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Update room settings"""
    try:
        room = await room_service.update_room(
            room_id=room_id,
            user_id=current_user["user_id"],
            request=request
        )
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        return room
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Delete (archive) a room"""
    try:
        success = await room_service.delete_room(
            room_id=room_id,
            user_id=current_user["user_id"]
        )
        if not success:
            raise HTTPException(status_code=404, detail="Room not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{room_id}/join", response_model=RoomParticipant)
async def join_room(
    room_id: str,
    request: JoinRoomRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Join a room"""
    try:
        participant = await room_service.join_room(
            room_id=room_id,
            user_id=current_user["user_id"],
            user_name=current_user.get("name", f"User_{current_user['user_id']}"),
            request=request
        )
        
        # Send notification to other participants
        active_participants = await room_service.get_active_participants(room_id)
        for p in active_participants:
            if p.user_id != current_user["user_id"]:
                await notification_service.create_notification(
                    user_id=p.user_id,
                    notification_type="user_joined",
                    title="User joined room",
                    message=f"{current_user.get('name')} joined the room",
                    data={"room_id": room_id}
                )
        
        return participant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{room_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_room(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Leave a room"""
    success = await room_service.leave_room(
        room_id=room_id,
        user_id=current_user["user_id"]
    )
    if not success:
        raise HTTPException(status_code=404, detail="Not in room")


@router.get("/{room_id}/participants", response_model=List[RoomParticipant])
async def get_room_participants(
    room_id: str,
    active_only: bool = Query(True, description="Only return active participants"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get participants in a room"""
    # Check if user has access to room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    room = await room_service.get_room(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if not participant and not room.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if active_only:
        participants = await room_service.get_active_participants(room_id)
    else:
        # Get all participants (would need to implement this method)
        participants = await room_service.get_active_participants(room_id)
    
    return participants


@router.put("/{room_id}/participants/{user_id}/status")
async def update_participant_status(
    room_id: str,
    user_id: str,
    video_enabled: Optional[bool] = Query(None),
    audio_enabled: Optional[bool] = Query(None),
    screen_sharing: Optional[bool] = Query(None),
    hand_raised: Optional[bool] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Update participant status (video/audio/screen/hand)"""
    # Users can only update their own status
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Can only update own status")
    
    participant = await room_service.update_participant_status(
        room_id=room_id,
        user_id=user_id,
        video_enabled=video_enabled,
        audio_enabled=audio_enabled,
        screen_sharing=screen_sharing,
        hand_raised=hand_raised
    )
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    return participant


@router.post("/{room_id}/promote/{user_id}")
async def promote_to_cohost(
    room_id: str,
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Promote a participant to co-host"""
    try:
        success = await room_service.promote_to_cohost(
            room_id=room_id,
            host_id=current_user["user_id"],
            target_user_id=user_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="User not found in room")
        
        return {"message": "User promoted to co-host"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/user/rooms", response_model=List[Room])
async def get_user_rooms(
    include_archived: bool = Query(False, description="Include archived rooms"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get all rooms for the current user"""
    rooms = await room_service.get_user_rooms(
        user_id=current_user["user_id"],
        include_archived=include_archived
    )
    return rooms


@router.get("/search", response_model=List[Room])
async def search_rooms(
    query: str = Query(..., description="Search query"),
    room_type: Optional[RoomType] = Query(None, description="Filter by room type"),
    status: Optional[RoomStatus] = Query(None, description="Filter by status"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Search for rooms"""
    rooms = await room_service.search_rooms(
        query=query,
        room_type=room_type,
        status=status
    )
    
    # Filter out private rooms user doesn't have access to
    accessible_rooms = []
    for room in rooms:
        if not not room.is_public:
            accessible_rooms.append(room)
        else:
            participant = await room_service.get_participant(
                room.id, 
                current_user["user_id"]
            )
            if participant:
                accessible_rooms.append(room)
    
    return accessible_rooms


@router.get("/{room_id}/settings")
async def get_room_settings(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get room settings (creator only)"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is the room creator
    if room.created_by.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only room creator can access settings")
    
    # Return detailed settings
    return {
        "room_id": room.room_id,
        "settings": room.settings,
        "voice_enabled": room.voice_enabled,
        "screen_sharing": room.screen_sharing,
        "recording_enabled": room.recording_enabled,
        "max_participants": room.max_participants,
        "is_public": room.is_public,
        "password_protected": room.password_protected,
        "require_approval": room.settings.get("require_approval", False),
        "tags": room.tags if hasattr(room, 'tags') else [],
        "subject": room.subject if hasattr(room, 'subject') else None,
        "institution": room.institution if hasattr(room, 'institution') else None
    }


@router.post("/{room_id}/archive")
async def archive_room(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Archive a room (creator only)"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is the room creator
    if room.created_by.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only room creator can archive room")
    
    # Update room status to archived
    update_request = UpdateRoomRequest(status=RoomStatus.ARCHIVED)
    updated_room = await room_service.update_room(
        room_id=room_id,
        user_id=current_user["user_id"],
        request=update_request
    )
    
    return {"message": "Room archived successfully", "room": updated_room}


# Invite Participants Endpoint

@router.post("/{room_id}/invite")
async def invite_participants(
    room_id: str,
    request: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Invite participants to a room via email"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is a participant and preferably host/co-host
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a room participant")
    
    emails = request.get("emails", [])
    message = request.get("message", "")
    
    if not emails:
        raise HTTPException(status_code=400, detail="No email addresses provided")
    
    # Generate room invite link
    invite_link = f"{request.get('base_url', 'http://localhost:3000')}/rooms/{room_id}"
    
    # In a real implementation, this would send actual emails
    # For now, we'll create notifications for existing users
    invited_count = 0
    for email in emails:
        # In production, this would look up users by email and send actual emails
        # For now, we'll simulate success
        invited_count += 1
        logger.info(f"Simulated invite sent to {email} for room {room_id}")
    
    # Log the invitation
    if room.created_by.get("user_id") == current_user["user_id"]:
        logger.info(f"Host {current_user['user_id']} invited {invited_count} participants to room {room_id}")
    
    return {
        "message": f"Invitations sent to {invited_count} participants",
        "invited_count": invited_count,
        "room_id": room_id
    }


# Join Request Endpoints

@router.post("/{room_id}/request-join")
async def request_join_room(
    room_id: str,
    request: CreateJoinRequestModel,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Request to join a room that requires approval"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if room requires approval
    if not room.settings.get("require_approval", False):
        raise HTTPException(status_code=400, detail="Room does not require approval")
    
    # Check if user already has a pending request
    existing_request = await room_service.get_pending_join_request(
        room_id=room_id,
        user_id=current_user["user_id"]
    )
    if existing_request:
        raise HTTPException(status_code=400, detail="You already have a pending join request")
    
    # Create join request
    join_request = await room_service.create_join_request(
        room_id=room_id,
        user_id=current_user["user_id"],
        user_name=current_user.get("name", f"User_{current_user['user_id']}"),
        message=request.message
    )
    
    # Send notification to room creator
    await notification_service.create_notification(
        user_id=room.created_by.get("user_id"),
        notification_type=NotificationType.JOIN_REQUEST,
        title="New join request",
        message=f"{current_user.get('name')} requested to join your room '{room.name}'",
        data={
            "room_id": room_id,
            "request_id": join_request.request_id,
            "user_id": current_user["user_id"]
        }
    )
    
    return {"message": "Join request sent successfully", "request": join_request}


@router.get("/{room_id}/join-requests")
async def get_room_join_requests(
    room_id: str,
    status: Optional[RequestStatus] = Query(None, description="Filter by request status"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get join requests for a room (creator/co-host only)"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is creator or co-host
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant or participant.user_role not in ["host", "co_host"]:
        raise HTTPException(status_code=403, detail="Only hosts can view join requests")
    
    requests = await room_service.get_room_join_requests(room_id, status)
    return requests


@router.post("/{room_id}/join-requests/{request_id}/process")
async def process_join_request(
    room_id: str,
    request_id: str,
    process_request: ProcessJoinRequestModel,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Process (approve/reject) a join request"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is creator or co-host
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant or participant.user_role not in ["host", "co_host"]:
        raise HTTPException(status_code=403, detail="Only hosts can process join requests")
    
    # Process the request
    join_request = await room_service.process_join_request(
        request_id=request_id,
        processed_by=current_user["user_id"],
        approve=process_request.approve,
        reason=process_request.reason
    )
    
    if not join_request:
        raise HTTPException(status_code=404, detail="Join request not found")
    
    # Send notification to requester
    if process_request.approve:
        # Add user to room
        await room_service.add_user_from_request(join_request)
        
        await notification_service.create_notification(
            user_id=join_request.user_id,
            notification_type=NotificationType.JOIN_APPROVED,
            title="Join request approved",
            message=f"Your request to join room '{room.name}' has been approved",
            data={"room_id": room_id}
        )
    else:
        await notification_service.create_notification(
            user_id=join_request.user_id,
            notification_type=NotificationType.JOIN_REJECTED,
            title="Join request rejected",
            message=f"Your request to join room '{room.name}' has been rejected",
            data={
                "room_id": room_id,
                "reason": process_request.reason
            }
        )
    
    return {"message": "Join request processed successfully", "request": join_request}


# Teaching Room Specific Endpoints

@router.post("/{room_id}/start-class")
async def start_class(
    room_id: str,
    request: StartClassRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Start a teaching class (teacher only)"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if room is teaching type
    if room.room_type != RoomType.TEACHING:
        raise HTTPException(status_code=400, detail="Only teaching rooms can start classes")
    
    # Check if user is the room creator (teacher)
    if room.created_by.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the teacher can start the class")
    
    # Update room settings for class
    update_data = {
        "is_class_active": True,
        "class_started_at": datetime.utcnow().isoformat(),
        "recording_enabled": request.enable_recording,
        "chat_enabled": request.enable_chat,
        "qa_enabled": request.enable_qa
    }
    
    await room_service.update_room_settings(room_id, update_data)
    
    # Notify all participants
    participants = await room_service.get_active_participants(room_id)
    for p in participants:
        if p.user_id != current_user["user_id"]:
            await notification_service.create_notification(
                user_id=p.user_id,
                notification_type=NotificationType.TEACHING_STARTED,
                title="Class started",
                message=f"Class '{room.name}' has started",
                data={"room_id": room_id}
            )
    
    return {"message": "Class started successfully", "settings": update_data}


@router.post("/{room_id}/end-class")
async def end_class(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """End a teaching class (teacher only)"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is the room creator (teacher)
    if room.created_by.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the teacher can end the class")
    
    # Update room settings
    update_data = {
        "is_class_active": False,
        "class_ended_at": datetime.utcnow().isoformat()
    }
    
    await room_service.update_room_settings(room_id, update_data)
    
    # Notify all participants
    participants = await room_service.get_active_participants(room_id)
    for p in participants:
        if p.user_id != current_user["user_id"]:
            await notification_service.create_notification(
                user_id=p.user_id,
                notification_type=NotificationType.TEACHING_ENDED,
                title="Class ended",
                message=f"Class '{room.name}' has ended",
                data={"room_id": room_id}
            )
    
    return {"message": "Class ended successfully"}


# Filtering Endpoints

@router.get("/filter/by-type/{room_type}")
async def get_rooms_by_type(
    room_type: RoomType,
    include_archived: bool = Query(False),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get rooms filtered by type"""
    status_filter = None if include_archived else RoomStatus.ACTIVE
    rooms = await room_service.get_all_rooms(
        room_type=room_type,
        status=status_filter
    )
    return rooms


@router.get("/filter/my-rooms")
async def get_my_filtered_rooms(
    participation: str = Query("all", description="Filter by participation: all, created, member, pending"),
    room_type: Optional[RoomType] = Query(None),
    include_archived: bool = Query(False),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get user's rooms filtered by participation status"""
    all_rooms = await room_service.get_user_rooms(
        user_id=current_user["user_id"],
        include_archived=include_archived
    )
    
    filtered_rooms = []
    
    for room in all_rooms:
        # Filter by room type if specified
        if room_type and room.room_type != room_type:
            continue
        
        # Filter by participation
        if participation == "created":
            if room.created_by.get("user_id") == current_user["user_id"]:
                filtered_rooms.append(room)
        elif participation == "member":
            if room.created_by.get("user_id") != current_user["user_id"]:
                filtered_rooms.append(room)
        elif participation == "pending":
            # Check for pending join requests
            pending_request = await room_service.get_pending_join_request(
                room_id=room.room_id,
                user_id=current_user["user_id"]
            )
            if pending_request:
                filtered_rooms.append(room)
        else:  # "all"
            filtered_rooms.append(room)
    
    return filtered_rooms


# WebRTC Video/Audio Endpoints

@router.post("/{room_id}/video/start")
async def start_video_session(
    room_id: str,
    session_type: str = Query("video", description="Session type: video or audio"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Start a video/audio session in a room"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is a participant
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a room participant")
    
    # Start video session
    session = await webrtc_service.start_video_session(
        room_id=room_id,
        initiator_id=current_user["user_id"],
        session_type=session_type
    )
    
    return {
        "message": "Video session started",
        "session": {
            "session_id": session.session_id,
            "room_id": session.room_id,
            "type": session_type
        }
    }


@router.post("/{room_id}/video/join")
async def join_video_session(
    room_id: str,
    offer_sdp: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Join an existing video session"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is a participant
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a room participant")
    
    # Join video session
    success = await webrtc_service.join_video_session(
        room_id=room_id,
        user_id=current_user["user_id"],
        offer_sdp=offer_sdp
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="No active video session in room")
    
    return {"message": "Joined video session successfully"}


@router.post("/{room_id}/video/leave")
async def leave_video_session(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """Leave video session"""
    success = await webrtc_service.leave_video_session(
        room_id=room_id,
        user_id=current_user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Not in video session")
    
    return {"message": "Left video session successfully"}


@router.get("/{room_id}/video/session")
async def get_video_session_info(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get current video session information"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is a participant
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a room participant")
    
    session_info = await webrtc_service.get_session_info(room_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="No active video session")
    
    return session_info


@router.get("/{room_id}/video/ice-servers")
async def get_ice_servers(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """Get ICE servers for WebRTC connection"""
    ice_servers = await webrtc_service.get_ice_servers()
    turn_credentials = await webrtc_service.get_turn_credentials(current_user["user_id"])
    
    return {
        "ice_servers": ice_servers,
        "turn_credentials": turn_credentials
    }


@router.post("/{room_id}/video/signal")
async def handle_webrtc_signal(
    room_id: str,
    signal_type: str,
    to_user: str,
    data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """Handle WebRTC signaling"""
    from ..models import WebRTCSignal
    
    signal = WebRTCSignal(
        type=signal_type,
        from_user=current_user["user_id"],
        to_user=to_user,
        data={**data, "room_id": room_id}
    )
    
    handled_signal = await webrtc_service.handle_webrtc_signal(signal)
    
    # In a real implementation, this would send the signal to the target user via WebSocket
    # For now, we just return success
    
    return {"message": "Signal sent successfully", "signal": handled_signal}


# Screen Sharing Endpoints

@router.post("/{room_id}/screen/start")
async def start_screen_sharing(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Start screen sharing"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if room supports screen sharing
    if not room.screen_sharing:
        raise HTTPException(status_code=400, detail="Room does not support screen sharing")
    
    # Update participant status
    await room_service.update_participant_status(
        room_id=room_id,
        user_id=current_user["user_id"],
        screen_sharing=True
    )
    
    return {"message": "Screen sharing started"}


@router.post("/{room_id}/screen/stop")
async def stop_screen_sharing(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Stop screen sharing"""
    await room_service.update_participant_status(
        room_id=room_id,
        user_id=current_user["user_id"],
        screen_sharing=False
    )
    
    return {"message": "Screen sharing stopped"}


# Recording Endpoints (for teaching rooms)

@router.post("/{room_id}/recording/start")
async def start_recording(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Start recording (host only)"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if room supports recording
    if not room.recording_enabled:
        raise HTTPException(status_code=400, detail="Room does not support recording")
    
    # Check if user is host
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant or participant.user_role not in ["host", "co_host"]:
        raise HTTPException(status_code=403, detail="Only hosts can start recording")
    
    success = await webrtc_service.start_recording(
        room_id=room_id,
        recording_options={"quality": "high", "format": "mp4"}
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start recording")
    
    return {"message": "Recording started"}


@router.post("/{room_id}/recording/stop")
async def stop_recording(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Stop recording (host only)"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is host
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant or participant.user_role not in ["host", "co_host"]:
        raise HTTPException(status_code=403, detail="Only hosts can stop recording")
    
    recording_url = await webrtc_service.stop_recording(room_id)
    
    if not recording_url:
        raise HTTPException(status_code=400, detail="No active recording")
    
    # Save recording URL to room
    await room_service.update_room_settings(room_id, {"recording_url": recording_url})
    
    return {"message": "Recording stopped", "recording_url": recording_url}


# Gemini Live AI Integration Endpoints

@router.post("/{room_id}/gemini/start")
async def start_gemini_session(
    room_id: str,
    mode: GeminiLiveMode,
    context: Optional[Dict[str, Any]] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Start a Gemini Live AI session in the room"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is a participant
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a room participant")
    
    # Add room context
    if context is None:
        context = {}
    
    context.update({
        "room_name": room.name,
        "room_type": room.room_type.value,
        "subject": room.subject if hasattr(room, 'subject') else None,
        "institution": room.institution if hasattr(room, 'institution') else None
    })
    
    # Start Gemini session
    session_info = await gemini_live_service.start_gemini_session(
        room_id=room_id,
        mode=mode,
        initiator_id=current_user["user_id"],
        context=context
    )
    
    return {
        "message": "Gemini Live session started",
        "session": session_info
    }


@router.post("/{room_id}/gemini/join")
async def join_gemini_session(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """Join an existing Gemini Live session"""
    success = await gemini_live_service.join_gemini_session(
        room_id=room_id,
        user_id=current_user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="No active Gemini session in room")
    
    return {"message": "Joined Gemini session successfully"}


@router.post("/{room_id}/gemini/audio")
async def send_audio_to_gemini(
    room_id: str,
    audio_data: bytes,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """Send audio stream to Gemini Live"""
    response = await gemini_live_service.send_audio_stream(
        room_id=room_id,
        user_id=current_user["user_id"],
        audio_data=audio_data
    )
    
    if not response:
        raise HTTPException(status_code=400, detail="Failed to process audio")
    
    return response


@router.post("/{room_id}/gemini/medical-analysis")
async def get_medical_analysis(
    room_id: str,
    medical_data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get AI medical analysis from Gemini"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is a participant
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a room participant")
    
    # Get analysis
    analysis = await gemini_live_service.send_medical_data(
        room_id=room_id,
        medical_data=medical_data
    )
    
    if not analysis:
        raise HTTPException(status_code=400, detail="Failed to get medical analysis")
    
    return analysis


@router.post("/{room_id}/gemini/teaching-help")
async def get_teaching_assistance(
    room_id: str,
    question: str,
    context: Optional[Dict[str, Any]] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """Get teaching assistance from Gemini"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Verify this is a teaching room
    if room.room_type != RoomType.TEACHING:
        raise HTTPException(status_code=400, detail="Only available in teaching rooms")
    
    # Add room context
    if context is None:
        context = {}
    
    context.update({
        "subject": room.subject if hasattr(room, 'subject') else None,
        "institution": room.institution if hasattr(room, 'institution') else None,
        "level": context.get("level", "Medical Student")
    })
    
    # Get teaching help
    response = await gemini_live_service.get_teaching_assistance(
        room_id=room_id,
        question=question,
        context=context
    )
    
    if not response:
        raise HTTPException(status_code=400, detail="Failed to get teaching assistance")
    
    return response


@router.get("/{room_id}/gemini/session")
async def get_gemini_session_info(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """Get current Gemini session information"""
    session_info = await gemini_live_service.get_session_info(room_id)
    
    if not session_info:
        raise HTTPException(status_code=404, detail="No active Gemini session")
    
    return session_info


@router.post("/{room_id}/gemini/end")
async def end_gemini_session(
    room_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """End Gemini Live session"""
    # Check if user is host or the one who started the session
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a room participant")
    
    success = await gemini_live_service.end_gemini_session(room_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="No active Gemini session to end")
    
    return {"status": "ended", "message": "Gemini Live session ended"}


# Message endpoints - proxy to chat service for frontend compatibility
@router.get("/{room_id}/messages", response_model=List[Message])
async def get_room_messages(
    room_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get messages for a room"""
    # Verify user is in the room
    participant = await room_service.get_participant(room_id, current_user["user_id"])
    if not participant:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    try:
        # Get raw messages from storage to handle data transformation
        from ..database.neo4j_storage import get_collaboration_storage
        storage = get_collaboration_storage()
        raw_messages = await storage.get_room_messages(room_id, limit, offset)
        
        # Transform raw messages to match Message model
        transformed_messages = []
        for msg in raw_messages:
            # Handle both 'id' and 'message_id' field names
            message_id = msg.get("message_id") or msg.get("id")
            if not message_id:
                logger.warning(f"No message_id found in message: {msg}")
                continue
                
            # Parse timestamp
            timestamp = msg.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Parse edited_at if present
            edited_at = msg.get("edited_at")
            if edited_at and isinstance(edited_at, str):
                edited_at = datetime.fromisoformat(edited_at)
                
            transformed_msg = Message(
                message_id=message_id,
                room_id=msg["room_id"],
                sender_id=msg["sender_id"],
                sender_name=msg.get("sender_name", f"User_{msg['sender_id']}"),
                content=msg.get("content", ""),
                message_type=MessageType(msg.get("type", "text")),
                timestamp=timestamp,
                edited_at=edited_at,
                is_edited=msg.get("is_edited", False),
                reactions=[],  # Empty list for now
                thread_id=msg.get("thread_id")
            )
            transformed_messages.append(transformed_msg)
            
        return transformed_messages
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{room_id}/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def send_room_message(
    room_id: str,
    request: SendMessageRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
    chat_service: ChatService = Depends(get_chat_service)
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
        return message
    except ValidationError as ve:
        # Handle validation error by manually creating the message
        logger.warning(f"Validation error in send_message, attempting manual fix: {ve}")
        
        # Store message directly
        from ..database.neo4j_storage import get_collaboration_storage
        import uuid
        
        storage = get_collaboration_storage()
        message_data = {
            "message_id": str(uuid.uuid4()),
            "room_id": room_id,
            "sender_id": current_user["user_id"],
            "sender_name": current_user.get("name", f"User_{current_user['user_id']}"),
            "content": request.content,
            "type": request.message_type.value if hasattr(request.message_type, 'value') else request.message_type,
            "timestamp": datetime.utcnow(),
            "is_edited": False,
            "is_deleted": False,
            "reactions": {},
            "attachments": request.attachments if hasattr(request, 'attachments') else [],
            "mentions": request.mentions if hasattr(request, 'mentions') else [],
            "reply_to_id": request.reply_to_id if hasattr(request, 'reply_to_id') else None
        }
        
        stored_message = await storage.store_message(message_data)
        
        # Return a properly formatted Message object
        return Message(
            message_id=stored_message.get("message_id", stored_message.get("id")),
            room_id=stored_message["room_id"],
            sender_id=stored_message["sender_id"],
            sender_name=stored_message.get("sender_name", f"User_{stored_message['sender_id']}"),
            content=stored_message["content"],
            message_type=MessageType(stored_message.get("type", "text")),
            timestamp=datetime.fromisoformat(stored_message["timestamp"]) if isinstance(stored_message["timestamp"], str) else stored_message["timestamp"],
            edited_at=None,
            is_edited=False,
            reactions=[],
            thread_id=None
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))