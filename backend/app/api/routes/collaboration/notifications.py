"""
Notification routes for collaboration microservice
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.microservices.collaboration.models import Notification
from app.api.routes.auth import get_current_active_user
from app.core.database.models import User

router = APIRouter(tags=["collaboration-notifications"])
security = HTTPBearer()

# Service dependencies - will be injected from integration
async def get_notification_service():
    """Get notification service from collaboration integration"""
    from app.microservices.collaboration.integration import collaboration_integration
    
    if not collaboration_integration.notification_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification service not available. Collaboration integration may not be initialized."
        )
    return collaboration_integration.notification_service


@router.get("", response_model=List[Notification])
async def get_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum notifications to return"),
    current_user: User = Depends(get_current_active_user),
    notification_service = Depends(get_notification_service)
):
    """Get notifications for the current user"""
    if unread_only:
        notifications = await notification_service.get_unread_notifications(
            current_user.user_id,
            limit=limit
        )
    else:
        # Get all notifications (both read and unread) - use private method
        notifications = await notification_service._get_user_notifications(
            current_user.user_id
        )
    return notifications


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    notification_service = Depends(get_notification_service)
):
    """Mark a notification as read"""
    success = await notification_service.mark_as_read(notification_id, current_user.user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied"
        )
    return {"message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    notification_service = Depends(get_notification_service)
):
    """Mark all notifications as read for the current user"""
    count = await notification_service.mark_all_as_read(current_user.user_id)
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    notification_service = Depends(get_notification_service)
):
    """Delete a notification"""
    success = await notification_service.delete_notification(notification_id, current_user.user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied"
        )
    return {"message": "Notification deleted"}