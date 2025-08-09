"""
WebSocket Handler for Voice Consultation
Real-time bidirectional communication for voice/video consultation
"""

from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
import asyncio
from typing import Dict, Any
from ..services.voice_consultation_service import voice_consultation_service

logger = logging.getLogger(__name__)


class VoiceWebSocketHandler:
    """Handles WebSocket connections for voice consultation"""
    
    def __init__(self):
        """Initialize WebSocket handler"""
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept WebSocket connection
        
        Args:
            websocket: WebSocket connection
            session_id: Unique session identifier
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Initialize consultation session
        result = await voice_consultation_service.start_consultation(session_id)
        await self.send_message(session_id, {
            "type": "session_started",
            "data": result
        })
        
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """
        Handle WebSocket disconnection
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """
        Send message to client
        
        Args:
            session_id: Session identifier
            message: Message to send
        """
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
    
    async def handle_message(self, session_id: str, data: Dict[str, Any]):
        """
        Handle incoming WebSocket message
        
        Args:
            session_id: Session identifier
            data: Message data
        """
        try:
            message_type = data.get("type")
            
            if message_type == "audio":
                # Process audio input or image frame
                audio_data = data.get("audio")
                format = data.get("format", "webm")
                
                if format == "image":
                    # Process webcam image frame
                    await self.send_message(session_id, {
                        "type": "processing",
                        "message": "Analyzing image..."
                    })
                    
                    # Process image frame with vision analysis
                    result = await voice_consultation_service.process_image(
                        session_id, audio_data
                    )
                else:
                    # Process audio input
                    await self.send_message(session_id, {
                        "type": "processing",
                        "message": "Processing your audio..."
                    })
                    
                    # Process audio
                    result = await voice_consultation_service.process_audio(
                        session_id, audio_data, format
                    )
                
                # Send response
                await self.send_message(session_id, {
                    "type": "response",
                    "data": result
                })
            
            elif message_type == "text":
                # Process text input
                text = data.get("text")
                
                # Send processing status
                await self.send_message(session_id, {
                    "type": "processing",
                    "message": "Thinking..."
                })
                
                # Process text
                result = await voice_consultation_service.process_text(session_id, text)
                
                # Send response
                await self.send_message(session_id, {
                    "type": "response",
                    "data": result
                })
            
            elif message_type == "set_mode":
                # Change consultation mode
                mode = data.get("mode")
                result = await voice_consultation_service.set_mode(session_id, mode)
                
                await self.send_message(session_id, {
                    "type": "mode_changed",
                    "data": result
                })
            
            elif message_type == "get_info":
                # Get session information
                result = await voice_consultation_service.get_session_info(session_id)
                
                await self.send_message(session_id, {
                    "type": "session_info",
                    "data": result
                })
            
            elif message_type == "end_session":
                # End consultation
                result = await voice_consultation_service.end_consultation(session_id)
                
                await self.send_message(session_id, {
                    "type": "session_ended",
                    "data": result
                })
                
                # Close WebSocket
                self.disconnect(session_id)
            
            elif message_type == "ping":
                # Respond to ping
                await self.send_message(session_id, {
                    "type": "pong",
                    "timestamp": data.get("timestamp")
                })
            
            else:
                # Unknown message type
                await self.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_message(session_id, {
                "type": "error",
                "message": str(e)
            })
    
    async def handle_websocket(self, websocket: WebSocket, session_id: str):
        """
        Main WebSocket handler
        
        Args:
            websocket: WebSocket connection
            session_id: Session identifier
        """
        try:
            # Connect
            await self.connect(websocket, session_id)
            
            # Handle messages
            while True:
                try:
                    # Receive message
                    data = await websocket.receive_json()
                    
                    # Handle message in background task
                    asyncio.create_task(self.handle_message(session_id, data))
                    
                except WebSocketDisconnect:
                    # Clean disconnection
                    break
                except json.JSONDecodeError as e:
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": f"Invalid JSON: {e}"
                    })
                except Exception as e:
                    logger.error(f"Error in WebSocket loop: {e}")
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": str(e)
                    })
                    
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            # Cleanup
            self.disconnect(session_id)
            await voice_consultation_service.end_consultation(session_id)


# Create singleton instance
voice_websocket_handler = VoiceWebSocketHandler()