"""
Event Broadcasting System for Collaboration WebSocket

This module provides a centralized event broadcasting system for 
collaboration events like user presence, room updates, and system notifications.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Collaboration event types"""
    # User presence events
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    USER_ACTIVE = "user_active"
    USER_IDLE = "user_idle"
    
    # Room events
    ROOM_CREATED = "room_created"
    ROOM_UPDATED = "room_updated"
    ROOM_DELETED = "room_deleted"
    ROOM_USER_ADDED = "room_user_added"
    ROOM_USER_REMOVED = "room_user_removed"
    ROOM_USER_ROLE_CHANGED = "room_user_role_changed"
    
    # Collaboration events
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_DELETED = "document_deleted"
    DOCUMENT_SHARED = "document_shared"
    
    # System events
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_UPDATE = "system_update"
    
    # Activity events
    USER_STARTED_TYPING = "user_started_typing"
    USER_STOPPED_TYPING = "user_stopped_typing"
    USER_READING_MESSAGE = "user_reading_message"
    USER_COMPOSING_MESSAGE = "user_composing_message"


class CollaborationEvent:
    """Represents a collaboration event"""
    
    def __init__(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        room_id: Optional[str] = None,
        user_id: Optional[str] = None,
        target_users: Optional[List[str]] = None,
        exclude_users: Optional[List[str]] = None
    ):
        self.event_type = event_type
        self.data = data
        self.room_id = room_id
        self.user_id = user_id
        self.target_users = target_users or []
        self.exclude_users = exclude_users or []
        self.timestamp = datetime.utcnow()
        self.event_id = f"{event_type.value}_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for broadcasting"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat()
        }


