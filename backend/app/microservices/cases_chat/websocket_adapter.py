"""
Cases Chat WebSocket Adapter
Provides chat-specific WebSocket functionality using the unified WebSocket manager
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from app.microservices.cases_chat.models import DoctorType

logger = logging.getLogger(__name__)


class CasesChatMessageType(str, Enum):
    """Extended message types for cases/chat"""
    DOCTOR_RESPONSE_START = "doctor_response_start"
    DOCTOR_RESPONSE_CHUNK = "doctor_response_chunk" 
    DOCTOR_RESPONSE_END = "doctor_response_end"
    CASE_UPDATE = "case_update"
    CHAT_SESSION_CREATED = "chat_session_created"
    DOCTOR_SWITCHED = "doctor_switched"
    MCP_ANALYSIS_START = "mcp_analysis_start"
    MCP_ANALYSIS_COMPLETE = "mcp_analysis_complete"
    MCP_ANALYSIS_FAILED = "mcp_analysis_failed"
    REPORT_GENERATED = "report_generated"
    TYPING_INDICATOR = "typing_indicator"


class CasesChatWebSocketAdapter:
    """
    WebSocket adapter for cases/chat microservice
    Provides chat-specific functionality on top of the unified WebSocket manager
    """
    
    def __init__(self):
        # Import here to avoid circular imports
        from app.core.websocket import websocket_manager, MessageType
        self.ws_manager = websocket_manager
        self.MessageType = MessageType
        
        # Register custom message handlers
        self._register_handlers()
        
        logger.info("Cases Chat WebSocket Adapter initialized")
    
    def _register_handlers(self):
        """Register cases/chat specific message handlers"""
        self.ws_manager.register_handler(
            CasesChatMessageType.TYPING_INDICATOR.value,  # Use .value to get the string
            self._handle_typing_indicator
        )
    
    async def join_case_room(self, user_id: str, case_id: str) -> bool:
        """
        Join a user to a case room
        
        Args:
            user_id: User ID
            case_id: Case ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            room_id = f"case_{case_id}"
            
            # Get user's connections
            if user_id not in self.ws_manager._user_connections:
                logger.warning(f"User {user_id} not connected to WebSocket")
                return False
            
            # Join all user connections to the room
            success_count = 0
            for connection_id in self.ws_manager._user_connections[user_id]:
                await self.ws_manager.join_room(connection_id, room_id)
                success_count += 1
            
            logger.info(f"User {user_id} joined case room {case_id} with {success_count} connections")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error joining case room: {e}")
            return False
    
    async def leave_case_room(self, user_id: str, case_id: str) -> bool:
        """
        Remove a user from a case room
        
        Args:
            user_id: User ID
            case_id: Case ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            room_id = f"case_{case_id}"
            
            # Get user's connections
            if user_id not in self.ws_manager._user_connections:
                return True  # Already not connected
            
            # Leave room for all user connections
            for connection_id in list(self.ws_manager._user_connections[user_id]):
                await self.ws_manager.leave_room(connection_id, room_id)
            
            logger.info(f"User {user_id} left case room {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error leaving case room: {e}")
            return False
    
    async def broadcast_new_message(
        self, 
        case_id: str, 
        message_data: Dict[str, Any]
    ):
        """
        Broadcast new chat message to case room
        
        Args:
            case_id: Case ID
            message_data: Message data including user_message, doctor_response, etc.
        """
        try:
            room_id = f"case_{case_id}"
            
            await self.ws_manager.broadcast_to_room(room_id, {
                "type": self.MessageType.CHAT_MESSAGE,
                "case_id": case_id,
                **message_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.debug(f"Broadcasted new message to case room {case_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting new message: {e}")
    
    async def notify_doctor_response_streaming(
        self, 
        user_id: str, 
        case_id: str, 
        doctor_type: DoctorType,
        chunk: str = None,
        is_start: bool = False,
        is_end: bool = False,
        full_response: str = None
    ):
        """
        Send streaming doctor response notifications
        
        Args:
            user_id: User ID to notify
            case_id: Case ID
            doctor_type: Type of doctor responding
            chunk: Response chunk (for streaming)
            is_start: Whether this is the start of the response
            is_end: Whether this is the end of the response
            full_response: Complete response (when is_end=True)
        """
        try:
            message_data = {
                "case_id": case_id,
                "doctor_type": doctor_type.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if is_start:
                message_data["type"] = CasesChatMessageType.DOCTOR_RESPONSE_START
                message_data["message"] = f"Dr. {doctor_type.value.title()} is responding..."
            elif is_end:
                message_data["type"] = CasesChatMessageType.DOCTOR_RESPONSE_END
                message_data["full_response"] = full_response
                message_data["message"] = "Response complete"
            else:
                message_data["type"] = CasesChatMessageType.DOCTOR_RESPONSE_CHUNK
                message_data["chunk"] = chunk
            
            await self.ws_manager.send_to_user(user_id, message_data)
            
        except Exception as e:
            logger.error(f"Error sending doctor response notification: {e}")
    
    async def notify_case_update(
        self, 
        case_id: str, 
        update_data: Dict[str, Any],
        exclude_user_id: Optional[str] = None
    ):
        """
        Notify case room about case updates
        
        Args:
            case_id: Case ID
            update_data: Update information
            exclude_user_id: User ID to exclude from notification
        """
        try:
            room_id = f"case_{case_id}"
            
            message = {
                "type": CasesChatMessageType.CASE_UPDATE,
                "case_id": case_id,
                **update_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # If we need to exclude a specific user, we'll need to manually send to others
            if exclude_user_id:
                # Get all connections in the room
                connection_ids = self.ws_manager.get_room_connections(room_id)
                for conn_id in connection_ids:
                    if conn_id in self.ws_manager._connections:
                        conn = self.ws_manager._connections[conn_id]
                        if conn.user_id != exclude_user_id:
                            await self.ws_manager._send_message(conn_id, message)
            else:
                await self.ws_manager.broadcast_to_room(room_id, message)
            
            logger.debug(f"Notified case room {case_id} about update")
            
        except Exception as e:
            logger.error(f"Error notifying case update: {e}")
    
    async def notify_chat_session_created(
        self, 
        user_id: str, 
        case_id: str, 
        session_data: Dict[str, Any]
    ):
        """
        Notify user about new chat session creation
        
        Args:
            user_id: User ID
            case_id: Case ID
            session_data: Chat session data
        """
        try:
            await self.ws_manager.send_to_user(user_id, {
                "type": CasesChatMessageType.CHAT_SESSION_CREATED,
                "case_id": case_id,
                **session_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error notifying chat session creation: {e}")
    
    async def notify_doctor_switch(
        self, 
        case_id: str, 
        from_doctor: Optional[str], 
        to_doctor: DoctorType,
        user_id: str,
        handover_summary: Optional[str] = None
    ):
        """
        Notify about doctor switch in case
        
        Args:
            case_id: Case ID
            from_doctor: Previous doctor type
            to_doctor: New doctor type
            user_id: User ID
            handover_summary: Optional handover summary
        """
        try:
            message = {
                "type": CasesChatMessageType.DOCTOR_SWITCHED,
                "case_id": case_id,
                "from_doctor": from_doctor,
                "to_doctor": to_doctor.value,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if handover_summary:
                message["handover_summary"] = handover_summary
            
            # Notify the case room
            room_id = f"case_{case_id}"
            await self.ws_manager.broadcast_to_room(room_id, message)
            
        except Exception as e:
            logger.error(f"Error notifying doctor switch: {e}")
    
    async def notify_mcp_analysis(
        self, 
        user_id: str, 
        case_id: str, 
        doctor_type: DoctorType,
        status: str,  # "started", "completed", "failed"
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Send MCP analysis notifications
        
        Args:
            user_id: User ID
            case_id: Case ID
            doctor_type: Doctor type performing analysis
            status: Analysis status
            data: Additional data based on status
        """
        try:
            message_types = {
                "started": CasesChatMessageType.MCP_ANALYSIS_START,
                "completed": CasesChatMessageType.MCP_ANALYSIS_COMPLETE,
                "failed": CasesChatMessageType.MCP_ANALYSIS_FAILED
            }
            
            message = {
                "type": message_types.get(status, CasesChatMessageType.MCP_ANALYSIS_START),
                "case_id": case_id,
                "doctor_type": doctor_type.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if data:
                message.update(data)
            
            await self.ws_manager.send_to_user(user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending MCP analysis notification: {e}")
    
    async def notify_report_generated(
        self, 
        user_id: str, 
        case_id: str, 
        report_data: Dict[str, Any]
    ):
        """
        Notify user about generated case report
        
        Args:
            user_id: User ID
            case_id: Case ID
            report_data: Report data
        """
        try:
            await self.ws_manager.send_to_user(user_id, {
                "type": CasesChatMessageType.REPORT_GENERATED,
                "case_id": case_id,
                **report_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error notifying report generation: {e}")
    
    async def send_typing_indicator(
        self, 
        case_id: str, 
        user_id: str, 
        username: str, 
        is_typing: bool = True
    ):
        """
        Send typing indicator to case room
        
        Args:
            case_id: Case ID
            user_id: User ID who is typing
            username: Username who is typing
            is_typing: Whether user is typing or stopped typing
        """
        try:
            room_id = f"case_{case_id}"
            
            if is_typing:
                await self.ws_manager.notify_user_typing(room_id, user_id, username)
            else:
                await self.ws_manager.notify_user_stopped_typing(room_id, user_id, username)
                
        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
    
    async def _handle_typing_indicator(self, connection_id: str, message: Dict[str, Any]):
        """
        Handle typing indicator messages
        
        Args:
            connection_id: Connection ID
            message: WebSocket message
        """
        try:
            case_id = message.get("case_id")
            is_typing = message.get("is_typing", True)
            
            if not case_id:
                await self.ws_manager._send_error(connection_id, "Case ID required for typing indicator")
                return
            
            # Get connection info
            connection = self.ws_manager._connections.get(connection_id)
            if not connection:
                return
            
            # Send typing indicator
            await self.send_typing_indicator(
                case_id, 
                connection.user_id, 
                connection.username, 
                is_typing
            )
            
        except Exception as e:
            logger.error(f"Error handling typing indicator: {e}")
    
    def get_case_room_users(self, case_id: str) -> List[Dict[str, str]]:
        """
        Get list of users in a case room
        
        Args:
            case_id: Case ID
            
        Returns:
            List of user info dictionaries
        """
        try:
            room_id = f"case_{case_id}"
            connection_ids = self.ws_manager.get_room_connections(room_id)
            
            users = []
            seen_users = set()
            
            for conn_id in connection_ids:
                if conn_id in self.ws_manager._connections:
                    conn = self.ws_manager._connections[conn_id]
                    if conn.user_id not in seen_users:
                        users.append({
                            "user_id": conn.user_id,
                            "username": conn.username
                        })
                        seen_users.add(conn.user_id)
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting case room users: {e}")
            return []
    
    def is_user_in_case_room(self, user_id: str, case_id: str) -> bool:
        """
        Check if user is in a case room
        
        Args:
            user_id: User ID
            case_id: Case ID
            
        Returns:
            True if user is in room, False otherwise
        """
        try:
            room_id = f"case_{case_id}"
            
            if user_id not in self.ws_manager._user_connections:
                return False
            
            for connection_id in self.ws_manager._user_connections[user_id]:
                if connection_id in self.ws_manager._connections:
                    conn = self.ws_manager._connections[connection_id]
                    if room_id in conn.rooms:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking user in case room: {e}")
            return False


# Create singleton instance lazily to avoid circular imports
cases_chat_ws_adapter = None

def get_cases_chat_ws_adapter():
    """Get the cases chat WebSocket adapter instance"""
    global cases_chat_ws_adapter
    if cases_chat_ws_adapter is None:
        cases_chat_ws_adapter = CasesChatWebSocketAdapter()
    return cases_chat_ws_adapter