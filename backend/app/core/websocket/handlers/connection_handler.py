"""
Connection Handler

Handles WebSocket connection-related messages and events.
"""

from typing import Dict, Any, List
from datetime import datetime
import json

from .base_handler import MessageTypeHandler
import logging

logger = logging.getLogger(__name__)


class ConnectionHandler(MessageTypeHandler):
    """
    Handles WebSocket connection-related messages
    
    This handler processes connection lifecycle messages such as:
    - Connection establishment
    - Heartbeat/ping-pong
    - Connection status updates
    - Client identification
    """
    
    def __init__(self):
        super().__init__(
            name="connection_handler",
            message_types=[
                "ping", "pong", "heartbeat",
                "client_info", "connection_status",
                "identify", "reconnect"
            ]
        )
        
        # Connection tracking
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        self.heartbeat_count = 0
        
    async def handle(self, connection_id: str, message: Dict[str, Any], manager) -> bool:
        """Handle connection-related messages"""
        if not self.enabled:
            return False
        
        message_type = message.get("type", "")
        
        if not self.can_handle(message_type):
            return False
        
        try:
            if message_type == "ping":
                await self._handle_ping(connection_id, message, manager)
            elif message_type == "pong":
                await self._handle_pong(connection_id, message, manager)
            elif message_type == "heartbeat":
                await self._handle_heartbeat(connection_id, message, manager)
            elif message_type == "client_info":
                await self._handle_client_info(connection_id, message, manager)
            elif message_type == "connection_status":
                await self._handle_connection_status(connection_id, message, manager)
            elif message_type == "identify":
                await self._handle_identify(connection_id, message, manager)
            elif message_type == "reconnect":
                await self._handle_reconnect(connection_id, message, manager)
            else:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling {message_type} from {connection_id}: {e}")
            await self._send_error(connection_id, manager, f"Error processing {message_type}")
            return False
    
    async def _handle_ping(self, connection_id: str, message: Dict[str, Any], manager):
        """Handle ping message and respond with pong"""
        timestamp = message.get("timestamp", datetime.utcnow().isoformat())
        
        pong_message = {
            "type": "pong",
            "timestamp": timestamp,
            "server_time": datetime.utcnow().isoformat()
        }
        
        await self._send_message(connection_id, manager, pong_message)
        self.heartbeat_count += 1
        
        # Update connection info
        if connection_id in self.connection_info:
            self.connection_info[connection_id]["last_ping"] = datetime.utcnow()
        
        self.logger.debug(f"Responded to ping from {connection_id}")
    
    async def _handle_pong(self, connection_id: str, message: Dict[str, Any], manager):
        """Handle pong response from client"""
        if connection_id in self.connection_info:
            self.connection_info[connection_id]["last_pong"] = datetime.utcnow()
        
        # Calculate round-trip time if timestamp is available
        client_timestamp = message.get("timestamp")
        if client_timestamp:
            try:
                client_time = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))
                rtt = (datetime.utcnow() - client_time).total_seconds() * 1000  # ms
                
                if connection_id in self.connection_info:
                    self.connection_info[connection_id]["rtt_ms"] = rtt
                
                self.logger.debug(f"RTT for {connection_id}: {rtt:.2f}ms")
            except Exception as e:
                self.logger.warning(f"Could not calculate RTT for {connection_id}: {e}")
        
        self.logger.debug(f"Received pong from {connection_id}")
    
    async def _handle_heartbeat(self, connection_id: str, message: Dict[str, Any], manager):
        """Handle heartbeat message"""
        heartbeat_response = {
            "type": "heartbeat_ack",
            "timestamp": datetime.utcnow().isoformat(),
            "connection_id": connection_id
        }
        
        await self._send_message(connection_id, manager, heartbeat_response)
        
        # Update connection activity
        if connection_id in self.connection_info:
            self.connection_info[connection_id]["last_heartbeat"] = datetime.utcnow()
        
        self.logger.debug(f"Processed heartbeat from {connection_id}")
    
    async def _handle_client_info(self, connection_id: str, message: Dict[str, Any], manager):
        """Handle client information update"""
        client_info = message.get("data", {})
        
        if connection_id not in self.connection_info:
            self.connection_info[connection_id] = {}
        
        # Store client information
        self.connection_info[connection_id].update({
            "client_info": client_info,
            "last_info_update": datetime.utcnow()
        })
        
        # Send acknowledgment
        ack_message = {
            "type": "client_info_ack",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._send_message(connection_id, manager, ack_message)
        
        self.logger.info(f"Updated client info for {connection_id}: {client_info}")
    
    async def _handle_connection_status(self, connection_id: str, message: Dict[str, Any], manager):
        """Handle connection status request"""
        status_info = {
            "type": "connection_status_response",
            "data": {
                "connection_id": connection_id,
                "status": "connected",
                "connected_at": self.connection_info.get(connection_id, {}).get("connected_at"),
                "last_activity": self.connection_info.get(connection_id, {}).get("last_activity"),
                "server_time": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_message(connection_id, manager, status_info)
        self.logger.debug(f"Sent connection status to {connection_id}")
    
    async def _handle_identify(self, connection_id: str, message: Dict[str, Any], manager):
        """Handle client identification"""
        identification = message.get("data", {})
        
        if connection_id not in self.connection_info:
            self.connection_info[connection_id] = {}
        
        self.connection_info[connection_id].update({
            "identification": identification,
            "identified_at": datetime.utcnow()
        })
        
        # Send identification acknowledgment
        ack_message = {
            "type": "identify_ack",
            "data": {
                "connection_id": connection_id,
                "identified": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_message(connection_id, manager, ack_message)
        
        self.logger.info(f"Client identified for {connection_id}: {identification}")
    
    async def _handle_reconnect(self, connection_id: str, message: Dict[str, Any], manager):
        """Handle reconnection request"""
        reconnect_data = message.get("data", {})
        previous_connection_id = reconnect_data.get("previous_connection_id")
        
        # Handle reconnection logic
        if previous_connection_id and previous_connection_id in self.connection_info:
            # Transfer some state from previous connection
            previous_info = self.connection_info[previous_connection_id]
            
            if connection_id not in self.connection_info:
                self.connection_info[connection_id] = {}
            
            self.connection_info[connection_id].update({
                "reconnected_from": previous_connection_id,
                "reconnected_at": datetime.utcnow(),
                "previous_client_info": previous_info.get("client_info"),
                "previous_identification": previous_info.get("identification")
            })
        
        # Send reconnection acknowledgment
        ack_message = {
            "type": "reconnect_ack",
            "data": {
                "connection_id": connection_id,
                "previous_connection_id": previous_connection_id,
                "reconnected": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_message(connection_id, manager, ack_message)
        
        self.logger.info(f"Reconnection handled for {connection_id} (from {previous_connection_id})")
    
    async def on_connect(self, connection_id: str, user_id: str, username: str, **kwargs):
        """Called when a new connection is established"""
        self.connection_info[connection_id] = {
            "user_id": user_id,
            "username": username,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            **kwargs
        }
        
        self.logger.info(f"Connection established: {connection_id} for user {username}")
    
    async def on_disconnect(self, connection_id: str, user_id: str, username: str):
        """Called when a connection is closed"""
        if connection_id in self.connection_info:
            del self.connection_info[connection_id]
        
        self.logger.info(f"Connection closed: {connection_id} for user {username}")
    
    async def _send_message(self, connection_id: str, manager, message: Dict[str, Any]):
        """Send message to a specific connection"""
        legacy_manager = manager.get_legacy_manager()
        await legacy_manager._send_message(connection_id, message)
    
    async def _send_error(self, connection_id: str, manager, error_message: str):
        """Send error message to a specific connection"""
        legacy_manager = manager.get_legacy_manager()
        await legacy_manager._send_error(connection_id, error_message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection handler statistics"""
        stats = super().get_stats()
        stats.update({
            "active_connections": len(self.connection_info),
            "heartbeat_count": self.heartbeat_count,
            "connections_with_client_info": sum(
                1 for info in self.connection_info.values() 
                if "client_info" in info
            ),
            "identified_connections": sum(
                1 for info in self.connection_info.values() 
                if "identification" in info
            ),
            "reconnected_connections": sum(
                1 for info in self.connection_info.values() 
                if "reconnected_from" in info
            )
        })
        return stats
    
    def get_connection_info(self, connection_id: str) -> Dict[str, Any]:
        """Get information for a specific connection"""
        return self.connection_info.get(connection_id, {})
    
    def get_all_connections_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information for all connections"""
        return self.connection_info.copy()