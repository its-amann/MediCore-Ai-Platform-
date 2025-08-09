"""
Unified WebSocket Adapter for Collaboration Service

This adapter wraps the core WebSocket manager (app.core.websocket) 
to provide collaboration-specific functionality while maintaining 
backward compatibility with existing collaboration features.
"""

import logging
import asyncio
from typing import Dict, Any, Set, List, Optional, Callable
from datetime import datetime
from enum import Enum

# Import directly from the websocket module to avoid circular imports
import app.core.websocket as core_websocket_module
core_websocket_manager = core_websocket_module.websocket_manager
CoreMessageType = core_websocket_module.MessageType
ConnectionInfo = core_websocket_module.ConnectionInfo
from ..services.room_service import RoomService
from ..utils.auth_utils import verify_ws_token
from .chat_handler import ChatHandler, chat_handler
from .video_handler import VideoHandler, video_handler
from .event_broadcaster import EventBroadcaster, EventType, CollaborationEvent
from .error_handler import (
    ErrorHandler, WebSocketError, ErrorType as ErrorTypeEnum,
    ErrorSeverity, with_retry, RetryConfig, error_handler
)
from .message_formats import (
    MessageBuilder, MessageValidator, ChatMessage,
    ErrorMessage, RoomEvent, PresenceUpdate, MessageStatus
)

logger = logging.getLogger(__name__)


class CollaborationMessageType(Enum):
    """Collaboration-specific message types that extend core types"""
    # Connection
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_ERROR = "connection_error"
    
    # Room management
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    JOINED_ROOM = "joined_room"
    LEFT_ROOM = "left_room"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    
    # Chat
    CHAT_MESSAGE = "chat_message"
    SEND_MESSAGE = "send_message"
    TYPING_START = "typing_start" 
    TYPING_STOP = "typing_stop"
    TYPING = "typing"
    MESSAGE_READ = "message_read"
    ADD_REACTION = "add_reaction"
    REMOVE_REACTION = "remove_reaction"
    EDIT_MESSAGE = "edit_message"
    DELETE_MESSAGE = "delete_message"
    UPLOAD_FILE = "upload_file"
    GET_HISTORY = "get_history"
    
    # Video calls
    VIDEO_OFFER = "video_offer"
    VIDEO_ANSWER = "video_answer"
    VIDEO_CANDIDATE = "video_candidate"
    VIDEO_HANGUP = "video_hangup"
    JOIN_VIDEO = "join_video"
    LEAVE_VIDEO = "leave_video"
    WEBRTC_SIGNAL = "webrtc_signal"
    WEBRTC_OFFER = "webrtc_offer"
    WEBRTC_ANSWER = "webrtc_answer"
    ICE_CANDIDATE = "ice_candidate"
    TOGGLE_VIDEO = "toggle_video"
    TOGGLE_AUDIO = "toggle_audio"
    SCREEN_SHARE = "screen_share"
    RAISE_HAND = "raise_hand"
    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    QUALITY_REPORT = "quality_report"
    
    # AI assistance
    AI_REQUEST = "ai_request"
    AI_RESPONSE = "ai_response"
    AI_STREAMING_START = "ai_streaming_start"
    AI_STREAMING_DATA = "ai_streaming_data"
    AI_STREAMING_END = "ai_streaming_end"
    
    # Presence
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    USER_ACTIVITY = "user_activity"
    
    # Errors
    ERROR = "error"


