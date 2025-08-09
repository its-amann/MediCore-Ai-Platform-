"""
WebSocket Manager for real-time communication
"""
import logging
from typing import Dict, Set, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum
import json
import uuid
import asyncio
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""
    CHAT = "chat"
    CHAT_MESSAGE = "chat_message"
    USER_TYPING = "user_typing"
    USER_STOPPED_TYPING = "user_stopped_typing"
    NOTIFICATION = "notification"
    CASE_UPDATE = "case_update"
    ROOM_UPDATE = "room_update"
    USER_STATUS = "user_status"
    ERROR = "error"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    ROOM_PARTICIPANT_JOINED = "room_participant_joined"
    ROOM_PARTICIPANT_LEFT = "room_participant_left"
    SCREEN_SHARE_STARTED = "screen_share_started"
    SCREEN_SHARE_STOPPED = "screen_share_stopped"
    VIDEO_STARTED = "video_started"
    VIDEO_STOPPED = "video_stopped"
    HAND_RAISED = "hand_raised"
    HAND_LOWERED = "hand_lowered"


@dataclass
class ConnectionInfo:
    """Stores information about a WebSocket connection"""
    connection_id: str
    websocket: WebSocket
    user_id: str
    username: str
    connected_at: datetime
    rooms: Set[str] = field(default_factory=set)
    is_alive: bool = True
    last_ping: Optional[datetime] = None
    connection_state: str = "connecting"  # connecting, connected, closing, closed


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Map of connection_id to ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        # Map of user_id to set of connection_ids
        self._user_connections: Dict[str, Set[str]] = {}
        # Map of room_id to set of connection_ids
        self._room_connections: Dict[str, Set[str]] = {}
        # Message handlers
        self.message_handlers: Dict[MessageType, callable] = {}
        # Heartbeat management
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_timeout = 10   # seconds
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Connection pooling and limits
        self._max_connections_per_user = 5  # Maximum concurrent connections per user
        self._max_total_connections = 1000  # Maximum total connections
        self._connection_cleanup_interval = 300  # 5 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocketManager initialized")
        
        # Start background tasks
        self._start_heartbeat_task()
        self._start_cleanup_task()
    
    async def connect(self, websocket: WebSocket, user_id: str, username: str) -> str:
        """Accept a new WebSocket connection and track it with proper lifecycle management"""
        # Generate unique connection ID first
        connection_id = str(uuid.uuid4())
        
        try:
            # Check connection limits before accepting
            if len(self._connections) >= self._max_total_connections:
                logger.warning(f"Maximum total connections ({self._max_total_connections}) reached")
                await websocket.close(code=1008, reason="Server capacity exceeded")
                raise ValueError("Maximum total connections reached")
            
            # Check per-user connection limit
            user_connections = self._user_connections.get(user_id, set())
            if len(user_connections) >= self._max_connections_per_user:
                logger.warning(f"Maximum connections per user ({self._max_connections_per_user}) reached for user {username}")
                # Close oldest connection for this user
                await self._close_oldest_user_connection(user_id)
            
            # Check if websocket is already accepted (prevent double accept)
            if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTING":
                logger.warning(f"WebSocket already in state {websocket.client_state.name}, cannot accept")
                raise ValueError(f"WebSocket in invalid state: {websocket.client_state.name}")
            
            # Accept the connection
            await websocket.accept()
            logger.info(f"WebSocket accepted for connection_id={connection_id}")
            
            # Create connection info
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                websocket=websocket,
                user_id=user_id,
                username=username,
                connected_at=datetime.utcnow(),
                rooms=set(),
                is_alive=True,
                last_ping=datetime.utcnow(),
                connection_state="connected"
            )
            
            # Store connection
            self._connections[connection_id] = connection_info
            
            # Track user connections
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)
            
            logger.info(f"WebSocket connected: user={username}, connection_id={connection_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            # Clean up partial connection state
            if connection_id in self._connections:
                del self._connections[connection_id]
            if user_id in self._user_connections and connection_id in self._user_connections[user_id]:
                self._user_connections[user_id].discard(connection_id)
            raise
    
    async def disconnect(self, connection_id: str):
        """Remove WebSocket connection and clean up with proper state management"""
        if connection_id not in self._connections:
            logger.warning(f"Attempted to disconnect non-existent connection: {connection_id}")
            return
        
        connection = self._connections[connection_id]
        
        try:
            # Mark as disconnecting
            connection.connection_state = "closing"
            connection.is_alive = False
            
            # Close websocket if still open
            if connection.websocket and hasattr(connection.websocket, 'client_state'):
                try:
                    if connection.websocket.client_state.name == "CONNECTED":
                        await connection.websocket.close(code=1000, reason="Normal closure")
                except Exception as close_error:
                    logger.warning(f"Error closing websocket for {connection_id}: {close_error}")
            
            # Remove from all rooms and notify
            rooms_to_notify = list(connection.rooms)
            for room_id in rooms_to_notify:
                if room_id in self._room_connections:
                    self._room_connections[room_id].discard(connection_id)
                    if not self._room_connections[room_id]:
                        del self._room_connections[room_id]
                    
                    # Notify remaining room members
                    await self.broadcast_to_room(room_id, {
                        "type": MessageType.ROOM_PARTICIPANT_LEFT,
                        "user_id": connection.user_id,
                        "username": connection.username,
                        "room_id": room_id
                    })
            
            # Remove from user connections
            if connection.user_id in self._user_connections:
                self._user_connections[connection.user_id].discard(connection_id)
                if not self._user_connections[connection.user_id]:
                    del self._user_connections[connection.user_id]
            
            # Mark as closed
            connection.connection_state = "closed"
            
            logger.info(f"WebSocket disconnected: user={connection.username}, connection_id={connection_id}")
            
        except Exception as e:
            logger.error(f"Error during disconnect for {connection_id}: {e}")
        finally:
            # Always remove from connections dict
            if connection_id in self._connections:
                del self._connections[connection_id]
    
    async def _send_message(self, connection_id: str, message: dict):
        """Send message to specific connection with improved error handling"""
        if connection_id not in self._connections:
            logger.warning(f"Attempted to send message to non-existent connection: {connection_id}")
            return False
        
        connection = self._connections[connection_id]
        
        # Check if connection is alive
        if not connection.is_alive or connection.connection_state != "connected":
            logger.warning(f"Attempted to send message to inactive connection: {connection_id}")
            return False
        
        try:
            # Check websocket state before sending
            if hasattr(connection.websocket, 'client_state') and connection.websocket.client_state.name != "CONNECTED":
                logger.warning(f"WebSocket not connected for {connection_id}, state: {connection.websocket.client_state.name}")
                await self.disconnect(connection_id)
                return False
            
            await connection.websocket.send_json(message)
            return True
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected during send for {connection_id}")
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {e}")
            # Mark connection as problematic
            connection.is_alive = False
            await self.disconnect(connection_id)
            return False
    
    async def _send_error(self, connection_id: str, error_message: str):
        """Send error message to specific connection"""
        await self._send_message(connection_id, {
            "type": MessageType.ERROR,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def join_room(self, connection_id: str, room_id: str):
        """Add connection to a room"""
        if connection_id not in self._connections:
            return
        
        connection = self._connections[connection_id]
        connection.rooms.add(room_id)
        
        if room_id not in self._room_connections:
            self._room_connections[room_id] = set()
        self._room_connections[room_id].add(connection_id)
        
        # Notify room members
        await self.broadcast_to_room(room_id, {
            "type": MessageType.ROOM_UPDATE,
            "action": "user_joined",
            "user_id": connection.user_id,
            "username": connection.username,
            "room_id": room_id
        }, exclude_connection=connection_id)
        
        logger.info(f"User {connection.username} joined room {room_id}")
    
    async def leave_room(self, connection_id: str, room_id: str):
        """Remove connection from a room"""
        if connection_id not in self._connections:
            return
        
        connection = self._connections[connection_id]
        connection.rooms.discard(room_id)
        
        if room_id in self._room_connections:
            self._room_connections[room_id].discard(connection_id)
            if not self._room_connections[room_id]:
                del self._room_connections[room_id]
        
        # Notify room members
        await self.broadcast_to_room(room_id, {
            "type": MessageType.ROOM_UPDATE,
            "action": "user_left",
            "user_id": connection.user_id,
            "username": connection.username,
            "room_id": room_id
        })
        
        logger.info(f"User {connection.username} left room {room_id}")
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_connection: Optional[str] = None):
        """Broadcast message to all connections in a room"""
        if room_id not in self._room_connections:
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Create a list to avoid set modification during iteration
        connection_ids = list(self._room_connections[room_id])
        for conn_id in connection_ids:
            if conn_id != exclude_connection:
                await self._send_message(conn_id, message)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user"""
        if user_id not in self._user_connections:
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        for conn_id in list(self._user_connections[user_id]):
            await self._send_message(conn_id, message)
    
    async def send_notification(self, user_id: str, notification: dict):
        """Send notification to a user"""
        await self.send_to_user(user_id, {
            "type": MessageType.NOTIFICATION,
            **notification
        })
    
    async def broadcast_chat_message(self, room_id: str, sender_user_id: str, message_data: dict):
        """Broadcast chat message to room"""
        await self.broadcast_to_room(room_id, {
            "type": MessageType.CHAT_MESSAGE,
            "sender_user_id": sender_user_id,
            **message_data
        })
    
    async def notify_user_typing(self, room_id: str, user_id: str, username: str):
        """Notify room that user is typing"""
        await self.broadcast_to_room(room_id, {
            "type": MessageType.USER_TYPING,
            "user_id": user_id,
            "username": username,
            "room_id": room_id
        }, exclude_connection=None)
    
    async def notify_user_stopped_typing(self, room_id: str, user_id: str, username: str):
        """Notify room that user stopped typing"""
        await self.broadcast_to_room(room_id, {
            "type": MessageType.USER_STOPPED_TYPING,
            "user_id": user_id,
            "username": username,
            "room_id": room_id
        })
    
    def register_handler(self, message_type: MessageType, handler: callable):
        """Register a message handler for a specific message type"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def handle_message(self, connection_id: str, message: dict):
        """Handle incoming WebSocket message with improved error handling"""
        if connection_id not in self._connections:
            logger.warning(f"Received message from non-existent connection: {connection_id}")
            return
        
        connection = self._connections[connection_id]
        if not connection.is_alive:
            logger.warning(f"Received message from inactive connection: {connection_id}")
            return
        
        message_type = message.get("type")
        
        try:
            # Handle built-in message types
            if message_type == "pong":
                await self.handle_pong(connection_id)
            elif message_type == MessageType.JOIN_ROOM:
                room_id = message.get("room_id")
                if room_id:
                    await self.join_room(connection_id, room_id)
                else:
                    await self._send_error(connection_id, "Room ID required for join_room")
            elif message_type == MessageType.LEAVE_ROOM:
                room_id = message.get("room_id")
                if room_id:
                    await self.leave_room(connection_id, room_id)
                else:
                    await self._send_error(connection_id, "Room ID required for leave_room")
            elif message_type in self.message_handlers:
                # Call custom handler
                handler = self.message_handlers[message_type]
                await handler(connection_id, message)
            else:
                logger.warning(f"No handler registered for message type: {message_type}")
                await self._send_error(connection_id, f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling message type {message_type} from {connection_id}: {e}")
            await self._send_error(connection_id, "Error processing message")
    
    def get_online_users(self) -> List[dict]:
        """Get list of currently online users"""
        users = {}
        for conn in self._connections.values():
            if conn.user_id not in users:
                users[conn.user_id] = {
                    "user_id": conn.user_id,
                    "username": conn.username,
                    "connection_count": 0
                }
            users[conn.user_id]["connection_count"] += 1
        return list(users.values())
    
    def get_room_connections(self, room_id: str) -> List[str]:
        """Get list of connection IDs in a room"""
        return list(self._room_connections.get(room_id, []))
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if a user is online"""
        return user_id in self._user_connections and len(self._user_connections[user_id]) > 0
    
    def _start_heartbeat_task(self):
        """Start the heartbeat monitoring task"""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            logger.info("Heartbeat monitoring task started")
    
    async def _heartbeat_monitor(self):
        """Monitor connections and send heartbeat pings"""
        while not self._shutdown:
            try:
                current_time = datetime.utcnow()
                connections_to_remove = []
                
                for connection_id, connection in self._connections.items():
                    if not connection.is_alive:
                        connections_to_remove.append(connection_id)
                        continue
                    
                    # Check if connection has been inactive too long
                    if connection.last_ping:
                        time_since_ping = (current_time - connection.last_ping).total_seconds()
                        if time_since_ping > (self._heartbeat_interval + self._heartbeat_timeout):
                            logger.warning(f"Connection {connection_id} timed out, last ping {time_since_ping}s ago")
                            connections_to_remove.append(connection_id)
                            continue
                    
                    # Send ping
                    try:
                        success = await self._send_message(connection_id, {
                            "type": "ping",
                            "timestamp": current_time.isoformat()
                        })
                        if not success:
                            connections_to_remove.append(connection_id)
                    except Exception as e:
                        logger.error(f"Error sending ping to {connection_id}: {e}")
                        connections_to_remove.append(connection_id)
                
                # Clean up dead connections
                for connection_id in connections_to_remove:
                    await self.disconnect(connection_id)
                
                # Wait for next heartbeat cycle
                await asyncio.sleep(self._heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def handle_pong(self, connection_id: str):
        """Handle pong response from client"""
        if connection_id in self._connections:
            connection = self._connections[connection_id]
            connection.last_ping = datetime.utcnow()
            logger.debug(f"Received pong from {connection_id}")
    
    async def shutdown(self):
        """Gracefully shutdown the WebSocket manager"""
        logger.info("Shutting down WebSocket manager...")
        self._shutdown = True
        
        # Cancel background tasks
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all connections
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)
        
        logger.info("WebSocket manager shutdown complete")
    
    def _start_cleanup_task(self):
        """Start the connection cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_monitor())
            logger.info("Connection cleanup task started")
    
    async def _cleanup_monitor(self):
        """Monitor and cleanup stale connections"""
        while not self._shutdown:
            try:
                current_time = datetime.utcnow()
                connections_to_remove = []
                
                # Find stale connections (inactive for more than 1 hour)
                stale_threshold = 3600  # 1 hour in seconds
                
                for connection_id, connection in self._connections.items():
                    if not connection.is_alive:
                        connections_to_remove.append(connection_id)
                        continue
                    
                    # Check if connection has been inactive too long
                    time_since_connect = (current_time - connection.connected_at).total_seconds()
                    if connection.last_ping:
                        time_since_ping = (current_time - connection.last_ping).total_seconds()
                        if time_since_ping > stale_threshold:
                            logger.info(f"Cleaning up stale connection {connection_id}, inactive for {time_since_ping}s")
                            connections_to_remove.append(connection_id)
                    elif time_since_connect > stale_threshold:
                        logger.info(f"Cleaning up connection {connection_id} without pings, connected {time_since_connect}s ago")
                        connections_to_remove.append(connection_id)
                
                # Clean up stale connections
                for connection_id in connections_to_remove:
                    await self.disconnect(connection_id)
                
                if connections_to_remove:
                    logger.info(f"Cleaned up {len(connections_to_remove)} stale connections")
                
                # Wait for next cleanup cycle
                await asyncio.sleep(self._connection_cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in cleanup monitor: {e}")
                await asyncio.sleep(30)  # Brief pause before retrying
    
    async def _close_oldest_user_connection(self, user_id: str):
        """Close the oldest connection for a user to make room for a new one"""
        if user_id not in self._user_connections:
            return
        
        user_connection_ids = list(self._user_connections[user_id])
        if not user_connection_ids:
            return
        
        # Find the oldest connection
        oldest_connection_id = None
        oldest_time = None
        
        for conn_id in user_connection_ids:
            if conn_id in self._connections:
                connection = self._connections[conn_id]
                if oldest_time is None or connection.connected_at < oldest_time:
                    oldest_time = connection.connected_at
                    oldest_connection_id = conn_id
        
        if oldest_connection_id:
            logger.info(f"Closing oldest connection {oldest_connection_id} for user {user_id} to make room for new connection")
            await self.disconnect(oldest_connection_id)
    
    def get_connection_stats(self) -> dict:
        """Get current connection statistics"""
        total_connections = len(self._connections)
        active_connections = sum(1 for conn in self._connections.values() if conn.is_alive)
        total_users = len(self._user_connections)
        total_rooms = len(self._room_connections)
        
        # Per-user connection counts
        user_connection_counts = {
            user_id: len(conn_ids) 
            for user_id, conn_ids in self._user_connections.items()
        }
        
        return {
            "total_connections": total_connections,
            "active_connections": active_connections,
            "total_users": total_users,
            "total_rooms": total_rooms,
            "max_connections_per_user": self._max_connections_per_user,
            "max_total_connections": self._max_total_connections,
            "user_connection_counts": user_connection_counts,
            "capacity_usage": f"{(total_connections / self._max_total_connections * 100):.1f}%"
        }


# Create a singleton instance
websocket_manager = WebSocketManager()

# Cleanup function for application shutdown
async def cleanup_websocket_manager():
    """Cleanup function to be called on application shutdown"""
    await websocket_manager.shutdown()