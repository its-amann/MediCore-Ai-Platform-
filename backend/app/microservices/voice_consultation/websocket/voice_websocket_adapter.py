"""
Voice Consultation WebSocket Adapter
Provides specialized WebSocket functionality for voice consultations using the unified WebSocket manager
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from app.core.websocket.manager import websocket_manager
from ..models.consultation_models import (
    VoiceSession, 
    ConsultationStatus,
    MessageType as ConsultationMessageType,
    ProviderType
)

logger = logging.getLogger(__name__)


class VoiceConsultationMessageType(str, Enum):
    """Voice consultation specific WebSocket message types"""
    SESSION_CREATED = "voice_session_created"
    SESSION_STATUS_CHANGED = "voice_session_status_changed"
    TRANSCRIPTION_STARTED = "transcription_started"
    TRANSCRIPTION_COMPLETED = "transcription_completed"
    AI_RESPONSE_STARTED = "ai_response_started"
    AI_RESPONSE_CHUNK = "ai_response_chunk"
    AI_RESPONSE_COMPLETED = "ai_response_completed"
    AUDIO_PROCESSING = "audio_processing"
    AUDIO_SYNTHESIS_STARTED = "audio_synthesis_started"
    AUDIO_SYNTHESIS_COMPLETED = "audio_synthesis_completed"
    PROVIDER_SWITCHED = "provider_switched"
    GEMINI_LIVE_CONNECTED = "gemini_live_connected"
    GEMINI_LIVE_DISCONNECTED = "gemini_live_disconnected"
    CONVERSATION_SUMMARY = "conversation_summary"
    SESSION_ENDED = "session_ended"
    ERROR_OCCURRED = "error_occurred"
    TYPING_INDICATOR = "typing_indicator"
    CONNECTION_STATUS = "connection_status"


@dataclass
class VoiceWebSocketSession:
    """Tracks WebSocket session state for voice consultations"""
    user_id: str
    consultation_session_id: str
    connection_ids: Set[str]
    case_id: Optional[str] = None
    doctor_type: Optional[str] = None
    ai_provider: Optional[ProviderType] = None
    language: str = "en"
    created_at: datetime = None
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()


class VoiceConsultationWebSocketAdapter:
    """Adapter for voice consultation WebSocket functionality using unified manager"""
    
    def __init__(self):
        # Track voice consultation WebSocket sessions
        self._voice_ws_sessions: Dict[str, VoiceWebSocketSession] = {}
        # Track user to session mapping
        self._user_sessions: Dict[str, Set[str]] = {}
        # Track consultation session to WebSocket session mapping
        self._consultation_to_ws_sessions: Dict[str, str] = {}
        
        # Register voice consultation message handlers
        try:
            self._register_handlers()
        except Exception as e:
            logger.warning(f"Failed to register handlers, continuing without them: {e}")
        
        # Start monitoring tasks
        try:
            self._start_monitoring_tasks()
        except Exception as e:
            logger.warning(f"Failed to start monitoring tasks: {e}")
        
        logger.info("Voice Consultation WebSocket Adapter initialized")
    
    def _register_handlers(self):
        """Register voice consultation specific message handlers"""
        try:
            # Register custom message handlers for voice consultation specific messages
            # Note: These are voice-specific message types, not part of the base MessageType enum
            websocket_manager.register_handler(
                "typing_indicator",  # Use string instead of enum value
                self._handle_typing_indicator
            )
            websocket_manager.register_handler(
                "connection_status",  # Use string instead of enum value
                self._handle_connection_status
            )
            websocket_manager.register_handler(
                "audio_chunk",
                self.handle_audio_chunk
            )
        except Exception as e:
            logger.warning(f"Could not register handlers (websocket manager may not be ready): {e}")
    
    async def create_voice_session(
        self, 
        user_id: str, 
        consultation_session_id: str,
        case_id: Optional[str] = None,
        doctor_type: Optional[str] = None,
        ai_provider: Optional[ProviderType] = None,
        language: str = "en"
    ) -> str:
        """Create a new voice consultation WebSocket session"""
        try:
            ws_session_id = f"voice_ws_{user_id}_{datetime.utcnow().timestamp()}"
            
            ws_session = VoiceWebSocketSession(
                user_id=user_id,
                consultation_session_id=consultation_session_id,
                connection_ids=set(),
                case_id=case_id,
                doctor_type=doctor_type,
                ai_provider=ai_provider,
                language=language
            )
            
            self._voice_ws_sessions[ws_session_id] = ws_session
            
            # Update user session mapping
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(ws_session_id)
            
            # Update consultation session mapping
            self._consultation_to_ws_sessions[consultation_session_id] = ws_session_id
            
            # Notify user about session creation
            await self.send_session_status(
                user_id,
                VoiceConsultationMessageType.SESSION_CREATED,
                {
                    "consultation_session_id": consultation_session_id,
                    "ws_session_id": ws_session_id,
                    "doctor_type": doctor_type,
                    "ai_provider": ai_provider.value if ai_provider else None,
                    "language": language,
                    "case_id": case_id
                }
            )
            
            logger.info(f"Created voice WebSocket session {ws_session_id} for consultation {consultation_session_id}")
            return ws_session_id
            
        except Exception as e:
            logger.error(f"Error creating voice WebSocket session: {e}")
            raise
    
    def get_ws_session_id_by_consultation(self, consultation_session_id: str) -> Optional[str]:
        """Get WebSocket session ID by consultation session ID"""
        return self._consultation_to_ws_sessions.get(consultation_session_id)
    
    async def connect_user_to_session(self, user_id: str, ws_session_id: str, connection_id: str):
        """Connect a user's WebSocket connection to a voice session"""
        try:
            if ws_session_id not in self._voice_ws_sessions:
                logger.warning(f"Voice WebSocket session {ws_session_id} not found")
                return False
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            
            # Check if authentication is disabled
            import os
            auth_required = os.getenv('WS_AUTH_REQUIRED', 'true').lower() == 'true'
            
            # Only check authorization if auth is enabled
            if auth_required and ws_session.user_id != user_id:
                logger.warning(f"User {user_id} not authorized for session {ws_session_id}")
                return False
            elif not auth_required:
                # Log for debugging when auth is disabled
                logger.info(f"Auth disabled - allowing user {user_id} to connect to session {ws_session_id} owned by {ws_session.user_id}")
            
            ws_session.connection_ids.add(connection_id)
            ws_session.last_activity = datetime.utcnow()
            
            # Join the consultation room
            room_id = f"voice_consultation_{ws_session.consultation_session_id}"
            await websocket_manager.join_room(connection_id, room_id)
            
            logger.info(f"Connected user {user_id} to voice session {ws_session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting user to voice session: {e}")
            return False
    
    async def disconnect_user_from_session(self, user_id: str, connection_id: str):
        """Disconnect a user's WebSocket connection from voice sessions"""
        try:
            # Find sessions for this user and connection
            sessions_to_update = []
            
            for ws_session_id, ws_session in self._voice_ws_sessions.items():
                if ws_session.user_id == user_id and connection_id in ws_session.connection_ids:
                    sessions_to_update.append((ws_session_id, ws_session))
            
            for ws_session_id, ws_session in sessions_to_update:
                ws_session.connection_ids.discard(connection_id)
                
                # Leave the consultation room
                room_id = f"voice_consultation_{ws_session.consultation_session_id}"
                await websocket_manager.leave_room(connection_id, room_id)
                
                logger.info(f"Disconnected user {user_id} from voice session {ws_session_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting user from voice session: {e}")
    
    async def send_session_status(
        self, 
        user_id: str, 
        status_type: VoiceConsultationMessageType,
        status_data: Dict[str, Any]
    ):
        """Send session status update to user"""
        try:
            message = {
                "type": status_type.value if hasattr(status_type, 'value') else str(status_type),
                "timestamp": datetime.utcnow().isoformat(),
                **status_data
            }
            
            # Debug logging to verify message content
            logger.info(f"Sending WebSocket message - Type: {message['type']}, User: {user_id}, Data: {status_data}")
            
            await websocket_manager.send_to_user(user_id, message)
            logger.debug(f"Sent voice session status to user {user_id}: {status_type}")
            
        except Exception as e:
            logger.error(f"Error sending session status: {e}")
    
    async def send_transcription_update(
        self, 
        consultation_session_id: str, 
        text: str,
        is_final: bool = False,
        confidence: float = 1.0,
        language: Optional[str] = None
    ):
        """Send transcription update for a consultation session"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                logger.warning(f"No WebSocket session found for consultation {consultation_session_id}")
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            ws_session.last_activity = datetime.utcnow()
            
            status_type = (VoiceConsultationMessageType.TRANSCRIPTION_COMPLETED 
                          if is_final 
                          else VoiceConsultationMessageType.TRANSCRIPTION_STARTED)
            
            await self.send_session_status(
                ws_session.user_id,
                status_type,
                {
                    "consultation_session_id": consultation_session_id,
                    "text": text,
                    "is_final": is_final,
                    "confidence": confidence,
                    "language": language or ws_session.language
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending transcription update: {e}")
    
    async def send_ai_response_update(
        self, 
        consultation_session_id: str,
        response_text: Optional[str] = None,
        response_chunk: Optional[str] = None,
        is_start: bool = False,
        is_complete: bool = False,
        provider_used: Optional[ProviderType] = None,
        audio_url: Optional[str] = None,
        audio_data: Optional[str] = None,  # Accept audio_data parameter
        **kwargs  # Accept any additional kwargs
    ):
        """Send AI response update for a consultation session"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                logger.warning(f"No WebSocket session found for consultation {consultation_session_id}")
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            ws_session.last_activity = datetime.utcnow()
            
            # Determine message type
            if is_start:
                status_type = VoiceConsultationMessageType.AI_RESPONSE_STARTED
            elif is_complete:
                status_type = VoiceConsultationMessageType.AI_RESPONSE_COMPLETED
            else:
                status_type = VoiceConsultationMessageType.AI_RESPONSE_CHUNK
            
            # Handle provider_used - it might be a string or ProviderType enum
            provider_value = None
            if provider_used:
                # Check if it's an enum with a value attribute
                if hasattr(provider_used, 'value') and not isinstance(provider_used, str):
                    provider_value = provider_used.value
                else:
                    # It's already a string or can be converted to string
                    provider_value = str(provider_used)
            
            status_data = {
                "consultation_session_id": consultation_session_id,
                "provider_used": provider_value
            }
            
            if response_text:
                status_data["response_text"] = response_text
            if response_chunk:
                status_data["response_chunk"] = response_chunk
            if audio_url:
                status_data["audio_url"] = audio_url
            if audio_data:
                status_data["audio_data"] = audio_data
            
            # Add any additional kwargs to status_data
            for key, value in kwargs.items():
                if key not in status_data and value is not None:
                    status_data[key] = value
            
            await self.send_session_status(
                ws_session.user_id,
                status_type,
                status_data
            )
            
        except Exception as e:
            logger.error(f"Error sending AI response update: {e}")
    
    async def send_audio_processing_update(
        self, 
        consultation_session_id: str,
        processing_type: str,  # "transcription", "synthesis", "processing"
        status: str,  # "started", "completed", "failed"
        details: Optional[Dict[str, Any]] = None
    ):
        """Send audio processing update"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                logger.warning(f"No WebSocket session found for consultation {consultation_session_id}")
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            ws_session.last_activity = datetime.utcnow()
            
            # Map processing types to message types
            message_type_map = {
                ("synthesis", "started"): VoiceConsultationMessageType.AUDIO_SYNTHESIS_STARTED,
                ("synthesis", "completed"): VoiceConsultationMessageType.AUDIO_SYNTHESIS_COMPLETED,
            }
            
            status_type = message_type_map.get(
                (processing_type, status), 
                VoiceConsultationMessageType.AUDIO_PROCESSING
            )
            
            status_data = {
                "consultation_session_id": consultation_session_id,
                "processing_type": processing_type,
                "status": status
            }
            
            if details:
                status_data.update(details)
            
            await self.send_session_status(
                ws_session.user_id,
                status_type,
                status_data
            )
            
        except Exception as e:
            logger.error(f"Error sending audio processing update: {e}")
    
    async def send_provider_switch_notification(
        self, 
        consultation_session_id: str,
        from_provider: Optional[ProviderType],
        to_provider: ProviderType,
        reason: Optional[str] = None
    ):
        """Send notification about AI provider switch"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            ws_session.ai_provider = to_provider
            ws_session.last_activity = datetime.utcnow()
            
            await self.send_session_status(
                ws_session.user_id,
                VoiceConsultationMessageType.PROVIDER_SWITCHED,
                {
                    "consultation_session_id": consultation_session_id,
                    "from_provider": from_provider.value if from_provider else None,
                    "to_provider": to_provider.value,
                    "reason": reason
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending provider switch notification: {e}")
    
    async def send_gemini_live_status(
        self, 
        consultation_session_id: str,
        is_connected: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """Send Gemini Live connection status"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            ws_session.last_activity = datetime.utcnow()
            
            status_type = (VoiceConsultationMessageType.GEMINI_LIVE_CONNECTED 
                          if is_connected 
                          else VoiceConsultationMessageType.GEMINI_LIVE_DISCONNECTED)
            
            status_data = {
                "consultation_session_id": consultation_session_id,
                "is_connected": is_connected
            }
            
            if details:
                status_data.update(details)
            
            await self.send_session_status(
                ws_session.user_id,
                status_type,
                status_data
            )
            
        except Exception as e:
            logger.error(f"Error sending Gemini Live status: {e}")
    
    async def send_session_summary(
        self, 
        consultation_session_id: str,
        summary: str,
        recommendations: List[str],
        follow_up_required: bool,
        session_stats: Optional[Dict[str, Any]] = None
    ):
        """Send session summary and recommendations"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            
            await self.send_session_status(
                ws_session.user_id,
                VoiceConsultationMessageType.CONVERSATION_SUMMARY,
                {
                    "consultation_session_id": consultation_session_id,
                    "summary": summary,
                    "recommendations": recommendations,
                    "follow_up_required": follow_up_required,
                    "session_stats": session_stats or {}
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending session summary: {e}")
    
    async def send_error_notification(
        self, 
        consultation_session_id: str,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """Send error notification for a consultation session"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                # Try to send to all user sessions as fallback
                for ws_session in self._voice_ws_sessions.values():
                    if ws_session.consultation_session_id == consultation_session_id:
                        await self._send_error_to_session(ws_session, error_message, error_context)
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            await self._send_error_to_session(ws_session, error_message, error_context)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
    
    async def _send_error_to_session(
        self, 
        ws_session: VoiceWebSocketSession, 
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """Send error to a specific WebSocket session"""
        try:
            status_data = {
                "consultation_session_id": ws_session.consultation_session_id,
                "error": error_message,
                "context": "voice_consultation"
            }
            
            if error_context:
                status_data.update(error_context)
            
            await self.send_session_status(
                ws_session.user_id,
                VoiceConsultationMessageType.ERROR_OCCURRED,
                status_data
            )
            
        except Exception as e:
            logger.error(f"Error sending error to session: {e}")
    
    async def end_voice_session(self, consultation_session_id: str):
        """End a voice consultation WebSocket session"""
        try:
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                logger.warning(f"No WebSocket session found for consultation {consultation_session_id}")
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            
            # Send session ended notification
            await self.send_session_status(
                ws_session.user_id,
                VoiceConsultationMessageType.SESSION_ENDED,
                {
                    "consultation_session_id": consultation_session_id,
                    "ws_session_id": ws_session_id,
                    "duration_seconds": int((datetime.utcnow() - ws_session.created_at).total_seconds())
                }
            )
            
            # Disconnect all connections from the room
            room_id = f"voice_consultation_{consultation_session_id}"
            for connection_id in list(ws_session.connection_ids):
                await websocket_manager.leave_room(connection_id, room_id)
            
            # Clean up session tracking
            self._voice_ws_sessions.pop(ws_session_id, None)
            self._consultation_to_ws_sessions.pop(consultation_session_id, None)
            
            if ws_session.user_id in self._user_sessions:
                self._user_sessions[ws_session.user_id].discard(ws_session_id)
                if not self._user_sessions[ws_session.user_id]:
                    del self._user_sessions[ws_session.user_id]
            
            logger.info(f"Ended voice WebSocket session {ws_session_id} for consultation {consultation_session_id}")
            
        except Exception as e:
            logger.error(f"Error ending voice session: {e}")
    
    async def _handle_typing_indicator(self, connection_id: str, message: Dict[str, Any]):
        """Handle typing indicator messages"""
        try:
            consultation_session_id = message.get("consultation_session_id")
            is_typing = message.get("is_typing", True)
            
            if not consultation_session_id:
                await websocket_manager._send_error(connection_id, "Consultation session ID required for typing indicator")
                return
            
            # Get connection info
            connection = websocket_manager._connections.get(connection_id)
            if not connection:
                return
            
            # Broadcast typing indicator to consultation room
            room_id = f"voice_consultation_{consultation_session_id}"
            await websocket_manager.broadcast_to_room(room_id, {
                "type": VoiceConsultationMessageType.TYPING_INDICATOR,
                "consultation_session_id": consultation_session_id,
                "user_id": connection.user_id,
                "username": connection.username,
                "is_typing": is_typing,
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_connection=connection_id)
            
        except Exception as e:
            logger.error(f"Error handling typing indicator: {e}")
    
    async def handle_audio_chunk(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming audio chunks from WebSocket"""
        try:
            consultation_session_id = message.get("consultation_session_id")
            audio_data_base64 = message.get("data")
            format = message.get("format", "pcm16")
            sample_rate = message.get("sample_rate", 16000)
            
            if not consultation_session_id or not audio_data_base64:
                await websocket_manager._send_error(
                    connection_id, 
                    "Consultation session ID and audio data required"
                )
                return
            
            # Find the WebSocket session
            ws_session_id = self._consultation_to_ws_sessions.get(consultation_session_id)
            if not ws_session_id or ws_session_id not in self._voice_ws_sessions:
                logger.warning(f"No WebSocket session found for consultation {consultation_session_id}")
                return
            
            ws_session = self._voice_ws_sessions[ws_session_id]
            ws_session.last_activity = datetime.utcnow()
            
            # Forward audio chunk to voice consultation service
            # This would typically be handled by injecting the service
            # For now, just acknowledge receipt
            await self.send_session_status(
                ws_session.user_id,
                VoiceConsultationMessageType.AUDIO_PROCESSING,
                {
                    "consultation_session_id": consultation_session_id,
                    "processing_type": "audio_chunk",
                    "status": "received",
                    "format": format,
                    "sample_rate": sample_rate
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling audio chunk: {e}")
    
    async def _handle_connection_status(self, connection_id: str, message: Dict[str, Any]):
        """Handle connection status messages"""
        try:
            consultation_session_id = message.get("consultation_session_id")
            status = message.get("status", "unknown")
            
            if not consultation_session_id:
                await websocket_manager._send_error(connection_id, "Consultation session ID required for connection status")
                return
            
            logger.info(f"Connection {connection_id} status for consultation {consultation_session_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error handling connection status: {e}")
    
    def _start_monitoring_tasks(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_voice_sessions())
    
    async def _monitor_voice_sessions(self):
        """Monitor active voice consultation WebSocket sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                current_time = datetime.utcnow()
                stale_sessions = []
                
                # Find stale sessions (inactive for more than 1 hour)
                for ws_session_id, ws_session in self._voice_ws_sessions.items():
                    if (current_time - ws_session.last_activity).total_seconds() > 3600:
                        stale_sessions.append(ws_session.consultation_session_id)
                
                # Clean up stale sessions
                for consultation_session_id in stale_sessions:
                    logger.info(f"Cleaning up stale voice WebSocket session: {consultation_session_id}")
                    await self.end_voice_session(consultation_session_id)
                
                if stale_sessions:
                    logger.info(f"Cleaned up {len(stale_sessions)} stale voice WebSocket sessions")
                
            except Exception as e:
                logger.error(f"Error in voice session monitoring: {e}")
                await asyncio.sleep(30)  # Brief pause before retrying
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active voice consultation WebSocket sessions"""
        try:
            total_sessions = len(self._voice_ws_sessions)
            active_users = len(self._user_sessions)
            
            # Calculate session details
            session_details = []
            for ws_session_id, ws_session in self._voice_ws_sessions.items():
                session_details.append({
                    "ws_session_id": ws_session_id,
                    "consultation_session_id": ws_session.consultation_session_id,
                    "user_id": ws_session.user_id,
                    "case_id": ws_session.case_id,
                    "doctor_type": ws_session.doctor_type,
                    "ai_provider": ws_session.ai_provider.value if ws_session.ai_provider else None,
                    "language": ws_session.language,
                    "connection_count": len(ws_session.connection_ids),
                    "created_at": ws_session.created_at.isoformat(),
                    "last_activity": ws_session.last_activity.isoformat()
                })
            
            return {
                "total_sessions": total_sessions,
                "active_users": active_users,
                "session_details": session_details
            }
            
        except Exception as e:
            logger.error(f"Error getting voice session stats: {e}")
            return {"error": str(e)}


# Create singleton instance
voice_consultation_websocket = VoiceConsultationWebSocketAdapter()


# Convenience functions for easy integration
async def create_voice_session(
    user_id: str, 
    consultation_session_id: str, 
    **kwargs
) -> str:
    """Convenience function to create voice consultation WebSocket session"""
    return await voice_consultation_websocket.create_voice_session(
        user_id, consultation_session_id, **kwargs
    )


async def send_transcription_update(consultation_session_id: str, text: str, message_type=None, metadata=None, **kwargs):
    """Convenience function to send transcription updates
    
    Args:
        consultation_session_id: The consultation session ID
        text: The transcription text
        message_type: MessageType enum value (determines is_final flag)
        metadata: Optional metadata dict with confidence, language, etc.
    """
    # Determine is_final based on message type
    from ..models.consultation_models import MessageType
    is_final = message_type == MessageType.TRANSCRIPTION_COMPLETED if message_type else False
    
    # Extract metadata fields
    confidence = metadata.get('confidence', 1.0) if metadata else 1.0
    language = metadata.get('language') if metadata else None
    
    await voice_consultation_websocket.send_transcription_update(
        consultation_session_id, 
        text,
        is_final=is_final,
        confidence=confidence,
        language=language,
        **kwargs
    )


async def send_ai_response_update(consultation_session_id: str, response_text: str = "", message_type=None, metadata=None, **kwargs):
    """Convenience function to send AI response updates
    
    Args:
        consultation_session_id: The consultation session ID
        response_text: The AI response text
        message_type: MessageType enum value (determines is_start/is_complete)
        metadata: Optional metadata dict with audio_data, provider_used, etc.
    """
    # Determine flags based on message type
    from ..models.consultation_models import MessageType
    is_start = message_type == MessageType.AI_RESPONSE_STARTED if message_type else False
    is_complete = message_type == MessageType.AI_RESPONSE_COMPLETED if message_type else False
    
    # Merge metadata into kwargs if provided
    if metadata:
        kwargs.update(metadata)
    
    await voice_consultation_websocket.send_ai_response_update(
        consultation_session_id,
        response_text=response_text if response_text else None,
        is_start=is_start,
        is_complete=is_complete,
        **kwargs
    )


async def send_audio_processing_update(consultation_session_id: str, processing_type: str, status: str, details=None, **kwargs):
    """Convenience function to send audio processing updates
    
    Args:
        consultation_session_id: The consultation session ID
        processing_type: Type of processing (e.g., "transcription", "synthesis", "processing")
        status: Status of the processing (e.g., "started", "completed", "failed")
        details: Optional dictionary with additional details
    """
    await voice_consultation_websocket.send_audio_processing_update(
        consultation_session_id, processing_type, status, details=details, **kwargs
    )


async def send_error_notification(consultation_session_id: str, error_message: str, **kwargs):
    """Convenience function to send error notifications"""
    await voice_consultation_websocket.send_error_notification(
        consultation_session_id, error_message, **kwargs
    )


async def end_voice_session(consultation_session_id: str):
    """Convenience function to end voice consultation session"""
    await voice_consultation_websocket.end_voice_session(consultation_session_id)


# Cleanup function for application shutdown
async def cleanup_voice_websocket():
    """Cleanup function to be called on application shutdown"""
    try:
        # End all active sessions
        consultation_session_ids = list(voice_consultation_websocket._consultation_to_ws_sessions.keys())
        for consultation_session_id in consultation_session_ids:
            await voice_consultation_websocket.end_voice_session(consultation_session_id)
        
        logger.info("Voice consultation WebSocket adapter cleanup complete")
        
    except Exception as e:
        logger.error(f"Error during voice WebSocket cleanup: {e}")