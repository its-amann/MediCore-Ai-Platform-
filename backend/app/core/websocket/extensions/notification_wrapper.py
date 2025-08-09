"""
Notification WebSocket Wrapper

Wraps notification functionality for integration with the unified WebSocket architecture.
"""

from typing import Dict, Any, List, Optional, Set
import logging
from datetime import datetime
import json

from .base_wrapper import BaseWrapper

logger = logging.getLogger(__name__)


class NotificationWrapper(BaseWrapper):
    """
    WebSocket wrapper for notification system
    
    This wrapper provides WebSocket support for:
    - Real-time notification delivery
    - Notification status updates
    - Bulk notification operations
    - User notification preferences
    - Notification channels management
    """
    
    def __init__(self, priority: int = 25):
        """Initialize the notification wrapper"""
        super().__init__(
            name="notification",
            priority=priority  # High priority for notifications
        )
        
        # Supported message types
        self._supported_types = [
            "notification_send", "notification_delivered", "notification_read",
            "notification_mark_read", "notification_mark_all_read",
            "notification_preference_update", "notification_channel_subscribe",
            "notification_channel_unsubscribe", "notification_bulk_update",
            "notification_history_request"
        ]
        
        # Notification tracking
        self._user_notifications: Dict[str, List[Dict[str, Any]]] = {}
        self._notification_channels: Dict[str, Set[str]] = {}  # channel -> user_ids
        self._user_channels: Dict[str, Set[str]] = {}  # user_id -> channels
        self._user_preferences: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self._notification_stats = {
            'sent': 0,
            'delivered': 0,
            'read': 0,
            'failed': 0
        }
        
        # Try to integrate with existing notification manager
        self._legacy_notification_manager = None
        self._setup_legacy_integration()
    
    def _setup_legacy_integration(self):
        """Set up integration with existing notification systems"""
        try:
            # Try to import the legacy notification WebSocket manager
            from ....voice_doctor_agent.backend.src.core.notifications.websocket_manager import ws_manager
            self._legacy_notification_manager = ws_manager
            self.logger.info("Legacy notification manager integration established")
        except ImportError:
            self.logger.info("No legacy notification manager found")
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize the notification wrapper"""
        await super().initialize(config)
        
        # Set up default notification channels
        default_channels = config.get('default_channels', [
            'system', 'medical_alerts', 'workflow_updates', 'chat_messages'
        ])
        
        for channel in default_channels:
            if channel not in self._notification_channels:
                self._notification_channels[channel] = set()
        
        self.logger.info(f"Notification wrapper initialized with channels: {default_channels}")
    
    async def shutdown(self):
        """Shutdown the notification wrapper"""
        # Clean up resources
        self._user_notifications.clear()
        self._notification_channels.clear()
        self._user_channels.clear()
        self._user_preferences.clear()
        
        await super().shutdown()
        self.logger.info("Notification wrapper shutdown")
    
    def can_handle_message(self, message_type: str) -> bool:
        """Check if this wrapper can handle a message type"""
        return message_type in self._supported_types
    
    def get_supported_message_types(self) -> List[str]:
        """Get list of supported message types"""
        return self._supported_types.copy()
    
    async def handle_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle a WebSocket message"""
        message_type = message.get("type", "")
        
        if not self.can_handle_message(message_type):
            return False
        
        try:
            # Get user info from connection
            connection_info = self.get_connection_info(connection_id)
            if not connection_info:
                self.logger.warning(f"No connection info for {connection_id}")
                return False
            
            user_id = connection_info.user_id
            
            # Handle notification sending
            if message_type == "notification_send":
                return await self._handle_send_notification(connection_id, user_id, message)
            
            # Handle notification status updates
            elif message_type in ["notification_delivered", "notification_read"]:
                return await self._handle_status_update(connection_id, user_id, message)
            
            # Handle notification actions
            elif message_type in ["notification_mark_read", "notification_mark_all_read"]:
                return await self._handle_notification_action(connection_id, user_id, message)
            
            # Handle preference updates
            elif message_type == "notification_preference_update":
                return await self._handle_preference_update(connection_id, user_id, message)
            
            # Handle channel management
            elif message_type in ["notification_channel_subscribe", "notification_channel_unsubscribe"]:
                return await self._handle_channel_management(connection_id, user_id, message)
            
            # Handle bulk operations
            elif message_type == "notification_bulk_update":
                return await self._handle_bulk_update(connection_id, user_id, message)
            
            # Handle history requests
            elif message_type == "notification_history_request":
                return await self._handle_history_request(connection_id, user_id, message)
            
            else:
                self.logger.warning(f"Unhandled notification message type: {message_type}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error handling notification message {message_type}: {e}")
            await self.send_message(connection_id, {
                "type": "error",
                "message": f"Notification operation failed: {str(e)}"
            })
            return False
    
    async def _handle_send_notification(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle sending a notification"""
        target_user_id = message.get("target_user_id")
        notification_data = message.get("notification", {})
        channel = message.get("channel", "system")
        
        if not target_user_id or not notification_data:
            await self.send_message(connection_id, {
                "type": "error",
                "message": "target_user_id and notification data are required"
            })
            return False
        
        try:
            # Create notification
            notification = {
                "id": f"notif_{datetime.utcnow().timestamp()}",
                "sender_id": user_id,
                "target_user_id": target_user_id,
                "channel": channel,
                "type": notification_data.get("type", "info"),
                "title": notification_data.get("title", ""),
                "message": notification_data.get("message", ""),
                "data": notification_data.get("data", {}),
                "created_at": datetime.utcnow().isoformat(),
                "read": False,
                "delivered": False
            }
            
            # Store notification
            if target_user_id not in self._user_notifications:
                self._user_notifications[target_user_id] = []
            self._user_notifications[target_user_id].append(notification)
            
            # Send notification to target user if online
            await self._deliver_notification(target_user_id, notification)
            
            # Send confirmation to sender
            await self.send_message(connection_id, {
                "type": "notification_sent",
                "notification_id": notification["id"],
                "target_user_id": target_user_id,
                "status": "sent"
            })
            
            self._notification_stats['sent'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            self._notification_stats['failed'] += 1
            return False
    
    async def _deliver_notification(self, user_id: str, notification: Dict[str, Any]):
        """Deliver notification to a user"""
        try:
            # Check if user is subscribed to the channel
            user_channels = self._user_channels.get(user_id, set())
            notification_channel = notification.get("channel", "system")
            
            if notification_channel not in user_channels and "system" not in user_channels:
                self.logger.debug(f"User {user_id} not subscribed to channel {notification_channel}")
                return
            
            # Check user preferences
            user_prefs = self._user_preferences.get(user_id, {})
            if not self._should_deliver_notification(notification, user_prefs):
                self.logger.debug(f"Notification filtered by user preferences for {user_id}")
                return
            
            # Try to deliver via unified WebSocket system
            if self.is_user_online(user_id):
                await self.send_to_user(user_id, {
                    "type": "notification.new",
                    "data": notification
                })
                
                notification["delivered"] = True
                notification["delivered_at"] = datetime.utcnow().isoformat()
                self._notification_stats['delivered'] += 1
                
                self.logger.info(f"Notification delivered to user {user_id}: {notification['id']}")
            
            # Also try legacy notification manager if available
            elif self._legacy_notification_manager:
                await self._legacy_notification_manager.send_notification(user_id, notification)
                notification["delivered"] = True
                notification["delivered_at"] = datetime.utcnow().isoformat()
                self._notification_stats['delivered'] += 1
                
                self.logger.info(f"Notification delivered via legacy manager to user {user_id}: {notification['id']}")
            
            else:
                self.logger.debug(f"User {user_id} not online, notification queued")
        
        except Exception as e:
            self.logger.error(f"Error delivering notification to user {user_id}: {e}")
            self._notification_stats['failed'] += 1
    
    def _should_deliver_notification(self, notification: Dict[str, Any], user_prefs: Dict[str, Any]) -> bool:
        """Check if notification should be delivered based on user preferences"""
        notification_type = notification.get("type", "info")
        channel = notification.get("channel", "system")
        
        # Check if notification type is enabled
        enabled_types = user_prefs.get("enabled_types", ["info", "warning", "error", "success"])
        if notification_type not in enabled_types:
            return False
        
        # Check if channel is enabled
        enabled_channels = user_prefs.get("enabled_channels", ["system"])
        if channel not in enabled_channels:
            return False
        
        # Check quiet hours
        quiet_hours = user_prefs.get("quiet_hours")
        if quiet_hours and self._is_in_quiet_hours(quiet_hours):
            # Only allow critical notifications during quiet hours
            if notification.get("priority", "normal") != "critical":
                return False
        
        return True
    
    def _is_in_quiet_hours(self, quiet_hours: Dict[str, Any]) -> bool:
        """Check if current time is within quiet hours"""
        # Simplified quiet hours check
        return False  # Placeholder implementation
    
    async def _handle_status_update(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle notification status updates"""
        notification_id = message.get("notification_id")
        status = message.get("type")  # "notification_delivered" or "notification_read"
        
        if not notification_id:
            return False
        
        # Find and update notification
        user_notifications = self._user_notifications.get(user_id, [])
        for notification in user_notifications:
            if notification["id"] == notification_id:
                if status == "notification_delivered":
                    notification["delivered"] = True
                    notification["delivered_at"] = datetime.utcnow().isoformat()
                    self._notification_stats['delivered'] += 1
                
                elif status == "notification_read":
                    notification["read"] = True
                    notification["read_at"] = datetime.utcnow().isoformat()
                    self._notification_stats['read'] += 1
                
                # Send acknowledgment
                await self.send_message(connection_id, {
                    "type": f"{status}_ack",
                    "notification_id": notification_id
                })
                
                return True
        
        return False
    
    async def _handle_notification_action(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle notification actions like mark as read"""
        message_type = message.get("type")
        
        try:
            if message_type == "notification_mark_read":
                notification_id = message.get("notification_id")
                return await self._mark_notification_read(connection_id, user_id, notification_id)
            
            elif message_type == "notification_mark_all_read":
                before_date = message.get("before_date")
                return await self._mark_all_notifications_read(connection_id, user_id, before_date)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error handling notification action: {e}")
            return False
    
    async def _mark_notification_read(self, connection_id: str, user_id: str, notification_id: str) -> bool:
        """Mark a specific notification as read"""
        user_notifications = self._user_notifications.get(user_id, [])
        
        for notification in user_notifications:
            if notification["id"] == notification_id:
                notification["read"] = True
                notification["read_at"] = datetime.utcnow().isoformat()
                self._notification_stats['read'] += 1
                
                await self.send_message(connection_id, {
                    "type": "notification_mark_read_ack",
                    "notification_id": notification_id
                })
                
                return True
        
        return False
    
    async def _mark_all_notifications_read(self, connection_id: str, user_id: str, before_date: Optional[str]) -> bool:
        """Mark all notifications as read"""
        user_notifications = self._user_notifications.get(user_id, [])
        marked_count = 0
        
        cutoff_time = None
        if before_date:
            try:
                cutoff_time = datetime.fromisoformat(before_date.replace('Z', '+00:00'))
            except ValueError:
                self.logger.warning(f"Invalid before_date format: {before_date}")
        
        for notification in user_notifications:
            if notification["read"]:
                continue
            
            # Check date filter
            if cutoff_time:
                created_at = datetime.fromisoformat(notification["created_at"].replace('Z', '+00:00'))
                if created_at > cutoff_time:
                    continue
            
            notification["read"] = True
            notification["read_at"] = datetime.utcnow().isoformat()
            marked_count += 1
        
        self._notification_stats['read'] += marked_count
        
        await self.send_message(connection_id, {
            "type": "notification_mark_all_read_ack",
            "marked_count": marked_count,
            "before_date": before_date
        })
        
        return True
    
    async def _handle_preference_update(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle notification preference updates"""
        preferences = message.get("preferences", {})
        
        # Update user preferences
        self._user_preferences[user_id] = preferences
        
        # Send acknowledgment
        await self.send_message(connection_id, {
            "type": "notification_preference_updated",
            "preferences": preferences
        })
        
        self.logger.info(f"Updated notification preferences for user {user_id}")
        return True
    
    async def _handle_channel_management(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle channel subscription/unsubscription"""
        message_type = message.get("type")
        channel = message.get("channel")
        
        if not channel:
            await self.send_message(connection_id, {
                "type": "error",
                "message": "channel is required"
            })
            return False
        
        try:
            if message_type == "notification_channel_subscribe":
                return await self._subscribe_to_channel(connection_id, user_id, channel)
            
            elif message_type == "notification_channel_unsubscribe":
                return await self._unsubscribe_from_channel(connection_id, user_id, channel)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error handling channel management: {e}")
            return False
    
    async def _subscribe_to_channel(self, connection_id: str, user_id: str, channel: str) -> bool:
        """Subscribe user to a notification channel"""
        # Add to channel
        if channel not in self._notification_channels:
            self._notification_channels[channel] = set()
        self._notification_channels[channel].add(user_id)
        
        # Add to user channels
        if user_id not in self._user_channels:
            self._user_channels[user_id] = set()
        self._user_channels[user_id].add(channel)
        
        await self.send_message(connection_id, {
            "type": "notification_channel_subscribed",
            "channel": channel
        })
        
        self.logger.info(f"User {user_id} subscribed to channel {channel}")
        return True
    
    async def _unsubscribe_from_channel(self, connection_id: str, user_id: str, channel: str) -> bool:
        """Unsubscribe user from a notification channel"""
        # Remove from channel
        if channel in self._notification_channels:
            self._notification_channels[channel].discard(user_id)
        
        # Remove from user channels
        if user_id in self._user_channels:
            self._user_channels[user_id].discard(channel)
        
        await self.send_message(connection_id, {
            "type": "notification_channel_unsubscribed",
            "channel": channel
        })
        
        self.logger.info(f"User {user_id} unsubscribed from channel {channel}")
        return True
    
    async def _handle_bulk_update(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle bulk notification updates"""
        updates = message.get("updates", {})
        
        # Apply bulk updates
        user_notifications = self._user_notifications.get(user_id, [])
        updated_count = 0
        
        for notification in user_notifications:
            notification_id = notification["id"]
            if notification_id in updates:
                notification.update(updates[notification_id])
                updated_count += 1
        
        await self.send_message(connection_id, {
            "type": "notification_bulk_update_ack",
            "updated_count": updated_count
        })
        
        return True
    
    async def _handle_history_request(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle notification history requests"""
        limit = message.get("limit", 50)
        offset = message.get("offset", 0)
        channel_filter = message.get("channel")
        unread_only = message.get("unread_only", False)
        
        user_notifications = self._user_notifications.get(user_id, [])
        
        # Apply filters
        filtered_notifications = []
        for notification in user_notifications:
            if channel_filter and notification.get("channel") != channel_filter:
                continue
            if unread_only and notification.get("read", False):
                continue
            filtered_notifications.append(notification)
        
        # Sort by creation time (newest first)
        filtered_notifications.sort(key=lambda n: n.get("created_at", ""), reverse=True)
        
        # Apply pagination
        paginated_notifications = filtered_notifications[offset:offset + limit]
        
        await self.send_message(connection_id, {
            "type": "notification_history_response",
            "notifications": paginated_notifications,
            "total_count": len(filtered_notifications),
            "offset": offset,
            "limit": limit
        })
        
        return True
    
    async def on_connect(self, connection_id: str, user_id: str, username: str, **kwargs):
        """Handle new connection for notification features"""
        await super().on_connect(connection_id, user_id, username, **kwargs)
        
        # Subscribe to default channels
        default_channels = ["system"]
        for channel in default_channels:
            if channel not in self._notification_channels:
                self._notification_channels[channel] = set()
            self._notification_channels[channel].add(user_id)
            
            if user_id not in self._user_channels:
                self._user_channels[user_id] = set()
            self._user_channels[user_id].add(channel)
        
        # Send any pending notifications
        await self._send_pending_notifications(user_id)
        
        self.logger.info(f"Notification connection established for user {username}")
    
    async def _send_pending_notifications(self, user_id: str):
        """Send any pending undelivered notifications to newly connected user"""
        user_notifications = self._user_notifications.get(user_id, [])
        pending_count = 0
        
        for notification in user_notifications:
            if not notification.get("delivered", False):
                await self._deliver_notification(user_id, notification)
                pending_count += 1
        
        if pending_count > 0:
            self.logger.info(f"Delivered {pending_count} pending notifications to user {user_id}")
    
    async def on_disconnect(self, connection_id: str, user_id: str, username: str):
        """Handle disconnection for notification features"""
        await super().on_disconnect(connection_id, user_id, username)
        
        # Note: We don't remove from channels on disconnect as user may reconnect
        # Channels are managed through explicit subscribe/unsubscribe
        
        self.logger.info(f"Notification disconnection handled for user {username}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification wrapper statistics"""
        stats = super().get_stats()
        
        # Calculate additional stats
        total_notifications = sum(len(notifications) for notifications in self._user_notifications.values())
        unread_notifications = sum(
            1 for notifications in self._user_notifications.values()
            for notification in notifications
            if not notification.get("read", False)
        )
        
        stats.update({
            'notification_stats': self._notification_stats,
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'active_channels': len(self._notification_channels),
            'users_with_notifications': len(self._user_notifications),
            'channel_subscriptions': sum(len(users) for users in self._notification_channels.values())
        })
        
        return stats
    
    def get_user_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notifications for a specific user"""
        user_notifications = self._user_notifications.get(user_id, [])
        # Sort by creation time (newest first)
        sorted_notifications = sorted(user_notifications, key=lambda n: n.get("created_at", ""), reverse=True)
        return sorted_notifications[:limit]
    
    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get subscribers for a specific channel"""
        return list(self._notification_channels.get(channel, set()))
    
    async def broadcast_to_channel(self, channel: str, notification: Dict[str, Any]):
        """Broadcast notification to all subscribers of a channel"""
        subscribers = self._notification_channels.get(channel, set())
        
        for user_id in subscribers:
            # Create personalized notification
            user_notification = {
                **notification,
                "id": f"notif_{datetime.utcnow().timestamp()}_{user_id}",
                "target_user_id": user_id,
                "channel": channel,
                "created_at": datetime.utcnow().isoformat(),
                "read": False,
                "delivered": False
            }
            
            # Store and deliver
            if user_id not in self._user_notifications:
                self._user_notifications[user_id] = []
            self._user_notifications[user_id].append(user_notification)
            
            await self._deliver_notification(user_id, user_notification)
        
        self._notification_stats['sent'] += len(subscribers)
        self.logger.info(f"Broadcasted notification to {len(subscribers)} subscribers of channel {channel}")