class EventBroadcaster:
    """Handles event broadcasting for collaboration"""
    
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._broadcast_task = None
        self._event_handlers: Dict[EventType, List[callable]] = {}
        self._event_history: List[CollaborationEvent] = []
        self._max_history_size = 1000
    
    async def start(self):
        """Start the event broadcaster"""
        if self._broadcast_task:
            return
        
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("Event broadcaster started")
    
    async def stop(self):
        """Stop the event broadcaster"""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._broadcast_task = None
        logger.info("Event broadcaster stopped")
    
    async def _broadcast_loop(self):
        """Main broadcast loop"""
        while True:
            try:
                event = await self._event_queue.get()
                await self._broadcast_event(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
    
    async def _broadcast_event(self, event: CollaborationEvent):
        """Broadcast an event to relevant users"""
        try:
            # Add to history
            self._add_to_history(event)
            
            # Execute registered handlers
            await self._execute_handlers(event)
            
            # Determine recipients
            recipients = await self._determine_recipients(event)
            
            # Broadcast to recipients
            message = event.to_dict()
            for user_id in recipients:
                try:
                    if event.room_id:
                        await self.connection_manager.send_to_user(
                            event.room_id, user_id, message
                        )
                    else:
                        await self.connection_manager.send_personal_message(
                            user_id, message
                        )
                except Exception as e:
                    logger.error(f"Failed to send event to user {user_id}: {e}")
            
            logger.debug(f"Broadcasted event {event.event_type.value} to {len(recipients)} users")
            
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")
    
    async def _determine_recipients(self, event: CollaborationEvent) -> Set[str]:
        """Determine who should receive the event"""
        recipients = set()
        
        # If specific targets are defined, use them
        if event.target_users:
            recipients.update(event.target_users)
        
        # If room_id is specified, add all room members
        elif event.room_id:
            room_members = self.connection_manager.get_room_members(event.room_id)
            recipients.update(room_members)
        
        # For user presence events, notify all users in the same rooms
        elif event.event_type in [EventType.USER_ONLINE, EventType.USER_OFFLINE]:
            if event.user_id:
                user_rooms = self.connection_manager.get_user_rooms(event.user_id)
                for room_id in user_rooms:
                    room_members = self.connection_manager.get_room_members(room_id)
                    recipients.update(room_members)
        
        # For system events, notify all online users
        elif event.event_type in [EventType.SYSTEM_ANNOUNCEMENT, EventType.SYSTEM_MAINTENANCE]:
            # Get all online users from all rooms
            all_rooms = list(self.connection_manager.room_members.keys())
            for room_id in all_rooms:
                room_members = self.connection_manager.get_room_members(room_id)
                recipients.update(room_members)
        
        # Remove excluded users
        if event.exclude_users:
            for user_id in event.exclude_users:
                recipients.discard(user_id)
        
        # Remove the event originator unless it's a self-notification event
        if event.user_id and event.event_type not in [EventType.USER_ACTIVE, EventType.USER_IDLE]:
            recipients.discard(event.user_id)
        
        return recipients
    
    def _add_to_history(self, event: CollaborationEvent):
        """Add event to history with size limit"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
    
    async def _execute_handlers(self, event: CollaborationEvent):
        """Execute registered handlers for the event"""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error executing handler for {event.event_type.value}: {e}")
    
    def register_handler(self, event_type: EventType, handler: callable):
        """Register a handler for an event type"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: EventType, handler: callable):
        """Unregister a handler for an event type"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].remove(handler)
    
    async def broadcast(self, event: CollaborationEvent):
        """Queue an event for broadcasting"""
        await self._event_queue.put(event)
    
    async def broadcast_user_online(self, user_id: str, user_info: Dict[str, Any]):
        """Broadcast user online event"""
        event = CollaborationEvent(
            EventType.USER_ONLINE,
            {
                "user_id": user_id,
                "username": user_info.get("username", user_id),
                "role": user_info.get("role", "user"),
                "status": "online"
            },
            user_id=user_id
        )
        await self.broadcast(event)
    
    async def broadcast_user_offline(self, user_id: str):
        """Broadcast user offline event"""
        event = CollaborationEvent(
            EventType.USER_OFFLINE,
            {
                "user_id": user_id,
                "status": "offline"
            },
            user_id=user_id
        )
        await self.broadcast(event)
    
    async def broadcast_room_update(
        self,
        room_id: str,
        update_type: str,
        data: Dict[str, Any],
        exclude_user: Optional[str] = None
    ):
        """Broadcast room update event"""
        event_type_map = {
            "created": EventType.ROOM_CREATED,
            "updated": EventType.ROOM_UPDATED,
            "deleted": EventType.ROOM_DELETED,
            "user_added": EventType.ROOM_USER_ADDED,
            "user_removed": EventType.ROOM_USER_REMOVED,
            "role_changed": EventType.ROOM_USER_ROLE_CHANGED
        }
        
        event_type = event_type_map.get(update_type)
        if not event_type:
            logger.error(f"Unknown room update type: {update_type}")
            return
        
        event = CollaborationEvent(
            event_type,
            data,
            room_id=room_id,
            exclude_users=[exclude_user] if exclude_user else []
        )
        await self.broadcast(event)
    
    async def broadcast_system_announcement(
        self,
        title: str,
        message: str,
        severity: str = "info",
        target_rooms: Optional[List[str]] = None
    ):
        """Broadcast system announcement"""
        event = CollaborationEvent(
            EventType.SYSTEM_ANNOUNCEMENT,
            {
                "title": title,
                "message": message,
                "severity": severity
            }
        )
        
        # If specific rooms are targeted, send to those rooms only
        if target_rooms:
            recipients = set()
            for room_id in target_rooms:
                room_members = self.connection_manager.get_room_members(room_id)
                recipients.update(room_members)
            event.target_users = list(recipients)
        
        await self.broadcast(event)
    
    def get_recent_events(
        self,
        event_types: Optional[List[EventType]] = None,
        room_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent events from history"""
        filtered_events = []
        
        for event in reversed(self._event_history):
            # Filter by event type
            if event_types and event.event_type not in event_types:
                continue
            
            # Filter by room
            if room_id and event.room_id != room_id:
                continue
            
            # Filter by user
            if user_id and event.user_id != user_id:
                continue
            
            filtered_events.append(event.to_dict())
            
            if len(filtered_events) >= limit:
                break
        
        return filtered_events