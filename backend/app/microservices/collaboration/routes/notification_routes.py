"""
Notification API routes
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models import Notification
from ..services.notification_service import NotificationService
from ..utils.auth_utils import get_current_user

router = APIRouter(redirect_slashes=False)
security = HTTPBearer()

# Service dependencies - will be injected from integration
async def get_notification_service():
    """Get notification service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Try to initialize if not already done
    if not collaboration_integration.notification_service:
        try:
            # Check if running as part of unified system
            from app.core.database.neo4j_client import neo4j_client
            if neo4j_client and hasattr(neo4j_client, 'driver') and neo4j_client.driver:
                await collaboration_integration.initialize(unified_neo4j_client=neo4j_client)
        except ImportError:
            # Running standalone, initialize without unified client
            await collaboration_integration.initialize()
    
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Get notifications for the current user"""
    if unread_only:
        notifications = await notification_service.get_unread_notifications(
            user_id=current_user["user_id"],
            limit=limit
        )
    else:
        notifications = await notification_service.get_notification_history(
            user_id=current_user["user_id"],
            limit=limit,
            include_read=True,
            include_expired=False
        )
    return notifications


@router.get("/unread-count")
async def get_unread_count(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Get count of unread notifications"""
    count = await notification_service.get_notification_count(
        user_id=current_user["user_id"]
    )
    return {"unread_count": count}


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Mark a notification as read"""
    success = await notification_service.mark_as_read(
        user_id=current_user["user_id"],
        notification_id=notification_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}


@router.put("/mark-all-read")
async def mark_all_read(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Mark all notifications as read"""
    count = await notification_service.mark_all_as_read(
        user_id=current_user["user_id"]
    )
    
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Delete a notification"""
    success = await notification_service.delete_notification(
        user_id=current_user["user_id"],
        notification_id=notification_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification deleted"}


@router.post("/subscribe")
async def subscribe_to_push_notifications(
    push_token: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Subscribe to push notifications"""
    success = await notification_service.register_push_token(
        user_id=current_user["user_id"],
        push_token=push_token
    )
    
    if success:
        return {"message": "Successfully subscribed to push notifications"}
    else:
        raise HTTPException(status_code=400, detail="Failed to subscribe")


@router.delete("/unsubscribe")
async def unsubscribe_from_push_notifications(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Unsubscribe from push notifications"""
    success = await notification_service.unregister_push_token(
        user_id=current_user["user_id"]
    )
    
    if success:
        return {"message": "Successfully unsubscribed from push notifications"}
    else:
        raise HTTPException(status_code=404, detail="No push token found")


@router.post("/test")
async def send_test_notification(
    title: str = Query("Test Notification", description="Notification title"),
    message: str = Query("This is a test notification", description="Notification message"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Send a test notification to the current user"""
    notification = await notification_service.create_notification(
        user_id=current_user["user_id"],
        notification_type="SYSTEM",
        title=title,
        message=message,
        data={"test": True}
    )
    
    return {
        "message": "Test notification sent",
        "notification_id": notification.id
    }