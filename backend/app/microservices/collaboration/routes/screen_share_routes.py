"""
Screen sharing routes for the collaboration microservice
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
import logging

from ..models.extended_models import (
    ScreenShareRequest, ScreenShareSession, ScreenSharePermission,
    ScreenShareQuality, ScreenShareEvent
)
from ..models import UserRole
from ..auth import get_current_user
from ..service_container import ServiceContainer
from ..exceptions import ValidationError, PermissionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screen-share", tags=["screen-share"])


@router.post("/start/{room_id}")
async def start_screen_share(
    room_id: str,
    request: ScreenShareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Start screen sharing in a room"""
    try:
        user_id = current_user["user_id"]
        
        # Verify user is in the room
        room_service = services.get_room_service()
        participant = await room_service.get_participant(room_id, user_id)
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a participant in this room"
            )
        
        # Start screen share
        screen_share_service = services.get_screen_share_service()
        session = await screen_share_service.start_screen_share(room_id, user_id, request)
        
        # Get WebRTC constraints
        constraints = await screen_share_service.get_capture_constraints(
            session.quality, request.enable_audio
        )
        
        return {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "status": session.status,
                "quality": session.quality,
                "source_type": session.source_type,
                "stream_id": session.stream_id
            },
            "constraints": constraints
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting screen share: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start screen share"
        )


@router.post("/stop/{room_id}")
async def stop_screen_share(
    room_id: str,
    session_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Stop screen sharing"""
    try:
        user_id = current_user["user_id"]
        
        screen_share_service = services.get_screen_share_service()
        success = await screen_share_service.stop_screen_share(room_id, user_id, session_id)
        
        return {
            "success": success,
            "message": "Screen share stopped" if success else "No active screen share found"
        }
        
    except Exception as e:
        logger.error(f"Error stopping screen share: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop screen share"
        )


@router.get("/sessions/{room_id}")
async def get_screen_share_sessions(
    room_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Get active screen sharing sessions in a room"""
    try:
        user_id = current_user["user_id"]
        
        # Verify user is in the room
        room_service = services.get_room_service()
        participant = await room_service.get_participant(room_id, user_id)
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a participant in this room"
            )
        
        screen_share_service = services.get_screen_share_service()
        sessions = await screen_share_service.get_active_sessions(room_id)
        
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "status": s.status,
                    "quality": s.quality,
                    "source_type": s.source_type,
                    "stream_id": s.stream_id,
                    "started_at": s.started_at.isoformat(),
                    "viewers": s.viewers,
                    "is_recording": s.is_recording,
                    "can_control": user_id in s.can_control
                }
                for s in sessions
            ],
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error getting screen share sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get screen share sessions"
        )


@router.put("/quality/{session_id}")
async def update_screen_share_quality(
    session_id: str,
    quality: ScreenShareQuality,
    custom_settings: Optional[Dict[str, Any]] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Update screen share quality settings"""
    try:
        user_id = current_user["user_id"]
        
        screen_share_service = services.get_screen_share_service()
        
        # Verify user owns the session or has permission
        session = await screen_share_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screen share session not found"
            )
        
        if session.user_id != user_id:
            # Check if user is host/co-host
            room_service = services.get_room_service()
            participant = await room_service.get_participant(session.room_id, user_id)
            if not participant or participant.role not in [UserRole.HOST, UserRole.CO_HOST]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the screen sharer or room host can update quality"
                )
        
        success = await screen_share_service.update_quality(session_id, quality, custom_settings)
        
        return {
            "success": success,
            "quality": quality,
            "custom_settings": custom_settings
        }
        
    except Exception as e:
        logger.error(f"Error updating screen share quality: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update screen share quality"
        )


@router.post("/control/grant/{session_id}")
async def grant_screen_control(
    session_id: str,
    grantee_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Grant control of shared screen to another user"""
    try:
        granter_id = current_user["user_id"]
        
        screen_share_service = services.get_screen_share_service()
        success = await screen_share_service.grant_control(session_id, granter_id, grantee_id)
        
        return {
            "success": success,
            "message": f"Control granted to {grantee_id}" if success else "Failed to grant control"
        }
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error granting screen control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant screen control"
        )


@router.post("/control/revoke/{session_id}")
async def revoke_screen_control(
    session_id: str,
    revokee_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Revoke control of shared screen from a user"""
    try:
        revoker_id = current_user["user_id"]
        
        screen_share_service = services.get_screen_share_service()
        success = await screen_share_service.revoke_control(session_id, revoker_id, revokee_id)
        
        return {
            "success": success,
            "message": f"Control revoked from {revokee_id}" if success else "Failed to revoke control"
        }
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error revoking screen control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke screen control"
        )


@router.post("/permissions/{room_id}")
async def set_screen_share_permission(
    room_id: str,
    target_user_id: str,
    permission: ScreenSharePermission,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Set screen share permissions for a user (host/co-host only)"""
    try:
        user_id = current_user["user_id"]
        
        # Verify user is host or co-host
        room_service = services.get_room_service()
        participant = await room_service.get_participant(room_id, user_id)
        if not participant or participant.role not in [UserRole.HOST, UserRole.CO_HOST]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only room hosts can set screen share permissions"
            )
        
        # Set granted_by field
        permission.granted_by = user_id
        permission.room_id = room_id
        permission.user_id = target_user_id
        
        screen_share_service = services.get_screen_share_service()
        success = await screen_share_service.set_permission(room_id, target_user_id, permission)
        
        return {
            "success": success,
            "permission": {
                "user_id": target_user_id,
                "can_share": permission.can_share,
                "can_view": permission.can_view,
                "can_control": permission.can_control,
                "can_record": permission.can_record
            }
        }
        
    except Exception as e:
        logger.error(f"Error setting screen share permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set screen share permission"
        )


@router.post("/recording/start/{session_id}")
async def start_screen_recording(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Start recording a screen share session"""
    try:
        user_id = current_user["user_id"]
        
        screen_share_service = services.get_screen_share_service()
        success = await screen_share_service.start_recording(session_id, user_id)
        
        return {
            "success": success,
            "message": "Recording started" if success else "Failed to start recording"
        }
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting screen recording: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start screen recording"
        )


@router.post("/recording/stop/{session_id}")
async def stop_screen_recording(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Stop recording a screen share session"""
    try:
        user_id = current_user["user_id"]
        
        screen_share_service = services.get_screen_share_service()
        recording_url = await screen_share_service.stop_recording(session_id, user_id)
        
        return {
            "success": recording_url is not None,
            "recording_url": recording_url,
            "message": "Recording stopped" if recording_url else "No active recording found"
        }
        
    except Exception as e:
        logger.error(f"Error stopping screen recording: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop screen recording"
        )


@router.get("/constraints")
async def get_screen_capture_constraints(
    quality: ScreenShareQuality = Query(default=ScreenShareQuality.AUTO),
    enable_audio: bool = Query(default=False),
    current_user: Dict[str, Any] = Depends(get_current_user),
    services: ServiceContainer = Depends(ServiceContainer.get_instance)
) -> Dict[str, Any]:
    """Get WebRTC constraints for screen capture"""
    try:
        screen_share_service = services.get_screen_share_service()
        constraints = await screen_share_service.get_capture_constraints(quality, enable_audio)
        
        return {
            "constraints": constraints,
            "quality": quality,
            "audio_enabled": enable_audio
        }
        
    except Exception as e:
        logger.error(f"Error getting screen capture constraints: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get screen capture constraints"
        )