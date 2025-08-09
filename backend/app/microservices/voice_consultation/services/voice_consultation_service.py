"""
Voice Consultation Service
Main service orchestrating voice consultation with multimodal capabilities
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from ..agents.voice_agent import get_voice_agent
from .audio_processing import audio_processor
from ..agents.tools import analyze_image_with_camera

logger = logging.getLogger(__name__)


class VoiceConsultationService:
    """Main service for voice consultation orchestration"""
    
    def __init__(self):
        """Initialize voice consultation service"""
        self.active_sessions = {}
        self.chat_histories = {}
        
    async def start_consultation(self, session_id: str, user_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start a new voice consultation session
        
        Args:
            session_id: Unique session identifier
            user_info: Optional user information
            
        Returns:
            Session initialization response
        """
        try:
            # Initialize session
            self.active_sessions[session_id] = {
                "status": "active",
                "started_at": datetime.now().isoformat(),
                "user_info": user_info or {},
                "mode": "voice",  # voice, video, screen_share
                "chat_history": []
            }
            
            self.chat_histories[session_id] = []
            
            logger.info(f"Started consultation session: {session_id}")
            
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Voice consultation started. I'm ready to help you."
            }
            
        except Exception as e:
            logger.error(f"Error starting consultation: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def process_audio(self, session_id: str, audio_data: str, format: str = "webm") -> Dict[str, Any]:
        """
        Process audio input and generate response
        
        Args:
            session_id: Session identifier
            audio_data: Base64 encoded audio data
            format: Audio format
            
        Returns:
            Response with transcription and AI response
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found"
                }
            
            # Transcribe audio
            transcription = audio_processor.transcribe_audio_base64(audio_data, format)
            if not transcription:
                return {
                    "status": "error",
                    "message": "Could not transcribe audio"
                }
            
            logger.info(f"Transcribed: {transcription}")
            
            # Get context for agent
            context = {
                "chat_history": self.chat_histories.get(session_id, []),
                "mode": self.active_sessions[session_id].get("mode", "voice")
            }
            
            # Process with agent
            agent = get_voice_agent()
            response_text = agent.process_query(transcription, context)
            
            # Update chat history
            self.chat_histories[session_id].append((transcription, response_text))
            self.active_sessions[session_id]["chat_history"].append({
                "user": transcription,
                "assistant": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # Generate audio response
            audio_response = audio_processor.text_to_speech_base64(response_text)
            
            return {
                "status": "success",
                "transcription": transcription,
                "response_text": response_text,
                "audio_response": audio_response,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def process_image(self, session_id: str, image_data: str) -> Dict[str, Any]:
        """
        Process webcam image frame with vision analysis
        
        Args:
            session_id: Session identifier
            image_data: Base64 encoded image data
            
        Returns:
            Response with vision analysis
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found"
                }
            
            # Get last user message as context
            last_message = ""
            if self.chat_histories.get(session_id):
                last_chat = self.chat_histories[session_id][-1]
                last_message = last_chat[0] if last_chat else ""
            
            # Analyze image with context
            query = last_message if last_message else "What do you see in this image?"
            analysis = analyze_image_with_camera(query, image_data)
            
            # Log but don't add to chat history (to avoid spam)
            logger.info(f"Image analysis: {analysis[:100]}...")
            
            # Only send response if significant
            if "I can see" in analysis or "appears" in analysis.lower():
                # Generate audio response
                audio_response = audio_processor.text_to_speech_base64(analysis)
                
                return {
                    "status": "success",
                    "response_text": analysis,
                    "audio_response": audio_response,
                    "session_id": session_id
                }
            
            # Don't send response for routine frames
            return {
                "status": "success",
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def process_text(self, session_id: str, text: str) -> Dict[str, Any]:
        """
        Process text input and generate response
        
        Args:
            session_id: Session identifier
            text: User text input
            
        Returns:
            Response with AI response and audio
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found"
                }
            
            # Get context
            context = {
                "chat_history": self.chat_histories.get(session_id, []),
                "mode": self.active_sessions[session_id].get("mode", "voice")
            }
            
            # Process with agent
            agent = get_voice_agent()
            response_text = agent.process_query(text, context)
            
            # Update chat history
            self.chat_histories[session_id].append((text, response_text))
            self.active_sessions[session_id]["chat_history"].append({
                "user": text,
                "assistant": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # Generate audio response
            audio_response = audio_processor.text_to_speech_base64(response_text)
            
            return {
                "status": "success",
                "response_text": response_text,
                "audio_response": audio_response,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def set_mode(self, session_id: str, mode: str) -> Dict[str, Any]:
        """
        Set the consultation mode (voice, video, screen_share)
        
        Args:
            session_id: Session identifier
            mode: New mode
            
        Returns:
            Status response
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found"
                }
            
            valid_modes = ["voice", "video", "screen_share"]
            if mode not in valid_modes:
                return {
                    "status": "error",
                    "message": f"Invalid mode. Must be one of: {valid_modes}"
                }
            
            self.active_sessions[session_id]["mode"] = mode
            
            mode_messages = {
                "voice": "Switched to voice mode.",
                "video": "Video mode activated. I can now see through your camera when needed.",
                "screen_share": "Screen sharing mode activated. I can help with what's on your screen."
            }
            
            return {
                "status": "success",
                "mode": mode,
                "message": mode_messages.get(mode, "Mode updated.")
            }
            
        except Exception as e:
            logger.error(f"Error setting mode: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get information about a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information
        """
        if session_id not in self.active_sessions:
            return {
                "status": "error",
                "message": "Session not found"
            }
        
        session = self.active_sessions[session_id]
        return {
            "status": "success",
            "session_id": session_id,
            "mode": session.get("mode", "voice"),
            "started_at": session.get("started_at"),
            "chat_count": len(session.get("chat_history", []))
        }
    
    async def end_consultation(self, session_id: str) -> Dict[str, Any]:
        """
        End a consultation session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session end response with summary
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found"
                }
            
            session = self.active_sessions[session_id]
            chat_history = session.get("chat_history", [])
            
            # Create session summary
            summary = {
                "session_id": session_id,
                "started_at": session.get("started_at"),
                "ended_at": datetime.now().isoformat(),
                "total_exchanges": len(chat_history),
                "mode": session.get("mode", "voice")
            }
            
            # Clean up session
            del self.active_sessions[session_id]
            if session_id in self.chat_histories:
                del self.chat_histories[session_id]
            
            logger.info(f"Ended consultation session: {session_id}")
            
            return {
                "status": "success",
                "message": "Consultation ended successfully.",
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error ending consultation: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions.keys())
    
    async def switch_provider(self, provider: str, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Switch the AI provider for the voice agent
        
        Args:
            provider: Provider name
            model_id: Optional model ID
            
        Returns:
            Status response
        """
        try:
            agent = get_voice_agent()
            agent.switch_provider(provider, model_id)
            return {
                "status": "success",
                "message": f"Switched to {provider}/{model_id or 'default'}",
                "agent_info": agent.get_agent_info()
            }
        except Exception as e:
            logger.error(f"Error switching provider: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# Create singleton instance
voice_consultation_service = VoiceConsultationService()