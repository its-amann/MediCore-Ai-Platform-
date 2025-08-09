"""
Comprehensive notification service for collaboration events
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import html
import re

from ..models import (
    Notification, 
    NotificationType, 
    NotificationPriority,
    NotificationPreferences
)
from ..database.neo4j_storage import get_collaboration_storage


logger = logging.getLogger(__name__)


class NotificationService:
    """
    Comprehensive notification service for managing real-time notifications,
    email notifications, and notification preferences for collaboration events.
    """
    
    def __init__(
        self,
        db_client=None,
        websocket_manager=None,
        email_service=None,
        push_service=None
    ):
        self.db_client = db_client
        self.websocket_manager = websocket_manager
        self.email_service = email_service
        self.push_service = push_service
        self.storage = get_collaboration_storage()
        
        # In-memory cache for preferences and push tokens only
        self._preferences: Dict[str, NotificationPreferences] = {}
        self._push_tokens: Dict[str, str] = {}
        
        # Notification templates
        self.notification_templates = NOTIFICATION_TEMPLATES
        
    # Core notification methods
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        expires_in_hours: Optional[int] = None
    ) -> Optional[Notification]:
        """Create and send a notification to a user"""
        try:
            # Check user preferences
            if not await self._should_send_notification(user_id, notification_type, priority):
                logger.debug(f"Notification blocked by user preferences: {user_id}, {notification_type}")
                return None
            
            notification_id = str(uuid.uuid4())
            
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            # Validate and sanitize notification content
            title = self._sanitize_content(title)
            message = self._sanitize_content(message)
            
            # Validate data if provided
            if data:
                data = self._validate_notification_data(data)
            
            notification = Notification(
                id=notification_id,
                user_id=user_id,
                notification_type=notification_type,
                priority=priority,
                title=title,
                message=message,
                data=data or {},
                expires_at=expires_at
            )
            
            # Store notification
            await self.store_notification(user_id, notification)
            
            # Send real-time notification via WebSocket
            if self.websocket_manager:
                await self._send_websocket_notification(notification)
            
            # Send email notification if enabled
            preferences = await self._get_user_preferences(user_id)
            if preferences.email_enabled and priority == NotificationPriority.URGENT:
                await self._send_email_notification(notification)
                notification.email_sent = True
            
            # Send push notification if enabled
            if preferences.push_enabled and user_id in self._push_tokens:
                await self._send_push_notification(notification)
                notification.push_sent = True
            
            logger.info(f"Notification created: {notification_id} for user {user_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            raise
    
    # Room join request notifications
    
    async def send_join_request_notification(
        self,
        room_id: str,
        room_name: str,
        requester_id: str,
        requester_name: str,
        room_owner_id: str
    ) -> Notification:
        """Notify room owner of a join request"""
        return await self.create_notification(
            user_id=room_owner_id,
            notification_type=NotificationType.JOIN_REQUEST,
            title="New Join Request",
            message=f"{requester_name} wants to join your room '{room_name}'",
            data={
                "room_id": room_id,
                "room_name": room_name,
                "requester_id": requester_id,
                "requester_name": requester_name,
                "action_required": True
            },
            priority=NotificationPriority.URGENT,
            expires_in_hours=24
        )
    
    async def send_join_approval_notification(
        self,
        room_id: str,
        room_name: str,
        user_id: str,
        approved_by: str,
        approved_by_name: str
    ) -> Notification:
        """Notify user that their join request was approved"""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.JOIN_APPROVED,
            title="Join Request Approved",
            message=f"Your request to join '{room_name}' has been approved by {approved_by_name}",
            data={
                "room_id": room_id,
                "room_name": room_name,
                "approved_by": approved_by,
                "approved_by_name": approved_by_name,
                "action": "join_room"
            },
            priority=NotificationPriority.NORMAL,
            expires_in_hours=48
        )
    
    async def send_join_rejection_notification(
        self,
        room_id: str,
        room_name: str,
        user_id: str,
        rejected_by: str,
        rejected_by_name: str,
        reason: Optional[str] = None
    ) -> Notification:
        """Notify user that their join request was rejected"""
        message = f"Your request to join '{room_name}' was declined by {rejected_by_name}"
        if reason:
            message += f". Reason: {reason}"
            
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.JOIN_REJECTED,
            title="Join Request Declined",
            message=message,
            data={
                "room_id": room_id,
                "room_name": room_name,
                "rejected_by": rejected_by,
                "rejected_by_name": rejected_by_name,
                "reason": reason
            },
            priority=NotificationPriority.NORMAL,
            expires_in_hours=48
        )
    
    # Room invitation notifications
    
    async def send_room_invitation_notification(
        self,
        room_id: str,
        room_name: str,
        invited_user_id: str,
        invited_by: str,
        invited_by_name: str,
        invitation_message: Optional[str] = None
    ) -> Notification:
        """Send room invitation to a user"""
        message = f"{invited_by_name} invited you to join '{room_name}'"
        if invitation_message:
            message += f": {invitation_message}"
            
        return await self.create_notification(
            user_id=invited_user_id,
            notification_type=NotificationType.ROOM_INVITE,
            title="Room Invitation",
            message=message,
            data={
                "room_id": room_id,
                "room_name": room_name,
                "invited_by": invited_by,
                "invited_by_name": invited_by_name,
                "invitation_message": invitation_message,
                "action": "accept_invitation"
            },
            priority=NotificationPriority.NORMAL,
            expires_in_hours=72
        )
    
    # Participant notifications
    
    async def send_participant_joined_notification(
        self,
        room_id: str,
        room_name: str,
        user_id: str,
        user_name: str,
        participants: List[str]
    ) -> List[Notification]:
        """Notify all participants when someone joins the room"""
        notifications = []
        
        for participant_id in participants:
            if participant_id != user_id:  # Don't notify the user who joined
                # Use template if available
                template = self.notification_templates.get('participant_joined', {})
                title = template.get('title', 'New Participant')
                message_template = template.get('message', "{user_name} joined '{room_name}'")
                message = message_template.format(user_name=user_name, room_name=room_name)
                
                notification = await self.create_notification(
                    user_id=participant_id,
                    notification_type=NotificationType.PARTICIPANT_JOINED,
                    title=title,
                    message=message,
                    data={
                        "room_id": room_id,
                        "room_name": room_name,
                        "joined_user_id": user_id,
                        "joined_user_name": user_name
                    },
                    priority=NotificationPriority.LOW
                )
                if notification:
                    notifications.append(notification)
        
        return notifications
    
    async def send_participant_left_notification(
        self,
        room_id: str,
        room_name: str,
        user_id: str,
        user_name: str,
        participants: List[str]
    ) -> List[Notification]:
        """Notify all participants when someone leaves the room"""
        notifications = []
        
        for participant_id in participants:
            if participant_id != user_id:  # Don't notify the user who left
                # Use template if available
                template = self.notification_templates.get('participant_left', {})
                title = template.get('title', 'Participant Left')
                message_template = template.get('message', "{user_name} left '{room_name}'")
                message = message_template.format(user_name=user_name, room_name=room_name)
                
                notification = await self.create_notification(
                    user_id=participant_id,
                    notification_type=NotificationType.PARTICIPANT_LEFT,
                    title=title,
                    message=message,
                    data={
                        "room_id": room_id,
                        "room_name": room_name,
                        "left_user_id": user_id,
                        "left_user_name": user_name
                    },
                    priority=NotificationPriority.LOW
                )
                if notification:
                    notifications.append(notification)
        
        return notifications
    
    # Room status notifications
    
    async def send_room_status_change_notification(
        self,
        room_id: str,
        room_name: str,
        new_status: str,
        changed_by: str,
        changed_by_name: str,
        participants: List[str],
        reason: Optional[str] = None
    ) -> List[Notification]:
        """Notify participants of room status changes"""
        notifications = []
        
        # Determine message and priority based on status
        if new_status == "disabled":
            title = "Room Disabled"
            message = f"'{room_name}' has been disabled by {changed_by_name}"
            notification_type = NotificationType.ROOM_DISABLED
            priority = NotificationPriority.URGENT
        elif new_status == "closing_soon":
            title = "Room Closing Soon"
            message = f"'{room_name}' will be closed soon"
            notification_type = NotificationType.ROOM_CLOSING_SOON
            priority = NotificationPriority.URGENT
        else:
            title = "Room Status Changed"
            message = f"'{room_name}' status changed to {new_status}"
            notification_type = NotificationType.ROOM_STARTED
            priority = NotificationPriority.NORMAL
        
        if reason:
            message += f". Reason: {reason}"
        
        for participant_id in participants:
            notification = await self.create_notification(
                user_id=participant_id,
                notification_type=notification_type,
                title=title,
                message=message,
                data={
                    "room_id": room_id,
                    "room_name": room_name,
                    "new_status": new_status,
                    "changed_by": changed_by,
                    "changed_by_name": changed_by_name,
                    "reason": reason
                },
                priority=priority
            )
            if notification:
                notifications.append(notification)
        
        return notifications
    
    # Teaching session notifications
    
    async def send_teaching_session_reminder(
        self,
        room_id: str,
        room_name: str,
        session_time: datetime,
        participants: List[str],
        teacher_name: str,
        reminder_minutes: int = 15
    ) -> List[Notification]:
        """Send teaching session reminder to participants"""
        notifications = []
        
        time_until = session_time - datetime.utcnow()
        minutes_until = int(time_until.total_seconds() / 60)
        
        message = f"Teaching session in '{room_name}' with {teacher_name} starts in {minutes_until} minutes"
        
        for participant_id in participants:
            notification = await self.create_notification(
                user_id=participant_id,
                notification_type=NotificationType.TEACHING_REMINDER,
                title="Teaching Session Reminder",
                message=message,
                data={
                    "room_id": room_id,
                    "room_name": room_name,
                    "session_time": session_time.isoformat(),
                    "teacher_name": teacher_name,
                    "minutes_until": minutes_until,
                    "action": "join_session"
                },
                priority=NotificationPriority.URGENT,
                expires_in_hours=1
            )
            if notification:
                notifications.append(notification)
        
        return notifications
    
    # AI response notifications
    
    async def send_ai_response_notification(
        self,
        user_id: str,
        room_id: str,
        room_name: str,
        question: str,
        answer_preview: str
    ) -> Notification:
        """Notify user when AI assistant has answered their question"""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.AI_RESPONSE,
            title="AI Assistant Response",
            message=f"AI has answered your question in '{room_name}': {answer_preview[:100]}...",
            data={
                "room_id": room_id,
                "room_name": room_name,
                "question": question,
                "answer_preview": answer_preview,
                "action": "view_response"
            },
            priority=NotificationPriority.NORMAL
        )
    
    async def send_mention_notification(
        self,
        user_id: str,
        sender_name: str,
        room_id: str,
        message_preview: str
    ) -> Optional[Notification]:
        """Notify user when they are mentioned in a message"""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.MENTION,
            title="Mentioned in Chat",
            message=f"{sender_name} mentioned you: {message_preview}",
            data={
                "room_id": room_id,
                "sender_name": sender_name,
                "message_preview": message_preview,
                "action": "view_message"
            },
            priority=NotificationPriority.NORMAL
        )
    
    # Storage and retrieval methods
    
    async def store_notification(self, user_id: str, notification: Notification) -> bool:
        """Store notification for a user"""
        try:
            # Prepare notification data for Neo4j
            notification_data = {
                "notification_id": notification.id,
                "user_id": user_id,
                "type": notification.notification_type.value if isinstance(notification.notification_type, NotificationType) else notification.notification_type,
                "priority": notification.priority.value if isinstance(notification.priority, NotificationPriority) else notification.priority,
                "title": notification.title,
                "message": notification.message,
                "data": notification.data,
                "is_read": notification.is_read,
                "read_at": notification.read_at,
                "expires_at": notification.expires_at,
                "email_sent": notification.email_sent,
                "push_sent": notification.push_sent,
                "created_at": notification.created_at
            }
            
            # Store in Neo4j
            await self.storage.store_notification(notification_data)
            
            return True
        except Exception as e:
            logger.error(f"Error storing notification: {str(e)}")
            return False
    
    async def get_unread_notifications(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Notification]:
        """Get unread notifications for a user"""
        notifications = await self._get_user_notifications(user_id)
        
        # Filter unread and non-expired
        current_time = datetime.utcnow()
        unread = [
            n for n in notifications
            if not n.is_read and (not n.expires_at or n.expires_at > current_time)
        ]
        
        # Sort by priority and creation time
        unread.sort(key=lambda n: (
            0 if n.priority == NotificationPriority.URGENT else
            1 if n.priority == NotificationPriority.NORMAL else 2,
            n.created_at
        ), reverse=True)
        
        return unread[:limit]
    
    async def get_notification_history(
        self,
        user_id: str,
        limit: int = 100,
        include_read: bool = True,
        include_expired: bool = False
    ) -> List[Notification]:
        """Get notification history for a user"""
        notifications = await self._get_user_notifications(user_id)
        
        # Filter based on parameters
        current_time = datetime.utcnow()
        filtered = []
        
        for n in notifications:
            if not include_read and n.is_read:
                continue
            if not include_expired and n.expires_at and n.expires_at < current_time:
                continue
            filtered.append(n)
        
        # Sort by creation time (newest first)
        filtered.sort(key=lambda n: n.created_at, reverse=True)
        
        return filtered[:limit]
    
    async def mark_as_read(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """Mark a notification as read"""
        try:
            # Update in database
            count = await self.storage.mark_notifications_as_read(
                user_id=user_id,
                notification_ids=[notification_id]
            )
            
            if count > 0:
                logger.info(f"Marked notification {notification_id} as read")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        try:
            # Get all unread notification IDs
            notifications = await self.storage.get_user_notifications(
                user_id=user_id,
                unread_only=True,
                limit=1000,
                offset=0
            )
            
            notification_ids = [n.get('notification_id') for n in notifications if n.get('notification_id')]
            
            if notification_ids:
                # Update in database
                count = await self.storage.mark_notifications_as_read(
                    user_id=user_id,
                    notification_ids=notification_ids
                )
                
                logger.info(f"Marked {count} notifications as read for user {user_id}")
                return count
            
            return 0
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0
    
    async def delete_notification(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """Delete a notification"""
        try:
            # Delete from database using a custom query
            query = """
            MATCH (u:User {user_id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification {notification_id: $notification_id})
            DETACH DELETE n
            RETURN true as success
            """
            
            result = await self.storage.run_write_query(query, {
                "user_id": user_id,
                "notification_id": notification_id
            })
            
            if result:
                logger.info(f"Deleted notification {notification_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return False
    
    async def get_notification_count(self, user_id: str) -> int:
        """Get count of unread notifications"""
        notifications = await self.get_unread_notifications(user_id)
        return len(notifications)
    
    # User preference management
    
    async def get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """Get user notification preferences"""
        return await self._get_user_preferences(user_id)
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> NotificationPreferences:
        """Update user notification preferences"""
        try:
            current_prefs = await self._get_user_preferences(user_id)
            
            # Update preferences
            for key, value in preferences.items():
                if hasattr(current_prefs, key):
                    setattr(current_prefs, key, value)
            
            current_prefs.updated_at = datetime.utcnow()
            self._preferences[user_id] = current_prefs
            
            # Update in database
            # await self.db_client.notification_preferences.update_one(
            #     {"user_id": user_id},
            #     {"$set": current_prefs.dict()},
            #     upsert=True
            # )
            
            logger.info(f"Updated notification preferences for user {user_id}")
            return current_prefs
        except Exception as e:
            logger.error(f"Error updating notification preferences: {str(e)}")
            raise
    
    # Helper methods
    
    async def _get_user_notifications(self, user_id: str) -> List[Notification]:
        """Get all notifications for a user from storage"""
        try:
            # Get notifications from database
            notifications_data = await self.storage.get_user_notifications(
                user_id=user_id,
                unread_only=False,
                limit=1000,  # Get all notifications for processing
                offset=0
            )
            
            # Convert to Notification objects
            notifications = []
            for notif_data in notifications_data:
                try:
                    # Parse notification type and priority from stored values
                    notif_type = notif_data.get('type', notif_data.get('notification_type'))
                    if isinstance(notif_type, str):
                        notif_type = NotificationType(notif_type)
                    
                    notif_priority = notif_data.get('priority', 'normal')
                    if isinstance(notif_priority, str):
                        notif_priority = NotificationPriority(notif_priority)
                    
                    notification = Notification(
                        id=notif_data.get('notification_id'),
                        user_id=user_id,
                        notification_type=notif_type,
                        priority=notif_priority,
                        title=notif_data.get('title', ''),
                        message=notif_data.get('message', ''),
                        data=notif_data.get('data', {}),
                        is_read=notif_data.get('is_read', False),
                        read_at=notif_data.get('read_at'),
                        expires_at=notif_data.get('expires_at'),
                        email_sent=notif_data.get('email_sent', False),
                        push_sent=notif_data.get('push_sent', False),
                        created_at=notif_data.get('created_at')
                    )
                    notifications.append(notification)
                except Exception as e:
                    logger.error(f"Error parsing notification: {str(e)}")
                    continue
            
            return notifications
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            return []
    
    async def _get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """Get user notification preferences"""
        if user_id not in self._preferences:
            # Create default preferences
            self._preferences[user_id] = NotificationPreferences(user_id=user_id)
        
        return self._preferences[user_id]
    
    async def _should_send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        priority: NotificationPriority
    ) -> bool:
        """Check if notification should be sent based on user preferences"""
        preferences = await self._get_user_preferences(user_id)
        
        # Check if urgent only mode
        if preferences.urgent_only and priority != NotificationPriority.URGENT:
            return False
        
        # Check quiet hours
        if preferences.quiet_hours_start is not None and preferences.quiet_hours_end is not None:
            current_hour = datetime.utcnow().hour
            if preferences.quiet_hours_start <= current_hour < preferences.quiet_hours_end:
                # Only allow urgent notifications during quiet hours
                if priority != NotificationPriority.URGENT:
                    return False
        
        # Check notification type preferences
        type_mapping = {
            NotificationType.JOIN_REQUEST: preferences.join_requests,
            NotificationType.JOIN_APPROVED: preferences.join_requests,
            NotificationType.JOIN_REJECTED: preferences.join_requests,
            NotificationType.ROOM_INVITE: preferences.room_invitations,
            NotificationType.MENTION: preferences.mentions,
            NotificationType.NEW_MESSAGE: preferences.messages,
            NotificationType.AI_RESPONSE: preferences.ai_responses,
            NotificationType.TEACHING_REMINDER: preferences.teaching_reminders,
            NotificationType.ROOM_DISABLED: preferences.room_updates,
            NotificationType.ROOM_CLOSING_SOON: preferences.room_updates,
        }
        
        return type_mapping.get(notification_type, True)
    
    async def _send_websocket_notification(self, notification: Notification):
        """Send notification via WebSocket"""
        if not self.websocket_manager:
            return
        
        try:
            await self.websocket_manager.send_notification(
                user_id=notification.user_id,
                data={
                    "type": "notification",
                    "notification": notification.dict()
                }
            )
            logger.debug(f"WebSocket notification sent to user {notification.user_id}")
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {str(e)}")
    
    async def _send_email_notification(self, notification: Notification):
        """Send notification via email"""
        if not self.email_service:
            return
        
        try:
            # Get user email from user service
            # user_email = await self.user_service.get_user_email(notification.user_id)
            
            # For now, we'll simulate
            logger.info(f"Would send email notification to user {notification.user_id}")
            
            # await self.email_service.send_email(
            #     to=user_email,
            #     subject=notification.title,
            #     body=notification.message,
            #     template="notification",
            #     context=notification.dict()
            # )
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
    
    async def _send_push_notification(self, notification: Notification):
        """Send push notification to device"""
        if not self.push_service:
            return
        
        push_token = self._push_tokens.get(notification.user_id)
        if not push_token:
            return
        
        try:
            payload = {
                "token": push_token,
                "notification": {
                    "title": notification.title,
                    "body": notification.message,
                    "badge": await self.get_notification_count(notification.user_id)
                },
                "data": {
                    "notification_id": notification.id,
                    "type": notification.notification_type,
                    **notification.data
                }
            }
            
            # await self.push_service.send(payload)
            logger.info(f"Would send push notification to user {notification.user_id}")
            
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
    
    # Push token management
    
    async def register_push_token(
        self,
        user_id: str,
        push_token: str,
        device_type: str = "mobile"
    ) -> bool:
        """Register a push notification token for a user"""
        try:
            self._push_tokens[user_id] = push_token
            
            # Store in database
            # await self.db_client.push_tokens.update_one(
            #     {"user_id": user_id},
            #     {"$set": {
            #         "token": push_token,
            #         "device_type": device_type,
            #         "updated_at": datetime.utcnow()
            #     }},
            #     upsert=True
            # )
            
            logger.info(f"Registered push token for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error registering push token: {str(e)}")
            return False
    
    async def unregister_push_token(self, user_id: str) -> bool:
        """Unregister push notification token"""
        try:
            if user_id in self._push_tokens:
                del self._push_tokens[user_id]
            
            # Delete from database
            # await self.db_client.push_tokens.delete_one({"user_id": user_id})
            
            logger.info(f"Unregistered push token for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error unregistering push token: {str(e)}")
            return False
    
    # Cleanup methods
    
    async def cleanup_expired_notifications(self):
        """Remove expired notifications (background task)"""
        try:
            current_time = datetime.utcnow()
            total_cleaned = 0
            
            for user_id, notifications in self._notifications.items():
                before_count = len(notifications)
                self._notifications[user_id] = [
                    n for n in notifications
                    if not n.expires_at or n.expires_at > current_time
                ]
                cleaned = before_count - len(self._notifications[user_id])
                total_cleaned += cleaned
            
            # Clean from database
            # await self.db_client.notifications.delete_many({
            #     "expires_at": {"$lt": current_time}
            # })
            
            if total_cleaned > 0:
                logger.info(f"Cleaned up {total_cleaned} expired notifications")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired notifications: {str(e)}")
    
    async def cleanup_old_notifications(self, days_to_keep: int = 30):
        """Remove old read notifications"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            total_cleaned = 0
            
            for user_id, notifications in self._notifications.items():
                before_count = len(notifications)
                self._notifications[user_id] = [
                    n for n in notifications
                    if not (n.is_read and n.created_at < cutoff_date)
                ]
                cleaned = before_count - len(self._notifications[user_id])
                total_cleaned += cleaned
            
            # Clean from database
            # await self.db_client.notifications.delete_many({
            #     "is_read": True,
            #     "created_at": {"$lt": cutoff_date}
            # })
            
            if total_cleaned > 0:
                logger.info(f"Cleaned up {total_cleaned} old notifications")
                
        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {str(e)}")
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize notification content to prevent XSS attacks"""
        if not content:
            return ""
        
        # Escape HTML entities
        content = html.escape(content)
        
        # Remove any script tags or javascript: URLs
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        content = re.sub(r'on\w+\s*=', '', content, flags=re.IGNORECASE)
        
        # Limit length to prevent abuse
        max_length = 1000  # Reasonable length for notifications
        if len(content) > max_length:
            content = content[:max_length] + '...'
        
        return content.strip()
    
    def _validate_notification_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize notification data"""
        if not isinstance(data, dict):
            return {}
        
        validated_data = {}
        allowed_keys = [
            'room_id', 'room_name', 'requester_id', 'requester_name',
            'action_required', 'action', 'approved_by', 'approved_by_name',
            'rejected_by', 'rejected_by_name', 'reason', 'invited_by',
            'invited_by_name', 'invitation_message', 'joined_user_id',
            'joined_user_name', 'left_user_id', 'left_user_name',
            'new_status', 'changed_by', 'changed_by_name', 'session_time',
            'teacher_name', 'minutes_until', 'question', 'answer_preview'
        ]
        
        for key in allowed_keys:
            if key in data:
                value = data[key]
                if isinstance(value, str):
                    # Sanitize string values
                    validated_data[key] = self._sanitize_content(value)
                elif isinstance(value, (int, float, bool)):
                    validated_data[key] = value
                elif isinstance(value, datetime):
                    validated_data[key] = value.isoformat()
                # Skip complex types like dicts and lists for safety
        
        return validated_data


# Notification templates for consistent messaging
NOTIFICATION_TEMPLATES = {
    "join_request": {
        "title": "New Join Request",
        "message": "{requester_name} wants to join your room '{room_name}'"
    },
    "join_approved": {
        "title": "Join Request Approved",
        "message": "Your request to join '{room_name}' has been approved"
    },
    "join_rejected": {
        "title": "Join Request Declined",
        "message": "Your request to join '{room_name}' was declined"
    },
    "room_invitation": {
        "title": "Room Invitation",
        "message": "{inviter_name} invited you to join '{room_name}'"
    },
    "participant_joined": {
        "title": "New Participant",
        "message": "{user_name} joined '{room_name}'"
    },
    "participant_left": {
        "title": "Participant Left",
        "message": "{user_name} left '{room_name}'"
    },
    "room_disabled": {
        "title": "Room Disabled",
        "message": "'{room_name}' has been disabled"
    },
    "room_closing_soon": {
        "title": "Room Closing Soon",
        "message": "'{room_name}' will be closed soon"
    },
    "teaching_reminder": {
        "title": "Teaching Session Reminder",
        "message": "Teaching session in '{room_name}' starts in {minutes} minutes"
    },
    "ai_response": {
        "title": "AI Assistant Response",
        "message": "AI has answered your question in '{room_name}'"
    }
}