class CollaborationConnectionManager:
    """Adapter that wraps the core WebSocket manager for collaboration-specific needs"""
    
    def __init__(self):
        self.core_manager = core_websocket_manager
        self.room_service = RoomService()
        
        # Map collaboration connection_ids to core connection_ids
        self._collaboration_to_core_connections: Dict[str, str] = {}
        self._core_to_collaboration_connections: Dict[str, str] = {}
        
        # Store room memberships: room_id -> set of user_ids
        self.room_members: Dict[str, Set[str]] = {}
        # Store user rooms: user_id -> set of room_ids  
        self.user_rooms: Dict[str, Set[str]] = {}
        # Store user last activity: user_id -> datetime
        self.user_last_activity: Dict[str, datetime] = {}
        # Store typing status: room_id -> set of user_ids currently typing
        self.room_typing_users: Dict[str, Set[str]] = {}
        
        # Use asyncio locks for thread safety
        self._connection_lock = asyncio.Lock()
        self._room_lock = asyncio.Lock()
        self._activity_lock = asyncio.Lock()
        
        # Connection health tracking
        self._connection_health: Dict[str, datetime] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task = None
    
    async def connect(self, room_id: str, user_id: str, websocket, username: str = None) -> bool:
        """
        Accept a new WebSocket connection and add user to room
        
        Args:
            room_id: The room ID to join
            user_id: The user ID
            websocket: The WebSocket connection
            username: Optional username for display
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            async with self._connection_lock:
                # Use the core manager to establish the connection
                core_connection_id = await self.core_manager.connect(
                    websocket, user_id, username or user_id
                )
                
                # Map the connection IDs
                collaboration_connection_id = f"collab_{core_connection_id}"
                self._collaboration_to_core_connections[collaboration_connection_id] = core_connection_id
                self._core_to_collaboration_connections[core_connection_id] = collaboration_connection_id
                
                if user_id not in self.user_rooms:
                    self.user_rooms[user_id] = set()
                
                # Update last activity
                await self.update_user_activity(room_id, user_id)
                
                logger.info(f"User {user_id} connected to collaboration WebSocket")
                
                # Join the room if room_id provided
                if room_id:
                    await self._join_room_internal(user_id, room_id)
                
                return True
                
        except Exception as e:
            logger.error(f"Error connecting user {user_id}: {e}")
            return False
    
    async def disconnect(self, room_id: str, user_id: str):
        """
        Remove a WebSocket connection and handle cleanup
        
        Args:
            room_id: The room ID to leave
            user_id: The user ID
        """
        async with self._connection_lock:
            # Find core connection ID
            core_connection_id = None
            collaboration_connection_id = None
            
            for collab_id, core_id in self._collaboration_to_core_connections.items():
                if core_id in self.core_manager._connections:
                    connection = self.core_manager._connections[core_id]
                    if connection.user_id == user_id:
                        core_connection_id = core_id
                        collaboration_connection_id = collab_id
                        break
            
            if core_connection_id:
                # Clean up mappings
                if collaboration_connection_id in self._collaboration_to_core_connections:
                    del self._collaboration_to_core_connections[collaboration_connection_id]
                if core_connection_id in self._core_to_collaboration_connections:
                    del self._core_to_collaboration_connections[core_connection_id]
                
                # Disconnect from core manager
                await self.core_manager.disconnect(core_connection_id)
            
            # Remove from typing users in all rooms
            for rid in list(self.room_typing_users.keys()):
                if user_id in self.room_typing_users.get(rid, set()):
                    self.room_typing_users[rid].discard(user_id)
                    # Notify others that user stopped typing
                    await self.broadcast_to_room(
                        rid,
                        {
                            "type": CollaborationMessageType.TYPING_STOP.value,
                            "room_id": rid,
                            "user_id": user_id,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        exclude_user=user_id
                    )
            
            # Remove from all rooms
            if user_id in self.user_rooms:
                for rid in list(self.user_rooms[user_id]):
                    await self._leave_room_internal(user_id, rid)
                del self.user_rooms[user_id]
            
            # Remove last activity
            if user_id in self.user_last_activity:
                del self.user_last_activity[user_id]
            
            logger.info(f"User {user_id} disconnected from collaboration WebSocket")
    
    async def _join_room_internal(self, user_id: str, room_id: str):
        """Internal method to add user to a room"""
        async with self._room_lock:
            if room_id not in self.room_members:
                self.room_members[room_id] = set()
            
            self.room_members[room_id].add(user_id)
            
            if user_id in self.user_rooms:
                self.user_rooms[user_id].add(room_id)
            
            # Join the core manager room as well
            await self.core_manager.join_room(self._get_core_connection_id(user_id), room_id)
            
            # Notify other room members
            await self.broadcast_to_room(
                room_id,
                {
                    "type": CollaborationMessageType.USER_JOINED.value,
                    "room_id": room_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user=user_id
            )
    
    async def _leave_room_internal(self, user_id: str, room_id: str):
        """Internal method to remove user from a room"""  
        async with self._room_lock:
            if room_id in self.room_members:
                self.room_members[room_id].discard(user_id)
                
            if user_id in self.user_rooms:
                self.user_rooms[user_id].discard(room_id)
            
            # Remove from typing users
            if room_id in self.room_typing_users:
                self.room_typing_users[room_id].discard(user_id)
            
            # Leave the core manager room as well
            core_connection_id = self._get_core_connection_id(user_id)
            if core_connection_id:
                await self.core_manager.leave_room(core_connection_id, room_id)
            
            # Notify other room members
            await self.broadcast_to_room(
                room_id,
                {
                    "type": CollaborationMessageType.USER_LEFT.value,
                    "room_id": room_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user=user_id
            )
    
    def _get_core_connection_id(self, user_id: str) -> Optional[str]:
        """Get core connection ID for a user - optimized with user lookup"""
        # Check if core manager has a user lookup method
        if hasattr(self.core_manager, 'get_user_connections'):
            connections = self.core_manager.get_user_connections(user_id)
            return connections[0] if connections else None
        
        # Fallback to linear search
        for core_id, connection in self.core_manager._connections.items():
            if connection.user_id == user_id:
                return core_id
        return None
    
    async def send_to_user(self, room_id: str, user_id: str, message: Dict[str, Any]):
        """
        Send message to a specific user in a room with health check
        
        Args:
            room_id: The room ID
            user_id: The target user ID  
            message: The message to send
        """
        # Check connection health before sending
        if not await self._is_connection_healthy(user_id):
            logger.warning(f"Skipping message to unhealthy connection: {user_id}")
            return
        
        # Add room_id to message if not present
        if "room_id" not in message:
            message["room_id"] = room_id
        
        try:
            # Use retry decorator for sending
            @with_retry(RetryConfig(max_attempts=3, initial_delay=0.5), error_handler)
            async def _send_with_retry():
                await self.core_manager.send_to_user(user_id, message)
            
            await _send_with_retry()
            
            # Update user activity
            await self.update_user_activity(room_id, user_id)
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id} after retries: {e}")
            # Mark connection as unhealthy
            await self._mark_connection_unhealthy(user_id)
            
            # Record error
            ws_error = WebSocketError(
                ErrorTypeEnum.BROADCAST_ERROR,
                f"Failed to send message to user {user_id}",
                ErrorSeverity.HIGH,
                details={"user_id": user_id, "error": str(e)}
            )
            await error_handler.handle_error(ws_error, user_id)
    
    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Send a personal message to a user - compatibility method"""
        await self.core_manager.send_to_user(user_id, message)
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None
    ):
        """
        Broadcast message to all users in a room using optimized core manager
        
        Args:
            room_id: The room ID
            message: The message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
        """
        # Add room_id to message if not present
        if "room_id" not in message:
            message["room_id"] = room_id
            
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Use core manager's optimized broadcast method
        if exclude_user:
            # Get all connection IDs except the excluded user
            connection_ids = []
            for core_id, connection in self.core_manager._connections.items():
                if connection.user_id != exclude_user and room_id in connection.rooms:
                    connection_ids.append(core_id)
            
            # Broadcast to specific connections
            if connection_ids:
                await self.core_manager.broadcast_to_connections(connection_ids, message)
        else:
            # Use direct room broadcast
            await self.core_manager.broadcast_to_room(room_id, message)
    
    async def broadcast_to_users(self, user_ids: List[str], message: Dict[str, Any]):
        """Broadcast message to specific users"""
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        for user_id in user_ids:
            await self.core_manager.send_to_user(user_id, message)
    
    async def update_user_activity(self, room_id: str, user_id: str):
        """
        Update user's last activity timestamp
        
        Args:
            room_id: The room ID
            user_id: The user ID
        """
        async with self._activity_lock:
            self.user_last_activity[user_id] = datetime.utcnow()
    
    async def handle_typing_indicator(self, room_id: str, user_id: str, is_typing: bool):
        """
        Handle typing indicator updates
        
        Args:
            room_id: The room ID
            user_id: The user ID
            is_typing: Whether user is typing
        """
        async with self._room_lock:
            if room_id not in self.room_typing_users:
                self.room_typing_users[room_id] = set()
                
            if is_typing:
                self.room_typing_users[room_id].add(user_id)
                message_type = CollaborationMessageType.TYPING_START.value
            else:
                self.room_typing_users[room_id].discard(user_id)
                message_type = CollaborationMessageType.TYPING_STOP.value
                
        # Broadcast typing status to room using standardized format
        typing_msg = MessageBuilder.typing_indicator(
            user_id=user_id,
            room_id=room_id,
            is_typing=is_typing,
            type=message_type
        )
        await self.broadcast_to_room(
            room_id,
            typing_msg,
            exclude_user=user_id
        )
    
    def get_room_members(self, room_id: str) -> List[str]:
        """Get list of users in a room"""
        return list(self.room_members.get(room_id, set()))
    
    def get_user_rooms(self, user_id: str) -> List[str]:
        """Get list of rooms a user is in"""
        return list(self.user_rooms.get(user_id, set()))
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user is online"""
        return self.core_manager.is_user_online(user_id)
    
    async def get_active_users(self, room_id: str, inactive_threshold_minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Get list of active users in a room with their status
        
        Args:
            room_id: The room ID
            inactive_threshold_minutes: Minutes of inactivity before considering user inactive
            
        Returns:
            List of user dictionaries with id, is_online, last_activity
        """
        if room_id not in self.room_members:
            return []
            
        active_users = []
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(minutes=inactive_threshold_minutes)
        
        for user_id in self.room_members[room_id]:
            user_info = {
                "user_id": user_id, 
                "is_online": self.is_user_online(user_id),
                "is_active": False,
                "last_activity": None
            }
            
            if user_id in self.user_last_activity:
                last_activity = self.user_last_activity[user_id]
                user_info["last_activity"] = last_activity.isoformat()
                user_info["is_active"] = last_activity > threshold
                
            active_users.append(user_info)
            
        return active_users
    
    async def _is_connection_healthy(self, user_id: str) -> bool:
        """Check if a user's connection is healthy"""
        # First check if user is online via core manager
        if not self.core_manager.is_user_online(user_id):
            return False
        
        # Check last activity
        if user_id in self.user_last_activity:
            last_activity = self.user_last_activity[user_id]
            inactive_duration = (datetime.utcnow() - last_activity).total_seconds()
            # Consider unhealthy if inactive for more than 2 minutes
            return inactive_duration < 120
        
        return True
    
    async def _mark_connection_unhealthy(self, user_id: str):
        """Mark a connection as unhealthy and handle cleanup"""
        logger.warning(f"Marking connection unhealthy for user {user_id}")
        
        # Remove from all rooms
        if user_id in self.user_rooms:
            for room_id in list(self.user_rooms[user_id]):
                await self._leave_room_internal(user_id, room_id)
    
    async def _start_health_check_task(self):
        """Start periodic health check task"""
        if self._health_check_task:
            return
        
        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(self._health_check_interval)
                    await self._perform_health_check()
                except Exception as e:
                    logger.error(f"Health check error: {e}")
        
        self._health_check_task = asyncio.create_task(health_check_loop())
    
    async def _perform_health_check(self):
        """Perform health check on all connections"""
        users_to_check = list(self.user_last_activity.keys())
        current_time = datetime.utcnow()
        
        for user_id in users_to_check:
            last_activity = self.user_last_activity.get(user_id)
            if last_activity:
                inactive_duration = (current_time - last_activity).total_seconds()
                # Remove users inactive for more than 5 minutes
                if inactive_duration > 300:
                    logger.info(f"Removing inactive user {user_id} (inactive for {inactive_duration}s)")
                    await self._mark_connection_unhealthy(user_id)
    
    async def cleanup_stale_data(self):
        """Clean up stale room and typing data"""
        # Clean up empty rooms
        empty_rooms = [room_id for room_id, members in self.room_members.items() if not members]
        for room_id in empty_rooms:
            del self.room_members[room_id]
            if room_id in self.room_typing_users:
                del self.room_typing_users[room_id]
        
        # Clean up typing indicators for offline users
        for room_id in list(self.room_typing_users.keys()):
            offline_typing_users = []
            for user_id in self.room_typing_users[room_id]:
                if not await self._is_connection_healthy(user_id):
                    offline_typing_users.append(user_id)
            
            for user_id in offline_typing_users:
                self.room_typing_users[room_id].discard(user_id)
                # Notify room about stopped typing
                await self.broadcast_to_room(
                    room_id,
                    {
                        "type": CollaborationMessageType.TYPING_STOP.value,
                        "room_id": room_id,
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    exclude_user=user_id
                )


class UnifiedWebSocketManager:
    """
    Main WebSocket manager that wraps the core WebSocket manager
    and provides collaboration-specific functionality
    """
    
    def __init__(self):
        self.connection_manager = CollaborationConnectionManager()
        self.room_service = RoomService()
        self.chat_handler = chat_handler
        self.video_handler = video_handler
        self.handlers: Dict[str, Callable] = {}
        
        # Initialize event broadcaster
        self.event_broadcaster = EventBroadcaster(self.connection_manager)
        
        # Register collaboration-specific handlers
        self._register_collaboration_handlers()
        
        # Async initialization will be done during app startup
        self._initialized = False
    
    async def initialize(self):
        """Initialize async components - call during app startup"""
        if not self._initialized:
            await self._initialize_async_components()
            self._initialized = True
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        self.handlers[event_type] = handler
    
    def _register_collaboration_handlers(self):
        """Register all collaboration-specific message handlers"""
        # Chat handlers
        self.register_handler("send_message", self.chat_handler.handle_send_message)
        self.register_handler("typing", self.chat_handler.handle_typing_indicator)
        self.register_handler("message_read", self.chat_handler.handle_message_read)
        self.register_handler("add_reaction", self.chat_handler.handle_add_reaction)
        self.register_handler("remove_reaction", self.chat_handler.handle_remove_reaction)
        self.register_handler("edit_message", self.chat_handler.handle_edit_message)
        self.register_handler("delete_message", self.chat_handler.handle_delete_message)
        
        # Video handlers
        self.register_handler("join_video", self.video_handler.handle_join_video)
        self.register_handler("leave_video", self.video_handler.handle_leave_video)
        self.register_handler("webrtc_signal", self.video_handler.handle_webrtc_signal)
        self.register_handler("toggle_video", self.video_handler.handle_toggle_video)
        self.register_handler("toggle_audio", self.video_handler.handle_toggle_audio)
        self.register_handler("screen_share", self.video_handler.handle_screen_share)
        self.register_handler("raise_hand", self.video_handler.handle_raise_hand)
        self.register_handler("start_recording", self.video_handler.handle_start_recording)
        self.register_handler("stop_recording", self.video_handler.handle_stop_recording)
        self.register_handler("quality_report", self.video_handler.handle_quality_report)
        
        # File upload handler
        self.register_handler("upload_file", lambda user_id, data, cm: 
            self.chat_handler.handle_file_upload(data.get("room_id"), user_id, data, cm))
        self.register_handler("get_history", lambda user_id, data, cm:
            self.chat_handler.get_message_history(data.get("room_id"), data.get("limit", 50), data.get("before")))
    
    async def _initialize_async_components(self):
        """Initialize async components like health checks and event broadcaster"""
        # Start event broadcaster
        await self.event_broadcaster.start()
        
        # Start health check tasks
        await self.connection_manager._start_health_check_task()
        
        # Also start periodic cleanup
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # Cleanup every minute
                    await self.connection_manager.cleanup_stale_data()
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
        
        asyncio.create_task(cleanup_loop())
    
    async def handle_connection(self, websocket, token: str, room_id: Optional[str] = None):
        """Handle a new WebSocket connection with enhanced authentication"""
        try:
            # Verify token and get user info
            user_info = await verify_ws_token(token)
            if not user_info:
                logger.warning(f"Invalid WebSocket authentication token from {websocket.client.host}")
                await websocket.close(code=1008, reason="Invalid authentication")
                return
            
            user_id = user_info["user_id"]
            username = user_info.get("name", user_info.get("username", user_id))
            user_role = user_info.get("role", "user")
            
            logger.info(f"WebSocket authentication successful for user {user_id} (role: {user_role})")
            
            # Connect user
            success = await self.connection_manager.connect(room_id or "", user_id, websocket, username)
            if not success:
                await websocket.close(code=1011, reason="Connection failed")
                return
            
            # Broadcast user online event
            await self.event_broadcaster.broadcast_user_online(user_id, {
                "username": username,
                "role": user_role
            })
            
            try:
                # Send connection success message with user info using standardized format
                connection_msg = MessageBuilder.notification(
                    title="Connection Established",
                    body=f"Welcome {username}!",
                    category="success",
                    type=CollaborationMessageType.CONNECTION_ESTABLISHED.value,
                    user_id=user_id,
                    username=username,
                    user_role=user_role
                )
                await websocket.send_json(connection_msg)
                
                # If room_id provided, join the room
                if room_id:
                    await self.handle_join_room(user_id, {"room_id": room_id})
                
                # Handle messages
                while True:
                    try:
                        data = await websocket.receive_json()
                        
                        # Validate message structure
                        if not isinstance(data, dict):
                            error_msg = MessageBuilder.error_message(
                                error_code="INVALID_FORMAT",
                                error_type="validation_error",
                                message="Invalid message format: expected JSON object"
                            )
                            await websocket.send_json(error_msg)
                            continue
                        
                        # Add user context to message
                        data["_user_context"] = {
                            "user_id": user_id,
                            "username": username,
                            "role": user_role
                        }
                        
                        await self.handle_message(user_id, data)
                        
                    except ValueError as e:
                        logger.error(f"Invalid JSON from user {user_id}: {e}")
                        await websocket.send_json({
                            "type": CollaborationMessageType.ERROR.value,
                            "message": "Invalid JSON format",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
            except Exception as e:
                logger.error(f"WebSocket error for user {user_id}: {e}")
            finally:
                # Broadcast user offline event
                await self.event_broadcaster.broadcast_user_offline(user_id)
                
                await self.connection_manager.disconnect(room_id or "", user_id)
                if not websocket.client_state.name == "DISCONNECTED":
                    await websocket.close(code=1011, reason="Internal error")
                    
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            if not websocket.client_state.name == "DISCONNECTED":
                await websocket.close(code=1011, reason="Internal error")
    
    async def handle_message(self, user_id: str, data: Dict[str, Any]):
        """Route message to appropriate handler with validation"""
        message_type = data.get("type")
        room_id = data.get("room_id", "")
        
        if not message_type:
            error_msg = MessageBuilder.error_message(
                error_code="MISSING_TYPE",
                error_type="validation_error",
                message="Message type is required",
                room_id=room_id
            )
            await self.connection_manager.send_to_user(
                room_id,
                user_id,
                error_msg
            )
            return
        
        # Validate message format if applicable
        try:
            validated_msg = MessageValidator.validate(data)
            logger.debug(f"Validated message type {message_type} from user {user_id}")
        except ValueError as e:
            logger.warning(f"Invalid message format from user {user_id}: {e}")
            # Continue processing even if validation fails for backward compatibility
        
        try:
            # Update user activity on any message
            await self.connection_manager.update_user_activity(room_id, user_id)
            
            # Handle room operations
            if message_type == CollaborationMessageType.JOIN_ROOM.value:
                await self.handle_join_room(user_id, data)
            elif message_type == CollaborationMessageType.LEAVE_ROOM.value:
                await self.handle_leave_room(user_id, data)
                
            # Handle chat messages
            elif message_type == CollaborationMessageType.CHAT_MESSAGE.value:
                await self.handle_chat_message(user_id, data)
                
            # Handle typing indicators
            elif message_type in [CollaborationMessageType.TYPING_START.value, CollaborationMessageType.TYPING_STOP.value]:
                await self.handle_typing_indicator(user_id, data)
                
            # Handle video call signals
            elif message_type in [CollaborationMessageType.VIDEO_OFFER.value, CollaborationMessageType.VIDEO_ANSWER.value, 
                                CollaborationMessageType.VIDEO_CANDIDATE.value, CollaborationMessageType.VIDEO_HANGUP.value]:
                await self.handle_video_signal(user_id, data)
                
            # Handle AI assistance
            elif message_type == CollaborationMessageType.AI_REQUEST.value:
                await self.handle_ai_request(user_id, data)
                
            # Handle user activity
            elif message_type == CollaborationMessageType.USER_ACTIVITY.value:
                # Just update activity, already done above
                pass
                
            # Route to registered handlers
            elif message_type in self.handlers:
                handler = self.handlers[message_type]
                await handler(user_id, data, self.connection_manager)
            
            else:
                await self.connection_manager.send_to_user(
                    room_id,
                    user_id,
                    {
                        "type": CollaborationMessageType.ERROR.value,
                        "message": f"Unknown message type: {message_type}"
                    }
                )
                
        except WebSocketError as ws_error:
            # Handle known WebSocket errors
            error_response = await error_handler.handle_error(ws_error, user_id, {"message_type": message_type})
            error_response["type"] = CollaborationMessageType.ERROR.value
            
            await self.connection_manager.send_to_user(
                room_id,
                user_id,
                error_response
            )
            
            # Check if user should be disconnected
            if error_handler.should_disconnect_user(user_id):
                logger.warning(f"Disconnecting user {user_id} due to excessive errors")
                raise Exception("Excessive errors")
                
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Error handling message from user {user_id}: {e}")
            
            ws_error = WebSocketError(
                ErrorTypeEnum.HANDLER_ERROR,
                "Error processing message",
                ErrorSeverity.HIGH,
                details={"error": str(e), "message_type": message_type}
            )
            
            error_response = await error_handler.handle_error(ws_error, user_id)
            error_response["type"] = CollaborationMessageType.ERROR.value
            
            await self.connection_manager.send_to_user(
                room_id,
                user_id,
                error_response
            )
    
    async def handle_join_room(self, user_id: str, data: Dict[str, Any]):
        """Handle room join request"""
        room_id = data.get("room_id")
        if not room_id:
            await self.connection_manager.send_to_user(
                "",
                user_id,
                {
                    "type": CollaborationMessageType.ERROR.value,
                    "message": "room_id is required"
                }
            )
            return
        
        # Verify user has access to room
        participant = await self.room_service.get_participant(room_id, user_id)
        if not participant:
            await self.connection_manager.send_to_user(
                room_id,
                user_id,
                {
                    "type": CollaborationMessageType.ERROR.value,
                    "message": "Not authorized to join this room"
                }
            )
            return
        
        # Get username from user context if available
        username = data.get("_user_context", {}).get("username", user_id)
        
        # Join room
        await self.connection_manager._join_room_internal(user_id, room_id)
        
        # Get active users in the room
        active_users = await self.connection_manager.get_active_users(room_id)
        
        # Broadcast room user added event
        await self.event_broadcaster.broadcast_room_update(
            room_id,
            "user_added",
            {
                "room_id": room_id,
                "user_id": user_id,
                "username": username,
                "role": participant.role if participant else "member"
            },
            exclude_user=user_id
        )
        
        # Send success response
        await self.connection_manager.send_to_user(
            room_id,
            user_id,
            {
                "type": CollaborationMessageType.JOINED_ROOM.value,
                "room_id": room_id,
                "members": self.connection_manager.get_room_members(room_id),
                "active_users": active_users
            }
        )
    
    async def handle_leave_room(self, user_id: str, data: Dict[str, Any]):
        """Handle room leave request"""
        room_id = data.get("room_id")
        if not room_id:
            await self.connection_manager.send_to_user(
                "",
                user_id,
                {
                    "type": CollaborationMessageType.ERROR.value,
                    "message": "room_id is required"
                }
            )
            return
        
        # Leave room
        await self.connection_manager._leave_room_internal(user_id, room_id)
        
        # Send success response
        await self.connection_manager.send_to_user(
            room_id,
            user_id,
            {
                "type": CollaborationMessageType.LEFT_ROOM.value,
                "room_id": room_id
            }
        )
    
    async def handle_chat_message(self, user_id: str, data: Dict[str, Any]):
        """Handle chat message with standardized format"""
        room_id = data.get("room_id")
        content = data.get("content")
        
        if not room_id or not content:
            error_msg = MessageBuilder.error_message(
                error_code="MISSING_FIELDS",
                error_type="validation_error",
                message="room_id and content are required",
                details={"missing_fields": [f for f in ["room_id", "content"] if not data.get(f)]}
            )
            await self.connection_manager.send_to_user(
                room_id or "",
                user_id,
                error_msg
            )
            return
        
        # Get username from user context
        username = data.get("_user_context", {}).get("username", user_id)
        
        # Create standardized chat message
        chat_msg = MessageBuilder.chat_message(
            user_id=user_id,
            room_id=room_id,
            content=content,
            username=username,
            status=MessageStatus.SENT,
            mentions=data.get("mentions", []),
            reply_to=data.get("reply_to")
        )
        
        # Broadcast message to room
        await self.connection_manager.broadcast_to_room(
            room_id,
            chat_msg,
            exclude_user=user_id
        )
        
        # Send acknowledgment to sender with delivered status
        ack_msg = chat_msg.copy()
        ack_msg["status"] = MessageStatus.DELIVERED.value
        await self.connection_manager.send_to_user(
            room_id,
            user_id,
            ack_msg
        )
    
    async def handle_typing_indicator(self, user_id: str, data: Dict[str, Any]):
        """Handle typing indicator with standardized format"""
        room_id = data.get("room_id")
        is_typing = data.get("type") == CollaborationMessageType.TYPING_START.value
        
        if not room_id:
            error_msg = MessageBuilder.error_message(
                error_code="MISSING_ROOM_ID",
                error_type="validation_error",
                message="room_id is required"
            )
            await self.connection_manager.send_to_user(
                "",
                user_id,
                error_msg
            )
            return
        
        # Get username from user context
        username = data.get("_user_context", {}).get("username", user_id)
        
        # Create standardized typing indicator
        typing_msg = MessageBuilder.typing_indicator(
            user_id=user_id,
            room_id=room_id,
            is_typing=is_typing,
            username=username,
            typing_in_thread=data.get("thread_id")
        )
        
        # Update typing state and broadcast
        await self.connection_manager.handle_typing_indicator(room_id, user_id, is_typing)
    
    async def handle_video_signal(self, user_id: str, data: Dict[str, Any]):
        """Handle video call signaling"""
        room_id = data.get("room_id")
        target_user = data.get("target_user")
        signal_type = data.get("type")
        signal_data = data.get("data")
        
        if not room_id:
            await self.connection_manager.send_to_user(
                "",
                user_id,
                {
                    "type": CollaborationMessageType.ERROR.value,
                    "message": "room_id is required"
                }
            )
            return
        
        # For hangup, broadcast to all in room
        if signal_type == CollaborationMessageType.VIDEO_HANGUP.value:
            await self.connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": signal_type,
                    "room_id": room_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user=user_id
            )
        # For other signals, send to specific target
        elif target_user:
            await self.connection_manager.send_to_user(
                room_id,
                target_user,
                {
                    "type": signal_type,
                    "room_id": room_id,
                    "user_id": user_id,
                    "data": signal_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        else:
            await self.connection_manager.send_to_user(
                room_id,
                user_id,
                {
                    "type": CollaborationMessageType.ERROR.value,
                    "message": "target_user is required for video signals"
                }
            )
    
    async def handle_ai_request(self, user_id: str, data: Dict[str, Any]):
        """Handle AI assistance request"""
        room_id = data.get("room_id")
        request_type = data.get("request_type")
        request_data = data.get("data")
        
        if not room_id or not request_type:
            await self.connection_manager.send_to_user(
                room_id or "",
                user_id,
                {
                    "type": CollaborationMessageType.ERROR.value,
                    "message": "room_id and request_type are required"
                }
            )
            return
        
        # Handle AI request through registered handler if available
        ai_handler = self.handlers.get("ai_request_handler")
        if ai_handler:
            try:
                # Start streaming
                await self.connection_manager.send_to_user(
                    room_id,
                    user_id,
                    {
                        "type": CollaborationMessageType.AI_STREAMING_START.value,
                        "room_id": room_id,
                        "request_id": data.get("request_id"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                # Process through AI handler
                await ai_handler(user_id, data, self.connection_manager)
                
            except Exception as e:
                logger.error(f"Error processing AI request: {e}")
                await self.connection_manager.send_to_user(
                    room_id,
                    user_id,
                    {
                        "type": CollaborationMessageType.ERROR.value,
                        "message": "Error processing AI request",
                        "details": str(e)
                    }
                )
        else:
            # No AI handler registered
            await self.connection_manager.send_to_user(
                room_id,
                user_id,
                {
                    "type": CollaborationMessageType.ERROR.value,
                    "message": "AI assistance not available"
                }
            )
    
    async def send_notification(self, user_id: str, data: Dict[str, Any]):
        """Send a notification to a specific user"""
        await self.connection_manager.send_personal_message(user_id, data)
    
    async def disconnect_all(self):
        """Disconnect all active WebSocket connections"""
        logger.info("Disconnecting all collaboration WebSocket connections...")
        
        # Get copy of all user IDs to avoid modification during iteration
        user_ids = []
        for user_id in list(self.connection_manager.user_rooms.keys()):
            user_ids.append(user_id)
        
        for user_id in user_ids:
            try:
                # Get user's rooms for proper cleanup
                user_rooms = self.connection_manager.get_user_rooms(user_id)
                
                # Disconnect from each room
                for room_id in user_rooms:
                    await self.connection_manager.disconnect(room_id, user_id)
                        
            except Exception as e:
                logger.error(f"Error disconnecting user {user_id}: {e}")
        
        # Clear collaboration-specific data structures
        self.connection_manager.room_members.clear()
        self.connection_manager.user_rooms.clear()
        self.connection_manager.user_last_activity.clear()
        self.connection_manager.room_typing_users.clear()
        
        logger.info("All collaboration WebSocket connections disconnected")
    
    def get_active_connections_count(self) -> int:
        """Get total number of active connections"""
        return self.connection_manager.core_manager.get_connection_stats()["active_connections"]
    
    # Backward compatibility methods
    async def connect(self, websocket, room_id: str, user_id: str, connection_type: str = "chat"):
        """Backward compatibility connect method"""
        return await self.connection_manager.connect(room_id, user_id, websocket)
    
    async def disconnect(self, room_id: str, user_id: str, connection_type: str = "chat"):
        """Backward compatibility disconnect method""" 
        return await self.connection_manager.disconnect(room_id, user_id)
    
    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any]):
        """Backward compatibility broadcast method"""
        return await self.connection_manager.broadcast_to_room(room_id, message)


# Global unified WebSocket manager instance
websocket_manager = UnifiedWebSocketManager()