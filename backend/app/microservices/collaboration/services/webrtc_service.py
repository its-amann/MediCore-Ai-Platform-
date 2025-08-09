"""
WebRTC Service for video/audio/screen sharing in collaboration rooms
Manages signaling, peer connections, and media streams
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid

from ..models import WebRTCSignal, VideoSession
from ..models.extended_models import ScreenShareSession, ScreenShareStatus

logger = logging.getLogger(__name__)


class WebRTCService:
    """Service for managing WebRTC connections and signaling"""
    
    def __init__(self, screen_share_service=None):
        # Active sessions by room_id
        self._active_sessions: Dict[str, VideoSession] = {}
        # Peer connections by room_id -> user_id -> connection_data
        self._peer_connections: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # ICE candidate queues for peers that haven't connected yet
        self._ice_candidate_queue: Dict[str, List[Dict[str, Any]]] = {}
        # Media stream states
        self._media_states: Dict[str, Dict[str, Dict[str, bool]]] = {}
        # Screen share service integration
        self.screen_share_service = screen_share_service
        # Track screen share streams separately
        self._screen_share_streams: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
    async def start_video_session(
        self,
        room_id: str,
        initiator_id: str,
        session_type: str = "video"
    ) -> VideoSession:
        """Start a new video/audio session in a room"""
        session_id = str(uuid.uuid4())
        
        session = VideoSession(
            room_id=room_id,
            session_id=session_id,
            participants=[initiator_id],
            is_recording=False,
            started_at=datetime.utcnow()
        )
        
        self._active_sessions[room_id] = session
        self._peer_connections[room_id] = {}
        self._media_states[room_id] = {
            initiator_id: {
                "video": session_type == "video",
                "audio": True,
                "screen": False
            }
        }
        
        logger.info(f"Started {session_type} session {session_id} in room {room_id}")
        return session
    
    async def join_video_session(
        self,
        room_id: str,
        user_id: str,
        offer_sdp: Optional[str] = None
    ) -> bool:
        """Join an existing video session"""
        session = self._active_sessions.get(room_id)
        if not session:
            logger.error(f"No active session in room {room_id}")
            return False
        
        if user_id not in session.participants:
            session.participants.append(user_id)
        
        # Initialize peer connection data
        if room_id not in self._peer_connections:
            self._peer_connections[room_id] = {}
        
        self._peer_connections[room_id][user_id] = {
            "connected": False,
            "offer_sdp": offer_sdp,
            "answer_sdp": None,
            "ice_candidates": []
        }
        
        # Initialize media state
        if room_id not in self._media_states:
            self._media_states[room_id] = {}
        
        self._media_states[room_id][user_id] = {
            "video": False,
            "audio": False,
            "screen": False
        }
        
        logger.info(f"User {user_id} joined video session in room {room_id}")
        return True
    
    async def leave_video_session(
        self,
        room_id: str,
        user_id: str
    ) -> bool:
        """Leave a video session"""
        session = self._active_sessions.get(room_id)
        if not session:
            return False
        
        # Remove from participants
        if user_id in session.participants:
            session.participants.remove(user_id)
        
        # Clean up peer connections
        if room_id in self._peer_connections:
            self._peer_connections[room_id].pop(user_id, None)
        
        # Clean up media states
        if room_id in self._media_states:
            self._media_states[room_id].pop(user_id, None)
        
        # End session if no participants left
        if not session.participants:
            await self.end_video_session(room_id)
        
        logger.info(f"User {user_id} left video session in room {room_id}")
        return True
    
    async def end_video_session(
        self,
        room_id: str
    ) -> bool:
        """End a video session"""
        session = self._active_sessions.get(room_id)
        if not session:
            return False
        
        session.ended_at = datetime.utcnow()
        
        # Clean up all data
        self._active_sessions.pop(room_id, None)
        self._peer_connections.pop(room_id, None)
        self._media_states.pop(room_id, None)
        self._ice_candidate_queue.pop(room_id, None)
        
        logger.info(f"Ended video session in room {room_id}")
        return True
    
    async def handle_webrtc_signal(
        self,
        signal: WebRTCSignal
    ) -> Optional[WebRTCSignal]:
        """Handle WebRTC signaling messages"""
        room_id = signal.data.get("room_id")
        
        if not room_id:
            logger.error("WebRTC signal missing room_id")
            return None
        
        # Validate signal authenticity
        if not await self._validate_signal_authenticity(signal):
            logger.error(f"Invalid signal from {signal.from_user}")
            return None
        
        # Handle screen share specific signals
        if signal.type in ["screen-share-offer", "screen-share-answer", "screen-share-candidate"]:
            return await self._handle_screen_share_signal(signal)
        
        if signal.type == "offer":
            # Validate SDP
            sdp = signal.data.get("sdp")
            if not self._validate_sdp(sdp):
                logger.error(f"Invalid offer SDP from {signal.from_user}")
                return None
            
            # Store offer and mark connection as pending
            if room_id in self._peer_connections:
                if signal.to_user in self._peer_connections[room_id]:
                    self._peer_connections[room_id][signal.to_user]["offer_sdp"] = sdp
                    
        elif signal.type == "answer":
            # Validate SDP
            sdp = signal.data.get("sdp")
            if not self._validate_sdp(sdp):
                logger.error(f"Invalid answer SDP from {signal.from_user}")
                return None
            
            # Store answer and mark connection as established
            if room_id in self._peer_connections:
                if signal.from_user in self._peer_connections[room_id]:
                    self._peer_connections[room_id][signal.from_user]["answer_sdp"] = sdp
                    self._peer_connections[room_id][signal.from_user]["connected"] = True
                    
                # Also update the connection state for the recipient
                if signal.to_user in self._peer_connections[room_id]:
                    self._peer_connections[room_id][signal.to_user]["connected"] = True
                    
        elif signal.type == "ice-candidate":
            # Queue or forward ICE candidates
            await self._handle_ice_candidate(room_id, signal)
            
        elif signal.type == "media-state":
            # Update media state
            await self._update_media_state(room_id, signal.from_user, signal.data)
        
        return signal
    
    async def _handle_ice_candidate(
        self,
        room_id: str,
        signal: WebRTCSignal
    ) -> None:
        """Handle ICE candidate exchange"""
        candidate_data = {
            "from": signal.from_user,
            "to": signal.to_user,
            "candidate": signal.data.get("candidate")
        }
        
        # Store ICE candidate
        if room_id in self._peer_connections:
            if signal.from_user in self._peer_connections[room_id]:
                self._peer_connections[room_id][signal.from_user]["ice_candidates"].append(
                    candidate_data
                )
        else:
            # Queue for later if peer hasn't joined yet
            if room_id not in self._ice_candidate_queue:
                self._ice_candidate_queue[room_id] = []
            self._ice_candidate_queue[room_id].append(candidate_data)
    
    async def _update_media_state(
        self,
        room_id: str,
        user_id: str,
        state_data: Dict[str, Any]
    ) -> None:
        """Update media state for a user"""
        if room_id not in self._media_states:
            self._media_states[room_id] = {}
        
        if user_id not in self._media_states[room_id]:
            self._media_states[room_id][user_id] = {
                "video": False,
                "audio": False,
                "screen": False
            }
        
        # Update states
        if "video" in state_data:
            self._media_states[room_id][user_id]["video"] = state_data["video"]
        if "audio" in state_data:
            self._media_states[room_id][user_id]["audio"] = state_data["audio"]
        if "screen" in state_data:
            self._media_states[room_id][user_id]["screen"] = state_data["screen"]
    
    async def get_session_info(
        self,
        room_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get information about an active session"""
        session = self._active_sessions.get(room_id)
        if not session:
            return None
        
        # Get screen share info
        screen_shares = []
        if self.screen_share_service:
            active_shares = await self.screen_share_service.get_active_sessions(room_id)
            for share in active_shares:
                screen_shares.append({
                    "session_id": share.session_id,
                    "user_id": share.user_id,
                    "status": share.status,
                    "quality": share.quality,
                    "source_type": share.source_type,
                    "stream_id": share.stream_id,
                    "is_recording": share.is_recording,
                    "viewers": share.viewers
                })
        
        return {
            "session_id": session.session_id,
            "room_id": session.room_id,
            "participants": session.participants,
            "started_at": session.started_at.isoformat(),
            "is_recording": session.is_recording,
            "media_states": self._media_states.get(room_id, {}),
            "connection_states": {
                user_id: conn.get("connected", False)
                for user_id, conn in self._peer_connections.get(room_id, {}).items()
            },
            "screen_shares": screen_shares,
            "screen_share_streams": self._screen_share_streams.get(room_id, {})
        }
    
    async def start_recording(
        self,
        room_id: str,
        recording_options: Dict[str, Any]
    ) -> bool:
        """Start recording a session"""
        session = self._active_sessions.get(room_id)
        if not session:
            logger.error(f"No active session in room {room_id}")
            return False
        
        if session.is_recording:
            logger.warning(f"Session in room {room_id} is already recording")
            return True
        
        # Configure recording parameters
        format = recording_options.get('format', 'webm')
        video_codec = recording_options.get('video_codec', 'vp8')
        audio_codec = recording_options.get('audio_codec', 'opus')
        bitrate = recording_options.get('bitrate', 1000000)
        storage_path = recording_options.get('storage_path', '/recordings')
        
        # Generate recording filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        recording_filename = f"{room_id}_{session.session_id}_{timestamp}.{format}"
        recording_path = f"{storage_path}/{recording_filename}"
        
        # TODO: Implement actual recording integration with media server
        # This would typically involve:
        # 1. Sending recording command to media server (Janus, Kurento, etc.)
        # 2. Configuring recording parameters (codecs, bitrate, etc.)
        # 3. Starting the recording pipeline
        
        # For now, simulate recording start
        session.is_recording = True
        session.recording_url = recording_path
        
        # Store recording metadata in quality_metrics since we can't add new fields
        session.quality_metrics['recording_started_at'] = datetime.utcnow().isoformat()
        session.quality_metrics['recording_config'] = {
            'format': format,
            'video_codec': video_codec,
            'audio_codec': audio_codec,
            'bitrate': bitrate
        }
        
        logger.info(f"Started recording session in room {room_id} with config: {session.quality_metrics['recording_config']}")
        return True
    
    async def stop_recording(
        self,
        room_id: str
    ) -> Optional[str]:
        """Stop recording and return the recording URL"""
        session = self._active_sessions.get(room_id)
        if not session or not session.is_recording:
            logger.error(f"No active recording in room {room_id}")
            return None
        
        # TODO: Implement actual recording stop with media server
        # This would typically involve:
        # 1. Sending stop command to media server
        # 2. Waiting for recording to finalize
        # 3. Moving recording to permanent storage
        # 4. Generating access URL
        
        # Calculate recording duration
        recording_duration = None
        if 'recording_started_at' in session.quality_metrics:
            started_at = datetime.fromisoformat(session.quality_metrics['recording_started_at'])
            recording_duration = (datetime.utcnow() - started_at).total_seconds()
        
        # For demonstration, convert local path to accessible URL
        base_url = os.getenv('RECORDING_BASE_URL', 'https://recordings.example.com')
        recording_filename = os.path.basename(session.recording_url)
        recording_url = f"{base_url}/{recording_filename}"
        
        # Update session
        session.is_recording = False
        session.recording_url = recording_url
        session.quality_metrics['recording_ended_at'] = datetime.utcnow().isoformat()
        if recording_duration:
            session.quality_metrics['recording_duration'] = recording_duration
        
        logger.info(f"Stopped recording session in room {room_id}. Duration: {recording_duration}s, URL: {recording_url}")
        return recording_url
    
    async def get_turn_credentials(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get TURN server credentials for a user"""
        import hmac
        import hashlib
        import time
        import base64
        
        # Get TURN server configuration from environment
        turn_server_url = os.getenv("TURN_SERVER_URL")
        turn_secret = os.getenv("TURN_SECRET")
        turn_ttl = int(os.getenv("TURN_TTL", "86400"))  # 24 hours default
        
        if not turn_server_url or not turn_secret:
            logger.warning("TURN server not configured properly")
            return {}
        
        # Generate time-limited credentials using TURN REST API spec
        # Username format: timestamp:user_id
        timestamp = int(time.time()) + turn_ttl
        username = f"{timestamp}:{user_id}"
        
        # Generate credential using HMAC-SHA1
        credential = base64.b64encode(
            hmac.new(
                turn_secret.encode('utf-8'),
                username.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        # Parse TURN server URLs
        turn_urls = []
        if "," in turn_server_url:
            turn_urls = turn_server_url.split(",")
        else:
            turn_urls = [turn_server_url]
        
        return {
            "urls": turn_urls,
            "username": username,
            "credential": credential,
            "credentialType": "password"
        }
    
    async def get_ice_servers(self) -> List[Dict[str, Any]]:
        """Get list of ICE servers for WebRTC"""
        ice_servers = []
        
        # Add public STUN servers
        stun_servers = os.getenv("STUN_SERVERS", "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302")
        for stun_server in stun_servers.split(","):
            ice_servers.append({
                "urls": [stun_server.strip()]
            })
        
        # Add TURN servers if configured
        turn_server_url = os.getenv("TURN_SERVER_URL")
        if turn_server_url:
            # Get fresh TURN credentials
            turn_creds = await self.get_turn_credentials("system")
            if turn_creds:
                ice_servers.append(turn_creds)
        
        return ice_servers
    
    async def _handle_screen_share_signal(
        self,
        signal: WebRTCSignal
    ) -> Optional[WebRTCSignal]:
        """Handle screen share specific WebRTC signals"""
        room_id = signal.data.get("room_id")
        
        if signal.type == "screen-share-offer":
            # Initialize screen share stream tracking
            if room_id not in self._screen_share_streams:
                self._screen_share_streams[room_id] = {}
            
            self._screen_share_streams[room_id][signal.from_user] = {
                "offer_sdp": signal.data.get("sdp"),
                "stream_id": signal.data.get("stream_id"),
                "connected": False
            }
            
            # Forward to screen share service if available
            if self.screen_share_service:
                response = await self.screen_share_service.handle_webrtc_signal(
                    "screen-share-offer", room_id, signal.from_user, signal.data
                )
                if response:
                    return WebRTCSignal(
                        type="screen-share-answer",
                        from_user="system",
                        to_user=signal.from_user,
                        data=response
                    )
        
        elif signal.type == "screen-share-answer":
            # Mark screen share stream as connected
            if room_id in self._screen_share_streams:
                if signal.from_user in self._screen_share_streams[room_id]:
                    self._screen_share_streams[room_id][signal.from_user]["answer_sdp"] = signal.data.get("sdp")
                    self._screen_share_streams[room_id][signal.from_user]["connected"] = True
        
        elif signal.type == "screen-share-candidate":
            # Handle screen share ICE candidates
            if self.screen_share_service:
                await self.screen_share_service.handle_webrtc_signal(
                    "screen-share-ice-candidate", room_id, signal.from_user, signal.data
                )
        
        return signal
    
    async def get_screen_share_constraints(
        self,
        quality: str = "auto"
    ) -> Dict[str, Any]:
        """Get constraints for screen capture"""
        if self.screen_share_service:
            from ..models.extended_models import ScreenShareQuality
            quality_enum = ScreenShareQuality(quality) if quality in ["low", "medium", "high", "auto"] else ScreenShareQuality.AUTO
            return await self.screen_share_service.get_capture_constraints(quality_enum)
        
        # Default constraints if no screen share service
        return {
            "video": {
                "cursor": "always",
                "displaySurface": "monitor",
                "width": {"ideal": 1920, "max": 3840},
                "height": {"ideal": 1080, "max": 2160},
                "frameRate": {"ideal": 30, "max": 60}
            }
        }
    
    async def update_screen_share_quality(
        self,
        room_id: str,
        user_id: str,
        quality: str
    ) -> bool:
        """Update screen share quality settings"""
        if self.screen_share_service:
            # Find active screen share session
            sessions = await self.screen_share_service.get_active_sessions(room_id)
            for session in sessions:
                if session.user_id == user_id:
                    from ..models.extended_models import ScreenShareQuality
                    quality_enum = ScreenShareQuality(quality) if quality in ["low", "medium", "high", "auto"] else ScreenShareQuality.AUTO
                    return await self.screen_share_service.update_quality(
                        session.session_id, quality_enum
                    )
        return False
    
    # Validation methods
    
    def _validate_sdp(self, sdp: str) -> bool:
        """Validate SDP format and content"""
        if not sdp or not isinstance(sdp, str):
            return False
        
        # Basic SDP validation
        required_lines = ["v=", "o=", "s=", "t="]
        sdp_lines = sdp.strip().split("\n")
        
        for required in required_lines:
            if not any(line.startswith(required) for line in sdp_lines):
                logger.error(f"SDP missing required line: {required}")
                return False
        
        # Check for media sections
        has_media = any(line.startswith("m=") for line in sdp_lines)
        if not has_media:
            logger.error("SDP has no media sections")
            return False
        
        # Validate version
        version_line = next((line for line in sdp_lines if line.startswith("v=")), None)
        if version_line != "v=0":
            logger.error(f"Invalid SDP version: {version_line}")
            return False
        
        return True
    
    async def _validate_signal_authenticity(self, signal: WebRTCSignal) -> bool:
        """Validate that the signal is from an authentic user"""
        room_id = signal.data.get("room_id")
        if not room_id:
            return False
        
        # Check if user is in the session
        session = self._active_sessions.get(room_id)
        if not session:
            logger.error(f"No active session for room {room_id}")
            return False
        
        # Verify sender is a participant
        if signal.from_user not in session.participants:
            logger.error(f"User {signal.from_user} not in session for room {room_id}")
            return False
        
        # For offers/answers, verify target is also in session
        if signal.type in ["offer", "answer"] and signal.to_user not in session.participants:
            logger.error(f"Target user {signal.to_user} not in session for room {room_id}")
            return False
        
        return True
    
    async def _send_pli_request(self, room_id: str, user_id: str) -> None:
        """Send Picture Loss Indication (PLI) request to trigger keyframe"""
        # In a real implementation, this would send an RTCP PLI packet
        # to the media server to request a keyframe from the sender
        
        # Check if user has an active screen share
        if room_id in self._screen_share_streams and user_id in self._screen_share_streams[room_id]:
            stream_info = self._screen_share_streams[room_id][user_id]
            if stream_info.get("connected"):
                # Create PLI signal
                pli_signal = WebRTCSignal(
                    type="rtcp-pli",
                    from_user="system",
                    to_user=user_id,
                    data={
                        "room_id": room_id,
                        "request_type": "keyframe",
                        "reason": "viewer_buffer_recovery"
                    }
                )
                
                # In production, this would trigger actual RTCP PLI through media server
                logger.info(f"Sent PLI request to {user_id} for keyframe in room {room_id}")
                
                # Store PLI request timestamp for rate limiting
                if "last_pli" not in stream_info:
                    stream_info["last_pli"] = {}
                stream_info["last_pli"][user_id] = datetime.utcnow()
        else:
            logger.warning(f"No active screen share found for PLI request from {user_id} in room {room_id}")


# Global instance
webrtc_service = WebRTCService()