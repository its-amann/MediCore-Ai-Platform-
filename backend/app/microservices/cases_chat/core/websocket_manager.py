"""
WebSocket connection management for real-time chat functionality
"""
from typing import Dict, Set, Optional, List, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
import uuid
from enum import Enum
from datetime import datetime
import asyncio
import logging
from ..core.exceptions import WebSocketError

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    USER_MESSAGE = "user_message"
    DOCTOR_RESPONSE = "doctor_response"
    SYSTEM_NOTIFICATION = "system_notification"
    TYPING_INDICATOR = "typing_indicator"
    ERROR_MESSAGE = "error_message"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_CLOSED = "connection_closed"
    HEARTBEAT = "heartbeat"
    MEDIA_UPLOAD = "media_upload"
    CASE_UPDATE = "case_update"


class ConnectionState(Enum):
    """WebSocket connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class WebSocketConnection:
    """Represents a single WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, case_id: str, user_id: str):
        self.id = str(uuid.uuid4())
        self.websocket = websocket
        self.case_id = case_id
        self.user_id = user_id
        self.state = ConnectionState.CONNECTING
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary"""
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "connected_at": self.connected_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "metadata": self.metadata
        }


class WebSocketManager:
    """Manages WebSocket connections for real-time chat"""
    
    def __init__(self):
        # case_id -> Set[WebSocketConnection]
        self.case_connections: Dict[str, Set[WebSocketConnection]] = {}
        # connection_id -> WebSocketConnection
        self.connections: Dict[str, WebSocketConnection] = {}
        # user_id -> Set[connection_id]
        self.user_connections: Dict[str, Set[str]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
    
    async def connect(self, websocket: WebSocket, case_id: str, user_id: str) -> WebSocketConnection:
        """Connect websocket to a case room"""
        try:
            await websocket.accept()
            
            async with self._lock:
                # Create connection object
                connection = WebSocketConnection(websocket, case_id, user_id)
                connection.state = ConnectionState.CONNECTED
                
                # Add to case connections
                if case_id not in self.case_connections:
                    self.case_connections[case_id] = set()
                self.case_connections[case_id].add(connection)
                
                # Add to global connections
                self.connections[connection.id] = connection
                
                # Add to user connections
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection.id)
                
                logger.info(f"WebSocket connected: user={user_id}, case={case_id}, conn={connection.id}")
                
                # Send connection established message
                await self.send_personal_message(connection, {
                    "type": MessageType.CONNECTION_ESTABLISHED.value,
                    "connection_id": connection.id,
                    "case_id": case_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Notify others in the case
                await self.broadcast_to_case(case_id, {
                    "type": MessageType.SYSTEM_NOTIFICATION.value,
                    "content": f"User {user_id} joined the conversation",
                    "timestamp": datetime.utcnow().isoformat()
                }, exclude_connection=connection)
                
                return connection
                
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            raise WebSocketError(f"Failed to establish WebSocket connection: {str(e)}")
    
    async def disconnect(self, connection_id: str):
        """Disconnect websocket from case room"""
        async with self._lock:
            connection = self.connections.get(connection_id)
            if not connection:
                return
            
            connection.state = ConnectionState.DISCONNECTED
            
            # Remove from case connections
            if connection.case_id in self.case_connections:
                self.case_connections[connection.case_id].discard(connection)
                if not self.case_connections[connection.case_id]:
                    del self.case_connections[connection.case_id]
            
            # Remove from user connections
            if connection.user_id in self.user_connections:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]
            
            # Remove from global connections
            del self.connections[connection_id]
            
            logger.info(f"WebSocket disconnected: user={connection.user_id}, case={connection.case_id}, conn={connection_id}")
            
            # Notify others in the case
            await self.broadcast_to_case(connection.case_id, {
                "type": MessageType.SYSTEM_NOTIFICATION.value,
                "content": f"User {connection.user_id} left the conversation",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def send_personal_message(self, connection: WebSocketConnection, message: dict):
        """Send message to specific websocket connection"""
        try:
            if connection.state == ConnectionState.CONNECTED:
                await connection.websocket.send_text(json.dumps(message))
        except WebSocketDisconnect:
            await self.disconnect(connection.id)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(connection.id)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user"""
        connection_ids = self.user_connections.get(user_id, set()).copy()
        for conn_id in connection_ids:
            connection = self.connections.get(conn_id)
            if connection:
                await self.send_personal_message(connection, message)
    
    async def broadcast_to_case(self, case_id: str, message: dict, exclude_connection: Optional[WebSocketConnection] = None):
        """Send message to all connections in a case room"""
        if case_id not in self.case_connections:
            return
        
        connections = self.case_connections[case_id].copy()
        for connection in connections:
            if exclude_connection and connection.id == exclude_connection.id:
                continue
            await self.send_personal_message(connection, message)
    
    async def send_to_case(self, case_id: str, message: dict):
        """Send message to all connections in a case room (alias for broadcast_to_case)"""
        await self.broadcast_to_case(case_id, message)
    
    async def handle_incoming_message(self, connection_id: str, message: str):
        """Handle incoming WebSocket message"""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        try:
            data = json.loads(message)
            message_type = data.get("type", MessageType.USER_MESSAGE.value)
            
            # Update heartbeat for any message
            connection.last_heartbeat = datetime.utcnow()
            
            # Handle different message types
            if message_type == MessageType.HEARTBEAT.value:
                # Respond to heartbeat
                await self.send_personal_message(connection, {
                    "type": MessageType.HEARTBEAT.value,
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif message_type == MessageType.TYPING_INDICATOR.value:
                # Broadcast typing indicator to others
                await self.broadcast_to_case(connection.case_id, {
                    "type": MessageType.TYPING_INDICATOR.value,
                    "user_id": connection.user_id,
                    "is_typing": data.get("is_typing", False),
                    "timestamp": datetime.utcnow().isoformat()
                }, exclude_connection=connection)
            else:
                # For other message types, return the parsed data
                return data
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from connection {connection_id}")
            await self.send_personal_message(connection, {
                "type": MessageType.ERROR_MESSAGE.value,
                "error": "Invalid message format",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
            await self.send_personal_message(connection, {
                "type": MessageType.ERROR_MESSAGE.value,
                "error": "Failed to process message",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def get_case_connections(self, case_id: str) -> List[WebSocketConnection]:
        """Get all active connections for a case"""
        return list(self.case_connections.get(case_id, set()))
    
    def get_user_connections(self, user_id: str) -> List[WebSocketConnection]:
        """Get all active connections for a user"""
        connections = []
        for conn_id in self.user_connections.get(user_id, set()):
            conn = self.connections.get(conn_id)
            if conn:
                connections.append(conn)
        return connections
    
    def get_connection_by_id(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get connection by ID"""
        return self.connections.get(connection_id)
    
    def get_active_cases(self) -> List[str]:
        """Get list of cases with active connections"""
        return list(self.case_connections.keys())
    
    def get_connection_count(self, case_id: Optional[str] = None) -> int:
        """Get count of active connections"""
        if case_id:
            return len(self.case_connections.get(case_id, set()))
        return len(self.connections)
    
    async def cleanup_stale_connections(self, timeout_seconds: int = 60):
        """Clean up stale connections that haven't sent heartbeat"""
        current_time = datetime.utcnow()
        stale_connections = []
        
        async with self._lock:
            for conn_id, connection in self.connections.items():
                time_since_heartbeat = (current_time - connection.last_heartbeat).total_seconds()
                if time_since_heartbeat > timeout_seconds:
                    stale_connections.append(conn_id)
        
        # Disconnect stale connections
        for conn_id in stale_connections:
            logger.warning(f"Cleaning up stale connection: {conn_id}")
            await self.disconnect(conn_id)
    
    async def start_heartbeat_monitor(self, interval: int = 30, timeout: int = 60):
        """Start background task to monitor connection heartbeats"""
        async def monitor():
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self.cleanup_stale_connections(timeout)
                except Exception as e:
                    logger.error(f"Error in heartbeat monitor: {e}")
        
        task = asyncio.create_task(monitor())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def shutdown(self):
        """Shutdown manager and close all connections"""
        logger.info("Shutting down WebSocket manager...")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Close all connections
        connection_ids = list(self.connections.keys())
        for conn_id in connection_ids:
            await self.disconnect(conn_id)
        
        logger.info("WebSocket manager shutdown complete")


# Global manager instance
websocket_manager = WebSocketManager()