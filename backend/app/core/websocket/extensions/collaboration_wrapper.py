"""
Collaboration WebSocket Wrapper

Wraps the collaboration microservice WebSocket functionality for integration
with the unified WebSocket architecture.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from .base_wrapper import MicroserviceWrapper
from app.microservices.collaboration.websocket.unified_websocket_adapter import (
    UnifiedWebSocketManager as CollaborationWebSocketManager,
    CollaborationMessageType
)

logger = logging.getLogger(__name__)


class CollaborationWrapper(MicroserviceWrapper):
    """
    WebSocket wrapper for collaboration microservice
    
    This wrapper integrates the collaboration microservice's WebSocket
    functionality with the unified WebSocket system, providing:
    - Chat functionality
    - Room management
    - Video call signaling
    - AI assistance integration
    - User presence tracking
    """
    
    def __init__(self, priority: int = 50):
        """Initialize the collaboration wrapper"""
        # Get the collaboration WebSocket manager instance
        from ...microservices.collaboration.websocket.unified_websocket_adapter import websocket_manager
        
        super().__init__(
            name="collaboration",
            microservice_manager=websocket_manager,
            priority=priority
        )
        
        # Supported message types
        self._supported_types = [
            "join_room", "leave_room", "chat_message",
            "typing_start", "typing_stop", "user_activity",
            "video_offer", "video_answer", "video_candidate", "video_hangup",
            "ai_request", "ai_response", "ai_streaming_start", "ai_streaming_data", "ai_streaming_end"
        ]
        
        # Set up message type mappings
        self._setup_message_mappings()
        
        # Connection tracking for collaboration features
        self._user_rooms: Dict[str, set] = {}
        self._room_users: Dict[str, set] = {}
    
    def _setup_message_mappings(self):
        """Set up message type mappings between unified and collaboration formats"""
        mappings = {
            # Room operations
            "join_room": CollaborationMessageType.JOIN_ROOM.value,
            "leave_room": CollaborationMessageType.LEAVE_ROOM.value,
            
            # Chat messages
            "chat_message": CollaborationMessageType.CHAT_MESSAGE.value,
            "typing_start": CollaborationMessageType.TYPING_START.value,
            "typing_stop": CollaborationMessageType.TYPING_STOP.value,
            
            # Video calls
            "video_offer": CollaborationMessageType.VIDEO_OFFER.value,
            "video_answer": CollaborationMessageType.VIDEO_ANSWER.value,
            "video_candidate": CollaborationMessageType.VIDEO_CANDIDATE.value,
            "video_hangup": CollaborationMessageType.VIDEO_HANGUP.value,
            
            # AI assistance
            "ai_request": CollaborationMessageType.AI_REQUEST.value,
            "ai_response": CollaborationMessageType.AI_RESPONSE.value,
            "ai_streaming_start": CollaborationMessageType.AI_STREAMING_START.value,
            "ai_streaming_data": CollaborationMessageType.AI_STREAMING_DATA.value,
            "ai_streaming_end": CollaborationMessageType.AI_STREAMING_END.value,
            
            # User activity
            "user_activity": CollaborationMessageType.USER_ACTIVITY.value,
        }
        
        for unified_type, collaboration_type in mappings.items():
            self.add_message_type_mapping(unified_type, collaboration_type)
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize the collaboration wrapper"""
        await super().initialize(config)
        
        # Register custom handlers with the collaboration manager if needed
        if hasattr(self.microservice_manager, 'register_handler'):
            # Register any custom handlers for collaboration-specific features
            pass
        
        self.logger.info("Collaboration wrapper initialized")
    
    async def shutdown(self):
        """Shutdown the collaboration wrapper"""
        # Clean up resources
        self._user_rooms.clear()
        self._room_users.clear()
        
        await super().shutdown()
        self.logger.info("Collaboration wrapper shutdown")
    
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
            
            # Handle room-specific operations
            if message_type in ["join_room", "leave_room"]:
                return await self._handle_room_operation(connection_id, user_id, message)
            
            # Handle chat messages
            elif message_type in ["chat_message", "typing_start", "typing_stop"]:
                return await self._handle_chat_operation(connection_id, user_id, message)
            
            # Handle video operations
            elif message_type in ["video_offer", "video_answer", "video_candidate", "video_hangup"]:
                return await self._handle_video_operation(connection_id, user_id, message)
            
            # Handle AI operations
            elif message_type in ["ai_request"]:
                return await self._handle_ai_operation(connection_id, user_id, message)
            
            # Handle user activity
            elif message_type == "user_activity":
                return await self._handle_user_activity(connection_id, user_id, message)
            
            # Forward other messages to collaboration manager
            else:
                return await self.forward_to_microservice(connection_id, message)
        
        except Exception as e:
            self.logger.error(f"Error handling collaboration message {message_type}: {e}")
            return False
    
    async def _handle_room_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle room join/leave operations"""
        message_type = message.get("type")
        room_id = message.get("room_id")
        
        if not room_id:
            await self.send_message(connection_id, {
                "type": "error",
                "message": "room_id is required"
            })
            return False
        
        try:
            if message_type == "join_room":
                # Track user-room relationship
                if user_id not in self._user_rooms:
                    self._user_rooms[user_id] = set()
                if room_id not in self._room_users:
                    self._room_users[room_id] = set()
                
                self._user_rooms[user_id].add(room_id)
                self._room_users[room_id].add(user_id)
                
                # Forward to collaboration manager
                await self.microservice_manager.handle_join_room(user_id, message)
                
            elif message_type == "leave_room":
                # Remove from tracking
                if user_id in self._user_rooms:
                    self._user_rooms[user_id].discard(room_id)
                if room_id in self._room_users:
                    self._room_users[room_id].discard(user_id)
                
                # Forward to collaboration manager
                await self.microservice_manager.handle_leave_room(user_id, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling room operation: {e}")
            return False
    
    async def _handle_chat_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle chat-related operations"""
        try:
            # Forward to collaboration manager
            return await self.forward_to_microservice(connection_id, message)
        except Exception as e:
            self.logger.error(f"Error handling chat operation: {e}")
            return False
    
    async def _handle_video_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle video call operations"""
        try:
            # Forward to collaboration manager
            return await self.forward_to_microservice(connection_id, message)
        except Exception as e:
            self.logger.error(f"Error handling video operation: {e}")
            return False
    
    async def _handle_ai_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle AI assistance operations"""
        try:
            # Forward to collaboration manager
            return await self.forward_to_microservice(connection_id, message)
        except Exception as e:
            self.logger.error(f"Error handling AI operation: {e}")
            return False
    
    async def _handle_user_activity(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle user activity updates"""
        try:
            room_id = message.get("room_id", "")
            
            # Update activity in collaboration manager
            if hasattr(self.microservice_manager.connection_manager, 'update_user_activity'):
                await self.microservice_manager.connection_manager.update_user_activity(room_id, user_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling user activity: {e}")
            return False
    
    async def on_connect(self, connection_id: str, user_id: str, username: str, **kwargs):
        """Handle new connection for collaboration features"""
        await super().on_connect(connection_id, user_id, username, **kwargs)
        
        # Initialize user tracking
        if user_id not in self._user_rooms:
            self._user_rooms[user_id] = set()
        
        self.logger.info(f"Collaboration connection established for user {username}")
    
    async def on_disconnect(self, connection_id: str, user_id: str, username: str):
        """Handle disconnection for collaboration features"""
        await super().on_disconnect(connection_id, user_id, username)
        
        # Clean up user from all rooms
        if user_id in self._user_rooms:
            user_rooms = self._user_rooms[user_id].copy()
            for room_id in user_rooms:
                if room_id in self._room_users:
                    self._room_users[room_id].discard(user_id)
                
                # Notify collaboration manager
                try:
                    await self.microservice_manager.connection_manager.disconnect(room_id, user_id)
                except Exception as e:
                    self.logger.error(f"Error disconnecting from collaboration room {room_id}: {e}")
            
            del self._user_rooms[user_id]
        
        self.logger.info(f"Collaboration disconnection handled for user {username}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collaboration wrapper statistics"""
        stats = super().get_stats()
        
        stats.update({
            'active_users': len(self._user_rooms),
            'active_rooms': len(self._room_users),
            'total_user_room_connections': sum(len(rooms) for rooms in self._user_rooms.values()),
            'collaboration_manager_stats': (
                self.microservice_manager.get_active_connections_count()
                if hasattr(self.microservice_manager, 'get_active_connections_count')
                else 'N/A'
            )
        })
        
        return stats
    
    def get_user_rooms(self, user_id: str) -> List[str]:
        """Get rooms that a user is in"""
        return list(self._user_rooms.get(user_id, set()))
    
    def get_room_users(self, room_id: str) -> List[str]:
        """Get users in a room"""
        return list(self._room_users.get(room_id, set()))
    
    def is_user_in_room(self, user_id: str, room_id: str) -> bool:
        """Check if user is in a specific room"""
        return room_id in self._user_rooms.get(user_id, set())
    
    async def broadcast_to_collaboration_room(self, room_id: str, message: Dict[str, Any], exclude_user: Optional[str] = None):
        """Broadcast message to all users in a collaboration room"""
        try:
            # Use the collaboration manager's broadcast functionality
            await self.microservice_manager.connection_manager.broadcast_to_room(
                room_id, message, exclude_user
            )
        except Exception as e:
            self.logger.error(f"Error broadcasting to collaboration room {room_id}: {e}")
    
    async def send_to_collaboration_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to a user through collaboration manager"""
        try:
            # Use the collaboration manager's send functionality
            if hasattr(self.microservice_manager.connection_manager, 'send_to_user'):
                await self.microservice_manager.connection_manager.send_to_user("", user_id, message)
        except Exception as e:
            self.logger.error(f"Error sending to collaboration user {user_id}: {e}")