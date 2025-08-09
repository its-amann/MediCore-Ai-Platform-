"""
Screen Sharing Service for managing screen share sessions
Handles screen capture, permissions, quality management, and WebRTC integration
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from ..models.extended_models import (
    ScreenShareSession, ScreenShareStatus, ScreenShareQuality,
    ScreenShareRequest, ScreenSharePermission, ScreenShareEvent,
    ScreenShareConstraints
)
from ..models import UserRole, NotificationType
from ..exceptions import ValidationError, PermissionError

logger = logging.getLogger(__name__)


class ScreenShareService:
    """Service for managing screen sharing sessions with WebRTC integration"""
    
    def __init__(self, room_service=None, notification_service=None, webrtc_service=None, chat_service=None):
        self.room_service = room_service
        self.notification_service = notification_service
        self.webrtc_service = webrtc_service
        self.chat_service = chat_service
        
        # Active screen share sessions by room
        self._active_sessions: Dict[str, ScreenShareSession] = {}
        # Permissions cache
        self._permissions: Dict[str, Dict[str, ScreenSharePermission]] = {}
        # Quality presets
        self._quality_presets = {
            ScreenShareQuality.LOW: {
                "width": 854,
                "height": 480,
                "frameRate": 15,
                "bitrate": 500
            },
            ScreenShareQuality.MEDIUM: {
                "width": 1280,
                "height": 720,
                "frameRate": 30,
                "bitrate": 1500
            },
            ScreenShareQuality.HIGH: {
                "width": 1920,
                "height": 1080,
                "frameRate": 30,
                "bitrate": 3000
            }
        }
        # Maximum concurrent screen shares per room
        self._max_concurrent_shares = 2
    
    async def start_screen_share(
        self,
        room_id: str,
        user_id: str,
        request: ScreenShareRequest
    ) -> ScreenShareSession:
        """Start a screen sharing session"""
        # Validate permissions
        if not await self._check_permission(room_id, user_id, "can_share"):
            raise PermissionError("User does not have permission to share screen")
        
        # Check if user is already sharing
        if await self._is_user_sharing(room_id, user_id):
            raise ValidationError("User is already sharing screen")
        
        # Check concurrent shares limit
        active_count = await self._count_active_shares(room_id)
        if active_count >= self._max_concurrent_shares:
            raise ValidationError(f"Maximum {self._max_concurrent_shares} concurrent screen shares allowed")
        
        # Validate room and participant
        if self.room_service:
            room = await self.room_service.get_room(room_id)
            if not room:
                raise ValidationError("Room not found")
            
            if not room.screen_sharing:
                raise ValidationError("Screen sharing is not enabled for this room")
            
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant:
                raise ValidationError("User is not a participant in this room")
        
        # Create session
        session_id = str(uuid.uuid4())
        session = ScreenShareSession(
            session_id=session_id,
            room_id=room_id,
            user_id=user_id,
            status=ScreenShareStatus.STARTING,
            quality=request.quality,
            source_type=request.source_type,
            source_id=request.source_id,
            can_control=request.allow_control
        )
        
        # Store session
        self._active_sessions[session_id] = session
        
        # Get WebRTC constraints
        constraints = await self._get_capture_constraints(request.quality, request.enable_audio)
        
        # Initialize WebRTC if available
        if self.webrtc_service:
            # Update media state to indicate screen sharing
            await self.webrtc_service._update_media_state(
                room_id, user_id, {"screen": True}
            )
        
        # Send notification
        await self._send_screen_share_event(
            ScreenShareEvent(
                event_type="start",
                room_id=room_id,
                user_id=user_id,
                user_name=participant.user_name if participant else user_id,
                session_id=session_id,
                details={
                    "source_type": request.source_type,
                    "quality": request.quality,
                    "constraints": constraints
                }
            )
        )
        
        # Update status
        session.status = ScreenShareStatus.ACTIVE
        
        logger.info(f"Started screen share session {session_id} in room {room_id} by user {user_id}")
        return session
    
    async def pause_screen_share(
        self,
        room_id: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Pause a screen sharing session"""
        # Find session
        session = None
        if session_id:
            session = self._active_sessions.get(session_id)
        else:
            # Find user's active session in room
            for sid, sess in self._active_sessions.items():
                if sess.room_id == room_id and sess.user_id == user_id and sess.status == ScreenShareStatus.ACTIVE:
                    session = sess
                    session_id = sid
                    break
        
        if not session:
            logger.warning(f"No active screen share session found for user {user_id} in room {room_id}")
            return False
        
        # Update status
        session.status = ScreenShareStatus.PAUSED
        
        # Update WebRTC state to pause the stream
        if self.webrtc_service:
            await self.webrtc_service._update_media_state(
                room_id, user_id, {"screen_paused": True}
            )
        
        # Send notification
        await self._send_screen_share_event(
            ScreenShareEvent(
                event_type="pause",
                room_id=room_id,
                user_id=user_id,
                user_name=session.user_id,
                session_id=session_id,
                details={"quality": session.quality.value}
            )
        )
        
        logger.info(f"Paused screen share session {session_id}")
        return True
    
    async def resume_screen_share(
        self,
        room_id: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Resume a paused screen sharing session"""
        # Find session
        session = None
        if session_id:
            session = self._active_sessions.get(session_id)
        else:
            # Find user's paused session in room
            for sid, sess in self._active_sessions.items():
                if sess.room_id == room_id and sess.user_id == user_id and sess.status == ScreenShareStatus.PAUSED:
                    session = sess
                    session_id = sid
                    break
        
        if not session:
            logger.warning(f"No paused screen share session found for user {user_id} in room {room_id}")
            return False
        
        # Update status
        session.status = ScreenShareStatus.ACTIVE
        
        # Update WebRTC state to resume the stream
        if self.webrtc_service:
            await self.webrtc_service._update_media_state(
                room_id, user_id, {"screen_paused": False}
            )
        
        # Send notification
        await self._send_screen_share_event(
            ScreenShareEvent(
                event_type="resume",
                room_id=room_id,
                user_id=user_id,
                user_name=session.user_id,
                session_id=session_id,
                details={"quality": session.quality.value}
            )
        )
        
        logger.info(f"Resumed screen share session {session_id}")
        return True
    
    async def stop_screen_share(
        self,
        room_id: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Stop a screen sharing session"""
        # Find session
        session = None
        if session_id:
            session = self._active_sessions.get(session_id)
        else:
            # Find user's active session in room
            for sid, sess in self._active_sessions.items():
                if sess.room_id == room_id and sess.user_id == user_id and sess.status == ScreenShareStatus.ACTIVE:
                    session = sess
                    session_id = sid
                    break
        
        if not session:
            logger.warning(f"No active screen share session found for user {user_id} in room {room_id}")
            return False
        
        # Update status
        session.status = ScreenShareStatus.STOPPING
        session.stopped_at = datetime.utcnow()
        
        # Update WebRTC state
        if self.webrtc_service:
            await self.webrtc_service._update_media_state(
                room_id, user_id, {"screen": False}
            )
        
        # Send notification
        await self._send_screen_share_event(
            ScreenShareEvent(
                event_type="stop",
                room_id=room_id,
                user_id=user_id,
                user_name=session.user_id,  # Will be replaced with actual username
                session_id=session_id,
                details={
                    "duration": (session.stopped_at - session.started_at).total_seconds()
                }
            )
        )
        
        # Remove session
        del self._active_sessions[session_id]
        
        logger.info(f"Stopped screen share session {session_id}")
        return True
    
    async def update_quality(
        self,
        session_id: str,
        quality: ScreenShareQuality,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update screen share quality settings"""
        session = self._active_sessions.get(session_id)
        if not session or session.status != ScreenShareStatus.ACTIVE:
            return False
        
        # Update quality
        old_quality = session.quality
        session.quality = quality
        session.last_quality_update = datetime.utcnow()
        
        # Apply quality preset or custom settings
        if quality != ScreenShareQuality.AUTO:
            preset = self._quality_presets.get(quality, {})
            session.resolution = {"width": preset["width"], "height": preset["height"]}
            session.frame_rate = preset["frameRate"]
            session.bitrate = preset["bitrate"]
        elif custom_settings:
            session.resolution = custom_settings.get("resolution", session.resolution)
            session.frame_rate = custom_settings.get("frameRate", session.frame_rate)
            session.bitrate = custom_settings.get("bitrate", session.bitrate)
        
        # Send quality change event
        await self._send_screen_share_event(
            ScreenShareEvent(
                event_type="quality_change",
                room_id=session.room_id,
                user_id=session.user_id,
                user_name=session.user_id,
                session_id=session_id,
                details={
                    "old_quality": old_quality,
                    "new_quality": quality,
                    "resolution": session.resolution,
                    "frame_rate": session.frame_rate,
                    "bitrate": session.bitrate
                }
            )
        )
        
        logger.info(f"Updated screen share quality for session {session_id} from {old_quality} to {quality}")
        return True
    
    async def update_metrics(
        self,
        session_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Update quality metrics for a screen share session"""
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        
        # Update metrics
        if "resolution" in metrics:
            session.resolution = metrics["resolution"]
        if "frameRate" in metrics:
            session.frame_rate = metrics["frameRate"]
        if "bitrate" in metrics:
            session.bitrate = metrics["bitrate"]
        if "packetLoss" in metrics:
            session.packet_loss = metrics["packetLoss"]
        
        session.last_quality_update = datetime.utcnow()
        
        # Auto-adjust quality if needed
        if session.quality == ScreenShareQuality.AUTO:
            await self._auto_adjust_quality(session, metrics)
        
        return True
    
    async def grant_control(
        self,
        session_id: str,
        granter_id: str,
        grantee_id: str
    ) -> bool:
        """Grant control of shared screen to another user"""
        session = self._active_sessions.get(session_id)
        if not session or session.status != ScreenShareStatus.ACTIVE:
            return False
        
        # Only the sharer can grant control
        if session.user_id != granter_id:
            raise PermissionError("Only the screen sharer can grant control")
        
        # Add to control list if not already present
        if grantee_id not in session.can_control:
            session.can_control.append(grantee_id)
        
        # Send notification
        await self._send_screen_share_event(
            ScreenShareEvent(
                event_type="control_granted",
                room_id=session.room_id,
                user_id=granter_id,
                user_name=granter_id,
                session_id=session_id,
                details={
                    "grantee_id": grantee_id
                }
            )
        )
        
        logger.info(f"Granted control of session {session_id} to user {grantee_id}")
        return True
    
    async def revoke_control(
        self,
        session_id: str,
        revoker_id: str,
        revokee_id: str
    ) -> bool:
        """Revoke control of shared screen from a user"""
        session = self._active_sessions.get(session_id)
        if not session or session.status != ScreenShareStatus.ACTIVE:
            return False
        
        # Only the sharer can revoke control
        if session.user_id != revoker_id:
            raise PermissionError("Only the screen sharer can revoke control")
        
        # Remove from control list
        if revokee_id in session.can_control:
            session.can_control.remove(revokee_id)
        
        logger.info(f"Revoked control of session {session_id} from user {revokee_id}")
        return True
    
    async def get_active_sessions(
        self,
        room_id: str
    ) -> List[ScreenShareSession]:
        """Get all active screen share sessions in a room"""
        sessions = []
        for session in self._active_sessions.values():
            if session.room_id == room_id and session.status == ScreenShareStatus.ACTIVE:
                sessions.append(session)
        return sessions
    
    async def get_session(
        self,
        session_id: str
    ) -> Optional[ScreenShareSession]:
        """Get a specific screen share session"""
        return self._active_sessions.get(session_id)
    
    async def set_permission(
        self,
        room_id: str,
        user_id: str,
        permission: ScreenSharePermission
    ) -> bool:
        """Set screen share permissions for a user"""
        if room_id not in self._permissions:
            self._permissions[room_id] = {}
        
        self._permissions[room_id][user_id] = permission
        
        logger.info(f"Set screen share permissions for user {user_id} in room {room_id}")
        return True
    
    async def get_capture_constraints(
        self,
        quality: ScreenShareQuality = ScreenShareQuality.AUTO,
        enable_audio: bool = False
    ) -> Dict[str, Any]:
        """Get WebRTC constraints for screen capture"""
        constraints = ScreenShareConstraints()
        
        # Apply quality preset
        if quality != ScreenShareQuality.AUTO:
            preset = self._quality_presets.get(quality, {})
            constraints.video["width"]["ideal"] = preset["width"]
            constraints.video["height"]["ideal"] = preset["height"]
            constraints.video["frameRate"]["ideal"] = preset["frameRate"]
        
        # Configure audio
        if not enable_audio:
            return {"video": constraints.video}
        
        return {
            "video": constraints.video,
            "audio": constraints.audio
        }
    
    async def handle_webrtc_signal(
        self,
        signal_type: str,
        room_id: str,
        user_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle WebRTC signaling for screen sharing with enhanced buffering"""
        if signal_type == "screen-share-offer":
            # Find active session
            session = None
            for sess in self._active_sessions.values():
                if sess.room_id == room_id and sess.user_id == user_id:
                    session = sess
                    break
            
            if session:
                # Update stream info
                session.stream_id = data.get("streamId")
                session.track_id = data.get("trackId")
                
                # Configure buffer settings for smooth playback
                buffer_config = {
                    "video": {
                        "jitterBufferTarget": 250,  # 250ms jitter buffer
                        "jitterBufferMaxPackets": 200,
                        "enableDtx": True,  # Discontinuous transmission
                        "enableFec": True,  # Forward error correction
                        "enableNack": True,  # Negative acknowledgment
                        "enableRtx": True,   # Retransmission
                        "playoutDelay": {
                            "min": 100,      # Min 100ms delay
                            "max": 500       # Max 500ms delay
                        }
                    },
                    "bufferManagement": {
                        "targetLevel": 300,   # Target 300ms buffer
                        "minLevel": 100,      # Min 100ms buffer
                        "maxLevel": 1000,     # Max 1s buffer
                        "adaptiveBuffering": True
                    },
                    "qualityAdaptation": {
                        "enabled": True,
                        "minQuality": "low",
                        "maxQuality": session.quality.value,
                        "degradationPreference": "maintain-framerate",
                        "cpuOveruseDetection": True
                    },
                    "networkAdaptation": {
                        "maxBitrate": self._quality_presets[session.quality]["bitrate"] * 1000,
                        "startBitrate": self._quality_presets[session.quality]["bitrate"] * 500,
                        "minBitrate": 250000,  # 250kbps minimum
                        "adaptiveBitrateAlgorithm": "transport-cc"
                    }
                }
                
                # Store buffer config in session
                session.metrics["buffer_config"] = buffer_config
                
                # Add viewer tracking
                if "viewers" not in session.metrics:
                    session.metrics["viewers"] = {}
                
                return {
                    "type": "screen-share-answer",
                    "sessionId": session.session_id,
                    "accepted": True,
                    "bufferConfig": buffer_config,
                    "qualityPreset": self._quality_presets[session.quality]
                }
        
        elif signal_type == "screen-share-ice-candidate":
            # Forward ICE candidate through WebRTC service
            if self.webrtc_service:
                from ..models import WebRTCSignal
                signal = WebRTCSignal(
                    type="ice-candidate",
                    from_user=user_id,
                    to_user=data.get("toUser", ""),
                    data={
                        "candidate": data.get("candidate"),
                        "room_id": room_id,
                        "isScreenShare": True
                    }
                )
                await self.webrtc_service.handle_webrtc_signal(signal)
        
        elif signal_type == "viewer-buffer-status":
            # Handle viewer buffer health reports
            session = None
            for sess in self._active_sessions.values():
                if sess.room_id == room_id:
                    session = sess
                    break
            
            if session:
                viewer_id = data.get("viewerId", user_id)
                buffer_health = data.get("bufferHealth", {})
                
                # Store viewer buffer metrics
                if "viewers" not in session.metrics:
                    session.metrics["viewers"] = {}
                
                session.metrics["viewers"][viewer_id] = {
                    "bufferLevel": buffer_health.get("level", 0),
                    "bufferHealth": buffer_health.get("health", "unknown"),
                    "droppedFrames": buffer_health.get("droppedFrames", 0),
                    "decodedFrames": buffer_health.get("decodedFrames", 0),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Auto-adjust quality if many viewers have poor buffer health
                await self._check_and_adjust_quality_for_viewers(session)
                
                return {
                    "type": "buffer-status-ack",
                    "currentQuality": session.quality.value
                }
        
        elif signal_type == "request-keyframe":
            # Handle keyframe requests for faster recovery
            if self.webrtc_service:
                await self.webrtc_service._send_pli_request(room_id, user_id)
                return {"type": "keyframe-requested"}
        
        return None
    
    async def start_recording(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Start recording a screen share session"""
        session = self._active_sessions.get(session_id)
        if not session or session.status != ScreenShareStatus.ACTIVE:
            return False
        
        # Check permission
        if not await self._check_permission(session.room_id, user_id, "can_record"):
            raise PermissionError("User does not have permission to record screen shares")
        
        session.is_recording = True
        # In production, this would start actual recording
        session.recording_url = f"recordings/screen_{session.session_id}.webm"
        
        logger.info(f"Started recording screen share session {session_id}")
        return True
    
    async def stop_recording(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[str]:
        """Stop recording and return the recording URL"""
        session = self._active_sessions.get(session_id)
        if not session or not session.is_recording:
            return None
        
        session.is_recording = False
        
        logger.info(f"Stopped recording screen share session {session_id}")
        return session.recording_url
    
    # Private helper methods
    
    async def _check_permission(
        self,
        room_id: str,
        user_id: str,
        permission_type: str
    ) -> bool:
        """Check if user has specific screen share permission"""
        # Check cached permissions
        if room_id in self._permissions and user_id in self._permissions[room_id]:
            perm = self._permissions[room_id][user_id]
            if perm.expires_at and perm.expires_at < datetime.utcnow():
                # Permission expired
                del self._permissions[room_id][user_id]
            else:
                return getattr(perm, permission_type, True)
        
        # Check room participant role
        if self.room_service:
            participant = await self.room_service.get_participant(room_id, user_id)
            if participant:
                # Host and co-host have all permissions
                if participant.user_role in [UserRole.HOST, UserRole.CO_HOST]:
                    return True
                # Regular participants can share and view by default
                if permission_type in ["can_share", "can_view"]:
                    return True
        
        return False
    
    async def _is_user_sharing(
        self,
        room_id: str,
        user_id: str
    ) -> bool:
        """Check if user is already sharing screen in room"""
        for session in self._active_sessions.values():
            if (session.room_id == room_id and 
                session.user_id == user_id and 
                session.status == ScreenShareStatus.ACTIVE):
                return True
        return False
    
    async def _count_active_shares(
        self,
        room_id: str
    ) -> int:
        """Count active screen shares in a room"""
        count = 0
        for session in self._active_sessions.values():
            if session.room_id == room_id and session.status == ScreenShareStatus.ACTIVE:
                count += 1
        return count
    
    async def _get_capture_constraints(
        self,
        quality: ScreenShareQuality,
        enable_audio: bool
    ) -> Dict[str, Any]:
        """Get WebRTC constraints based on quality settings"""
        return await self.get_capture_constraints(quality, enable_audio)
    
    async def _auto_adjust_quality(
        self,
        session: ScreenShareSession,
        metrics: Dict[str, Any]
    ) -> None:
        """Auto-adjust quality based on network metrics"""
        packet_loss = metrics.get("packetLoss", 0)
        bitrate = metrics.get("bitrate", 0)
        
        # Downgrade quality if high packet loss
        if packet_loss > 5:
            if session.quality == ScreenShareQuality.HIGH:
                await self.update_quality(session.session_id, ScreenShareQuality.MEDIUM)
            elif session.quality == ScreenShareQuality.MEDIUM:
                await self.update_quality(session.session_id, ScreenShareQuality.LOW)
        
        # Upgrade quality if good conditions
        elif packet_loss < 1 and bitrate > 2000:
            if session.quality == ScreenShareQuality.LOW:
                await self.update_quality(session.session_id, ScreenShareQuality.MEDIUM)
            elif session.quality == ScreenShareQuality.MEDIUM:
                await self.update_quality(session.session_id, ScreenShareQuality.HIGH)
    
    async def _check_and_adjust_quality_for_viewers(
        self,
        session: ScreenShareSession
    ) -> None:
        """Check viewer buffer health and auto-adjust quality if needed"""
        if session.quality == ScreenShareQuality.AUTO and "viewers" in session.metrics:
            viewers = session.metrics["viewers"]
            if not viewers:
                return
            
            # Calculate percentage of viewers with poor buffer health
            poor_health_count = sum(
                1 for v in viewers.values() 
                if v.get("bufferHealth") in ["poor", "critical"] or v.get("bufferLevel", 300) < 150
            )
            
            poor_health_percentage = (poor_health_count / len(viewers)) * 100
            
            # Adjust quality based on viewer experience
            current_preset = self._quality_presets.get(session.quality, self._quality_presets[ScreenShareQuality.MEDIUM])
            current_bitrate = session.bitrate or current_preset["bitrate"]
            
            if poor_health_percentage > 50:
                # More than half viewers struggling - reduce quality
                if current_bitrate > 1000:
                    new_bitrate = int(current_bitrate * 0.7)  # Reduce by 30%
                    await self.update_metrics(session.session_id, {"bitrate": new_bitrate})
                    logger.info(f"Reduced bitrate to {new_bitrate} due to {poor_health_percentage:.1f}% viewers with poor buffer health")
            
            elif poor_health_percentage < 10 and current_bitrate < 3000:
                # Most viewers doing well - can increase quality
                new_bitrate = min(int(current_bitrate * 1.3), 3000)  # Increase by 30%, max 3000
                await self.update_metrics(session.session_id, {"bitrate": new_bitrate})
                logger.info(f"Increased bitrate to {new_bitrate} due to good viewer buffer health")
    
    async def _send_screen_share_event(
        self,
        event: ScreenShareEvent
    ) -> None:
        """Send screen share event notification and chat message"""
        # Send chat system message
        if self.chat_service:
            try:
                await self.chat_service.send_screen_share_event_message(
                    room_id=event.room_id,
                    event_type=event.event_type,
                    user_name=event.user_name,
                    session_id=event.session_id,
                    details=event.details
                )
            except Exception as e:
                logger.error(f"Failed to send screen share chat message: {e}")
        
        # Send notifications
        if self.notification_service:
            # Get all participants in the room
            if self.room_service:
                participants = await self.room_service.get_active_participants(event.room_id)
                for participant in participants:
                    # Create notification
                    notification_type = NotificationType.NEW_MESSAGE  # Use existing type
                    title = f"Screen Share {event.event_type.replace('_', ' ').title()}"
                    
                    if event.event_type == "start":
                        message = f"{event.user_name} started sharing their screen"
                    elif event.event_type == "stop":
                        message = f"{event.user_name} stopped sharing their screen"
                    elif event.event_type == "quality_change":
                        message = f"Screen share quality changed to {event.details.get('new_quality', 'auto')}"
                    elif event.event_type == "pause":
                        message = f"{event.user_name} paused screen sharing"
                    elif event.event_type == "resume":
                        message = f"{event.user_name} resumed screen sharing"
                    else:
                        message = f"Screen share {event.event_type}"
                    
                    await self.notification_service.create_notification(
                        user_id=participant.user_id,
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        data={
                            "room_id": event.room_id,
                            "session_id": event.session_id,
                            "event_type": event.event_type,
                            "details": event.details
                        }
                    )


# Global instance
screen_share_service = ScreenShareService()