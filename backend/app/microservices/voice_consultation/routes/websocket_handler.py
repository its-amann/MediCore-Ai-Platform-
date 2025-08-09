"""
WebSocket Handler for Voice Consultation
Handles real-time audio, video, and screen share communication
"""

import os
import json
import asyncio
import uuid
import base64
from datetime import datetime
from typing import Dict, Optional, Any, List
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.websockets import WebSocketState
import logging

from ..services.audio_processing import AudioProcessor
from ..agents.voice_agent import get_voice_agent
from ..services.voice_consultation_service import VoiceConsultationService
from app.core.services.database_manager import get_database_manager

logger = logging.getLogger(__name__)


class VoiceWebSocketManager:
    """Manages WebSocket connections for voice consultations"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.audio_processor = AudioProcessor()
        # Get shared database connection
        db_manager = get_database_manager()
        self.neo4j_driver = db_manager.connect_sync() if db_manager else None
        
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Accept WebSocket connection and initialize session"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Initialize session
        self.sessions[session_id] = {
            "user_id": user_id,
            "started_at": datetime.utcnow(),
            "chat_history": [],
            "transcripts": [],
            "mode": "audio",  # audio, video, screen_share
            "provider": "groq",
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "agent": None,
            "camera_enabled": False,
            "screen_share_enabled": False
        }
        
        # Initialize voice agent
        try:
            agent = get_voice_agent()
            self.sessions[session_id]["agent"] = agent
            logger.info(f"Voice agent initialized for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize voice agent: {e}")
            await self.send_error(websocket, "Failed to initialize AI agent")
            return
        
        # Store session in Neo4j
        await self._create_session_in_db(session_id, user_id)
        
        # Send connection success message
        await self.send_message(websocket, {
            "type": "connection_established",
            "session_id": session_id,
            "mode": "audio",
            "provider": "groq",
            "model": "meta-llama/llama-4-scout-17b-16e-instruct"
        })
    
    async def disconnect(self, session_id: str):
        """Handle WebSocket disconnection"""
        if session_id in self.active_connections:
            # Update session end time in database
            await self._end_session_in_db(session_id)
            
            # Clean up
            del self.active_connections[session_id]
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            logger.info(f"Session {session_id} disconnected")
    
    async def handle_message(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = message.get("type")
        
        if message_type == "audio_data":
            await self._handle_audio_data(websocket, session_id, message)
        elif message_type == "text_message":
            await self._handle_text_message(websocket, session_id, message)
        elif message_type == "switch_mode":
            await self._handle_mode_switch(websocket, session_id, message)
        elif message_type == "enable_camera":
            await self._handle_camera_toggle(websocket, session_id, message)
        elif message_type == "enable_screen_share":
            await self._handle_screen_share_toggle(websocket, session_id, message)
        elif message_type == "get_history":
            await self._send_chat_history(websocket, session_id)
        elif message_type == "ping":
            await self.send_message(websocket, {"type": "pong"})
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_audio_data(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Process incoming audio data with automatic silence detection"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                await self.send_error(websocket, "Session not found")
                return
            
            # Extract audio data
            audio_base64 = message.get("audio")
            if not audio_base64:
                await self.send_error(websocket, "No audio data provided")
                return
            
            # Initialize audio buffer if not exists
            if "audio_buffer" not in session:
                session["audio_buffer"] = []
                session["silence_count"] = 0
                session["has_speech"] = False
                session["last_speech_time"] = datetime.utcnow()
                session["partial_transcript"] = ""
            
            # Add to buffer
            session["audio_buffer"].append(audio_base64)
            
            # Transcribe current chunk
            transcript = self.audio_processor.transcribe_audio_base64(audio_base64, format="webm")
            
            # Check for speech or silence
            if transcript and len(transcript.strip()) > 0:
                # Real speech detected
                session["silence_count"] = 0
                session["has_speech"] = True
                session["last_speech_time"] = datetime.utcnow()
                session["partial_transcript"] += " " + transcript
                
                # Send partial transcript
                await self.send_message(websocket, {
                    "type": "partial_transcript",
                    "text": transcript,
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                # No speech in this chunk
                if session["has_speech"]:
                    # We had speech before, now counting silence
                    session["silence_count"] += 1
                    
                    # Process if we've had 2 seconds of silence after speech (8 chunks at 250ms each)
                    if session["silence_count"] >= 8 and session["partial_transcript"].strip():
                        await self._process_complete_utterance(websocket, session_id)
                        # Reset for next utterance
                        session["audio_buffer"] = []
                        session["silence_count"] = 0
                        session["has_speech"] = False
                        session["partial_transcript"] = ""
                # else: Still waiting for first speech, don't process
            
            # Also process if buffer gets too large with speech (>5 seconds)
            if len(session["audio_buffer"]) > 20 and session["has_speech"] and session["partial_transcript"].strip():
                await self._process_complete_utterance(websocket, session_id)
                session["audio_buffer"] = []
                session["silence_count"] = 0
                session["has_speech"] = False
                session["partial_transcript"] = ""
            
        except Exception as e:
            logger.error(f"Error handling audio data: {e}")
            await self.send_error(websocket, f"Error processing audio: {str(e)}")
    
    async def _process_complete_utterance(self, websocket: WebSocket, session_id: str):
        """Process a complete user utterance and generate AI response"""
        try:
            session = self.sessions.get(session_id)
            if not session or not session.get("partial_transcript"):
                return
            
            # Get the complete transcript
            transcript = session["partial_transcript"].strip()
            
            # If no real transcript detected, skip processing
            if not transcript or transcript == "":
                logger.debug("No speech detected in audio, skipping processing")
                return
            
            # Send final transcript
            await self.send_message(websocket, {
                "type": "transcription",
                "text": transcript,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Store transcript in session
            session["transcripts"].append({
                "speaker": "user",
                "text": transcript,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Process with AI agent
            agent = session.get("agent")
            if agent:
                # Get response from agent
                context = {
                    "chat_history": session["chat_history"][-10:],  # Last 10 exchanges
                    "mode": session["mode"],
                    "camera_enabled": session["camera_enabled"],
                    "screen_share_enabled": session["screen_share_enabled"]
                }
                
                response = agent.process_query(transcript, context)
                
                # Store in chat history
                session["chat_history"].append((transcript, response))
                
                # Send AI response
                await self.send_message(websocket, {
                    "type": "ai_response",
                    "text": response,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Generate TTS audio
                audio_url = await self._generate_tts(response)
                if audio_url:
                    await self.send_message(websocket, {
                        "type": "audio_response",
                        "audio_url": audio_url,
                        "text": response
                    })
                
                # Store AI response transcript
                session["transcripts"].append({
                    "speaker": "assistant",
                    "text": response,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Save to database
                await self._save_transcript_to_db(session_id, transcript, response)
            
        except Exception as e:
            logger.error(f"Error handling audio data: {e}")
            await self.send_error(websocket, f"Error processing audio: {str(e)}")
    
    async def _handle_text_message(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Handle text-based messages"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                await self.send_error(websocket, "Session not found")
                return
            
            text = message.get("text", "")
            if not text:
                return
            
            # Process with AI agent
            agent = session.get("agent")
            if agent:
                context = {
                    "chat_history": session["chat_history"][-10:],
                    "mode": session["mode"],
                    "camera_enabled": session["camera_enabled"],
                    "screen_share_enabled": session["screen_share_enabled"]
                }
                
                response = agent.process_query(text, context)
                
                # Store in chat history
                session["chat_history"].append((text, response))
                
                # Send response
                await self.send_message(websocket, {
                    "type": "ai_response",
                    "text": response,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Save to database
                await self._save_transcript_to_db(session_id, text, response)
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await self.send_error(websocket, f"Error processing message: {str(e)}")
    
    async def _handle_mode_switch(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Handle switching between audio, video, and screen share modes"""
        new_mode = message.get("mode", "audio")
        
        if new_mode not in ["audio", "video", "screen_share"]:
            await self.send_error(websocket, f"Invalid mode: {new_mode}")
            return
        
        session = self.sessions.get(session_id)
        if session:
            session["mode"] = new_mode
            
            # Update UI based on mode
            await self.send_message(websocket, {
                "type": "mode_switched",
                "mode": new_mode,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Session {session_id} switched to {new_mode} mode")
    
    async def _handle_camera_toggle(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Toggle camera on/off"""
        enabled = message.get("enabled", False)
        
        session = self.sessions.get(session_id)
        if session:
            session["camera_enabled"] = enabled
            
            await self.send_message(websocket, {
                "type": "camera_status",
                "enabled": enabled,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if enabled:
                # Notify agent that camera is available
                agent = session.get("agent")
                if agent:
                    await self.send_message(websocket, {
                        "type": "system_message",
                        "text": "Camera is now enabled. The AI can analyze visual information when needed."
                    })
    
    async def _handle_screen_share_toggle(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Toggle screen sharing on/off"""
        enabled = message.get("enabled", False)
        
        session = self.sessions.get(session_id)
        if session:
            session["screen_share_enabled"] = enabled
            
            await self.send_message(websocket, {
                "type": "screen_share_status",
                "enabled": enabled,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if enabled:
                # Notify agent that screen share is available
                agent = session.get("agent")
                if agent:
                    await self.send_message(websocket, {
                        "type": "system_message",
                        "text": "Screen sharing is now enabled. The AI can analyze your screen when needed."
                    })
    
    async def _send_chat_history(self, websocket: WebSocket, session_id: str):
        """Send chat history to client"""
        session = self.sessions.get(session_id)
        if session:
            history = []
            for user_msg, ai_msg in session["chat_history"]:
                history.append({"role": "user", "content": user_msg})
                history.append({"role": "assistant", "content": ai_msg})
            
            await self.send_message(websocket, {
                "type": "chat_history",
                "history": history,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """Transcribe audio using Whisper via Groq"""
        try:
            # Save audio to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            
            # Transcribe using Groq Whisper
            transcript = self.audio_processor.transcribe_audio_with_groq(tmp_file_path)
            
            # Clean up
            os.unlink(tmp_file_path)
            
            return transcript
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    async def _generate_tts(self, text: str) -> Optional[str]:
        """Generate TTS audio using gTTS"""
        try:
            audio_base64 = self.audio_processor.text_to_speech_base64(text)
            if audio_base64:
                # Return as data URL
                return f"data:audio/mp3;base64,{audio_base64}"
            return None
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None
    
    async def _create_session_in_db(self, session_id: str, user_id: str):
        """Create or update voice consultation session in Neo4j"""
        try:
            if not self.neo4j_driver:
                logger.warning("No Neo4j driver available, skipping database operation")
                return
                
            with self.neo4j_driver.session() as db_session:
                # First check if session already exists
                result = db_session.run("""
                    MATCH (v:VoiceConsultation {session_id: $session_id})
                    RETURN v
                """, session_id=session_id)
                
                existing_session = result.single()
                
                if existing_session:
                    # Update existing session
                    db_session.run("""
                        MATCH (v:VoiceConsultation {session_id: $session_id})
                        SET v.status = 'active',
                            v.updated_at = datetime(),
                            v.reconnected_at = datetime()
                    """, session_id=session_id)
                    logger.info(f"Updated existing session {session_id} in database")
                else:
                    # Create new session
                    db_session.run("""
                        MATCH (u:User {user_id: $user_id})
                        MERGE (v:VoiceConsultation {session_id: $session_id})
                        ON CREATE SET 
                            v.consultation_type = 'voice',
                            v.status = 'active',
                            v.mode = 'audio',
                            v.provider = 'groq',
                            v.model = 'meta-llama/llama-4-scout-17b-16e-instruct',
                            v.created_at = datetime(),
                            v.updated_at = datetime()
                        ON MATCH SET
                            v.status = 'active',
                            v.updated_at = datetime()
                        MERGE (u)-[:HAS_VOICE_CONSULTATION {
                            started_at: datetime(),
                            role: 'patient'
                        }]->(v)
                    """, user_id=user_id, session_id=session_id)
                    logger.info(f"Created session {session_id} in database")
        except Exception as e:
            logger.error(f"Failed to create/update session in database: {e}")
    
    async def _end_session_in_db(self, session_id: str):
        """Mark session as ended in database"""
        try:
            if not self.neo4j_driver:
                logger.warning("No Neo4j driver available, skipping database operation")
                return
                
            session = self.sessions.get(session_id)
            duration = 0
            if session:
                duration = (datetime.utcnow() - session["started_at"]).total_seconds()
            
            with self.neo4j_driver.session() as db_session:
                db_session.run("""
                    MATCH (v:VoiceConsultation {session_id: $session_id})
                    SET v.status = 'completed',
                        v.ended_at = datetime(),
                        v.duration = $duration,
                        v.updated_at = datetime()
                """, session_id=session_id, duration=duration)
                
                logger.info(f"Ended session {session_id} in database")
        except Exception as e:
            logger.error(f"Failed to end session in database: {e}")
    
    async def _save_transcript_to_db(self, session_id: str, user_text: str, ai_response: str):
        """Save transcript to database"""
        try:
            if not self.neo4j_driver:
                logger.warning("No Neo4j driver available, skipping database operation")
                return
                
            with self.neo4j_driver.session() as db_session:
                # Save user transcript
                db_session.run("""
                    MATCH (v:VoiceConsultation {session_id: $session_id})
                    CREATE (t:Transcript {
                        transcript_id: $transcript_id,
                        speaker: 'user',
                        content: $content,
                        timestamp: datetime()
                    })
                    CREATE (v)-[:HAS_TRANSCRIPT {
                        order: timestamp(),
                        timestamp: datetime()
                    }]->(t)
                """, session_id=session_id, 
                    transcript_id=f"transcript_{uuid.uuid4()}",
                    content=user_text)
                
                # Save AI response transcript
                db_session.run("""
                    MATCH (v:VoiceConsultation {session_id: $session_id})
                    CREATE (t:Transcript {
                        transcript_id: $transcript_id,
                        speaker: 'assistant',
                        content: $content,
                        timestamp: datetime()
                    })
                    CREATE (v)-[:HAS_TRANSCRIPT {
                        order: timestamp(),
                        timestamp: datetime()
                    }]->(t)
                """, session_id=session_id,
                    transcript_id=f"transcript_{uuid.uuid4()}",
                    content=ai_response)
                    
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
    
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_error(self, websocket: WebSocket, error: str):
        """Send error message to client"""
        await self.send_message(websocket, {
            "type": "error",
            "message": error,
            "timestamp": datetime.utcnow().isoformat()
        })


# Create singleton instance
websocket_manager = VoiceWebSocketManager()


async def voice_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: Optional[str] = None
):
    """WebSocket endpoint for voice consultation"""
    # User ID is required in production
    if not user_id:
        logger.error("User ID is required for voice consultation")
        await websocket.close(code=1008, reason="User ID required")
        return
    
    try:
        # Connect WebSocket
        await websocket_manager.connect(websocket, session_id, user_id)
        
        # Handle messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()
                
                # Handle message
                await websocket_manager.handle_message(websocket, session_id, data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except json.JSONDecodeError:
                await websocket_manager.send_error(websocket, "Invalid JSON message")
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                await websocket_manager.send_error(websocket, str(e))
                
    finally:
        # Disconnect and cleanup
        await websocket_manager.disconnect(session_id)