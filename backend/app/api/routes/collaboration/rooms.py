"""
Collaboration room routes for the Unified Medical AI Platform
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime

from app.microservices.collaboration.models import (
    Room, RoomType, RoomStatus, RoomParticipant
)
from app.core.database.models import User
from app.api.routes.auth import get_current_active_user

router = APIRouter(tags=["collaboration-rooms"])

# Service dependencies
async def get_room_service():
    """Get room service from collaboration integration"""
    from app.microservices.collaboration.integration import collaboration_integration
    
    if not collaboration_integration.room_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Room service not available"
        )
    return collaboration_integration.room_service


@router.post("", response_model=Room)
async def create_room(
    room_type: RoomType,
    name: str,
    description: Optional[str] = None,
    case_id: Optional[str] = None,
    scheduled_start: Optional[datetime] = None,
    scheduled_duration_minutes: Optional[int] = None,
    max_participants: Optional[int] = None,
    is_public: bool = True,
    room_password: Optional[str] = None,
    voice_enabled: bool = True,
    screen_sharing: bool = True,
    recording_enabled: bool = False,
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Create a new collaboration room"""
    from app.microservices.collaboration.models import CreateRoomRequest
    
    # Create request object
    request = CreateRoomRequest(
        type=room_type,
        name=name,
        description=description or "",
        max_participants=max_participants or 10,
        is_public=is_public,
        room_password=room_password,
        scheduled_start=scheduled_start,
        scheduled_end=None,  # Calculate from duration if needed
        voice_enabled=voice_enabled,
        screen_sharing=screen_sharing,
        recording_enabled=recording_enabled
    )
    
    room = await room_service.create_room(
        creator_id=current_user.user_id,
        request=request
    )
    return room


@router.get("", response_model=List[Room])
async def get_user_rooms(
    status: Optional[RoomStatus] = Query(None, description="Filter by room status"),
    room_type: Optional[RoomType] = Query(None, description="Filter by room type"),
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Get all rooms the user is a participant in"""
    rooms = await room_service.get_user_rooms(
        current_user.user_id,
        status=status,
        room_type=room_type
    )
    return rooms


@router.get("/{room_id}", response_model=Room)
async def get_room(
    room_id: str,
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Get room details"""
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Check if user is a participant
    participant = await room_service.get_participant(room_id, current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return room


@router.put("/{room_id}/status")
async def update_room_status(
    room_id: str,
    new_status: RoomStatus,
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Update room status"""
    # Check if user is the room creator
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    if room.created_by != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room creator can update status"
        )
    
    updated_room = await room_service.update_room_status(room_id, new_status)
    return updated_room


@router.post("/{room_id}/participants")
async def add_participant(
    room_id: str,
    user_id: str,
    is_presenter: bool = False,
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Add a participant to the room"""
    # Check if current user is the room creator
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    if room.created_by != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room creator can add participants"
        )
    
    participant = await room_service.add_participant(
        room_id=room_id,
        user_id=user_id,
        is_presenter=is_presenter
    )
    return participant


@router.delete("/{room_id}/participants/{user_id}")
async def remove_participant(
    room_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Remove a participant from the room"""
    # Check if current user is the room creator or removing themselves
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    if room.created_by != current_user.user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room creator can remove other participants"
        )
    
    success = await room_service.remove_participant(room_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    return {"message": "Participant removed successfully"}


@router.get("/{room_id}/participants", response_model=List[RoomParticipant])
async def get_room_participants(
    room_id: str,
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Get all participants in a room"""
    # Check if user is a participant
    participant = await room_service.get_participant(room_id, current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    participants = await room_service.get_room_participants(room_id)
    return participants


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    current_user: User = Depends(get_current_active_user),
    room_service = Depends(get_room_service)
):
    """Delete a room"""
    # Check if user is the room creator
    room = await room_service.get_room(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    if room.created_by != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room creator can delete the room"
        )
    
    success = await room_service.delete_room(room_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete room"
        )
    
    return {"message": "Room deleted successfully"}