"""
Medical Imaging WebSocket Adapter
Provides specialized WebSocket functionality for medical imaging using the unified WebSocket manager
"""

import logging
import asyncio
import gc
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Import from the websocket package
from app.core.websocket import websocket_manager, MessageType
from app.core.websocket.config import WebSocketConfig
from app.core.websocket.utils.auth import WebSocketAuth

# Define permissions for medical imaging
class MedicalImagingPermissions:
    VIEW_IMAGES = "medical_imaging:view"
    UPLOAD_IMAGES = "medical_imaging:upload"
    ANALYZE_IMAGES = "medical_imaging:analyze"
    DOWNLOAD_REPORTS = "medical_imaging:download"

# Create websocket auth instance with config
websocket_config = WebSocketConfig()
websocket_auth = WebSocketAuth(websocket_config)

# Simple permission decorator
def require_permission(permission: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # For now, just pass through - implement proper permission checking later
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Make torch import optional
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not installed. GPU memory cleanup features will be disabled.")

logger = logging.getLogger(__name__)


class MedicalImagingMessageType(str, Enum):
    """Medical imaging specific message types"""
    MEDICAL_IMAGING_PROGRESS = "medical_imaging_progress"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PROGRESS = "workflow_progress" 
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_ERROR = "workflow_error"
    WORKFLOW_FAILED = "workflow_failed"
    IMAGE_PROCESSING = "image_processing"
    AI_ANALYSIS = "ai_analysis"
    REPORT_GENERATION = "report_generation"
    GPU_MEMORY_WARNING = "gpu_memory_warning"
    RESOURCE_CLEANUP = "resource_cleanup"


@dataclass
class MedicalImagingSession:
    """Tracks medical imaging session state"""
    user_id: str
    case_id: Optional[str] = None
    report_id: Optional[str] = None
    workflow_id: Optional[str] = None
    total_images: int = 0
    processed_images: int = 0
    current_stage: str = "idle"
    gpu_memory_allocated: float = 0.0
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()


class MedicalImagingWebSocketAdapter:
    """Adapter for medical imaging WebSocket functionality using unified manager"""
    
    def __init__(self):
        # Track medical imaging sessions
        self._medical_sessions: Dict[str, MedicalImagingSession] = {}
        # Track user to session mapping
        self._user_sessions: Dict[str, Set[str]] = {}
        
        # Register medical imaging message handlers
        self._register_handlers()
        
        # Monitoring tasks will be started lazily when needed
        # This avoids RuntimeError when importing without an event loop
        self._monitoring_started = False
        
        logger.info("Medical Imaging WebSocket Adapter initialized")
    
    def _register_handlers(self):
        """Register medical imaging specific message handlers"""
        websocket_manager.register_handler(
            MessageType.NOTIFICATION, 
            self._handle_medical_notification
        )
        
        # We'll handle medical imaging messages through the notification system
        # but could add custom handlers if needed
    
    async def _handle_medical_notification(self, connection_id: str, message: dict):
        """Handle medical imaging notifications"""
        try:
            if connection_id not in websocket_manager._connections:
                return
            
            connection = websocket_manager._connections[connection_id]
            notification_type = message.get("notification_type")
            
            if notification_type == "medical_imaging_progress":
                await self._handle_progress_update(connection_id, message)
            elif notification_type == "gpu_memory_warning":
                await self._handle_gpu_warning(connection_id, message)
            elif notification_type == "resource_cleanup":
                await self._cleanup_user_resources(connection.user_id)
                
        except Exception as e:
            logger.error(f"Error handling medical notification: {e}")
    
    async def send_progress_update(
        self, 
        user_id: str, 
        status: str,
        progress_data: Dict[str, Any]
    ):
        """Send medical imaging progress update to user"""
        # Start monitoring tasks on first use (lazy initialization)
        if not self._monitoring_started:
            self._start_monitoring_tasks()
            self._monitoring_started = True
            
        try:
            # Update session if exists
            session_ids = self._user_sessions.get(user_id, set())
            for session_id in session_ids:
                if session_id in self._medical_sessions:
                    session = self._medical_sessions[session_id]
                    session.last_activity = datetime.utcnow()
                    session.current_stage = status
                    
                    # Update progress counters
                    if "current_image" in progress_data:
                        session.processed_images = progress_data["current_image"]
                    if "total_images" in progress_data:
                        session.total_images = progress_data["total_images"]
            
            # Normalize progress field name for frontend compatibility
            # Backend sends "progress_percentage" but frontend expects "progress"
            if "progress_percentage" in progress_data:
                progress_data["progress"] = progress_data["progress_percentage"]
                # Keep both for backward compatibility
            
            # Send progress message using unified manager
            message = {
                "type": MedicalImagingMessageType.MEDICAL_IMAGING_PROGRESS,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                **progress_data
            }
            
            # Check if websocket_manager exists
            if not websocket_manager:
                logger.error("WebSocket manager not initialized")
                return False
                
            # Send with error handling - send directly to user
            success = await websocket_manager.send_to_user(user_id, message)
            
            if success:
                logger.info(f"Sent medical imaging progress to user {user_id}: {status}")
            else:
                logger.warning(f"Failed to send progress to user {user_id} - no active connections")
            
        except Exception as e:
            logger.error(f"Error sending progress update: {e}")
    
    async def send_workflow_status(
        self, 
        user_id: str, 
        workflow_id: str,
        status: str,
        workflow_data: Optional[Dict[str, Any]] = None
    ):
        """Send workflow status update"""
        try:
            message = {
                "type": MedicalImagingMessageType.WORKFLOW_PROGRESS,
                "workflow_id": workflow_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if workflow_data:
                # Normalize progress field name for frontend compatibility
                if "progress_percentage" in workflow_data:
                    workflow_data["progress"] = workflow_data["progress_percentage"]
                    # Keep both for backward compatibility
                message.update(workflow_data)
            
            if websocket_manager:
                success = await websocket_manager.send_to_user(user_id, message)
                if success:
                    logger.info(f"Sent workflow status to user {user_id}: {workflow_id} - {status}")
                else:
                    logger.warning(f"Failed to send workflow status to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending workflow status: {e}")
    
    async def send_error_notification(
        self, 
        user_id: str, 
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """Send error notification with medical imaging context"""
        try:
            message = {
                "type": MessageType.ERROR,
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "context": "medical_imaging"
            }
            
            if error_context:
                message.update(error_context)
            
            if websocket_manager:
                success = await websocket_manager.send_to_user(user_id, message)
                if success:
                    logger.error(f"Sent error notification to user {user_id}: {error_message}")
                else:
                    logger.error(f"Failed to send error notification to user {user_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
    
    async def create_medical_session(
        self, 
        user_id: str, 
        case_id: str,
        report_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new medical imaging session"""
        try:
            # Check permissions if user_data provided
            if user_data and websocket_auth:
                if not await require_permission(user_data, MedicalImagingPermissions.ANALYZE_IMAGES):
                    raise PermissionError("User does not have permission to analyze images")
            
            session_id = f"medical_{user_id}_{datetime.utcnow().timestamp()}"
            
            session = MedicalImagingSession(
                user_id=user_id,
                case_id=case_id,
                report_id=report_id,
                workflow_id=workflow_id
            )
            
            self._medical_sessions[session_id] = session
            
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session_id)
            
            logger.info(f"Created medical imaging session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating medical session: {e}")
            raise
    
    async def get_or_create_medical_session(
        self, 
        user_id: str, 
        case_id: str,
        report_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None
    ) -> tuple[str, bool]:
        """Get existing session or create new one"""
        try:
            # Check for existing active session
            existing_session_id = await self._find_active_session(user_id, case_id)
            
            if existing_session_id:
                logger.info(f"Recovering existing session {existing_session_id}")
                session = self._medical_sessions[existing_session_id]
                
                # Update last activity
                session.last_activity = datetime.utcnow()
                
                # Send current state to reconnected user
                await self.send_progress_update(
                    user_id=user_id,
                    status="session_recovered",
                    progress_data={
                        "session_id": existing_session_id,
                        "case_id": case_id,
                        "current_stage": session.current_stage,
                        "progress_percentage": int((session.processed_images / max(session.total_images, 1)) * 100),
                        "processed_images": session.processed_images,
                        "total_images": session.total_images,
                        "report_id": session.report_id,
                        "workflow_id": session.workflow_id
                    }
                )
                return existing_session_id, True
            
            # Create new session if none exists
            session_id = await self.create_medical_session(user_id, case_id, report_id, workflow_id, user_data)
            return session_id, False
            
        except Exception as e:
            logger.error(f"Error in get_or_create_medical_session: {e}")
            raise
    
    async def _find_active_session(self, user_id: str, case_id: str) -> Optional[str]:
        """Find active session for user and case"""
        user_sessions = self._user_sessions.get(user_id, set())
        for session_id in user_sessions:
            if session_id in self._medical_sessions:
                session = self._medical_sessions[session_id]
                if session.case_id == case_id and session.current_stage != "completed":
                    # Check if session is not too old (1 hour)
                    if (datetime.utcnow() - session.last_activity).total_seconds() < 3600:
                        return session_id
        return None
    
    async def update_session_progress(
        self, 
        session_id: str, 
        processed_images: int,
        total_images: Optional[int] = None
    ):
        """Update session progress"""
        try:
            if session_id in self._medical_sessions:
                session = self._medical_sessions[session_id]
                session.processed_images = processed_images
                if total_images is not None:
                    session.total_images = total_images
                session.last_activity = datetime.utcnow()
                
                # Check for GPU memory usage
                await self._check_gpu_memory(session)
                
        except Exception as e:
            logger.error(f"Error updating session progress: {e}")
    
    async def close_medical_session(self, session_id: str):
        """Close a medical imaging session and cleanup resources"""
        try:
            if session_id not in self._medical_sessions:
                return
            
            session = self._medical_sessions[session_id]
            user_id = session.user_id
            
            # Cleanup resources
            await self._cleanup_session_resources(session_id)
            
            # Remove session tracking
            self._medical_sessions.pop(session_id, None)
            if user_id in self._user_sessions:
                self._user_sessions[user_id].discard(session_id)
                if not self._user_sessions[user_id]:
                    del self._user_sessions[user_id]
            
            logger.info(f"Closed medical imaging session {session_id}")
            
        except Exception as e:
            logger.error(f"Error closing medical session: {e}")
    
    async def _check_gpu_memory(self, session: MedicalImagingSession):
        """Check GPU memory usage and send warnings if needed"""
        try:
            if not TORCH_AVAILABLE or not torch.cuda.is_available():
                return
            
            allocated = torch.cuda.memory_allocated() / 1024**3  # GB
            reserved = torch.cuda.memory_reserved() / 1024**3   # GB
            
            session.gpu_memory_allocated = allocated
            
            # Send warning if memory usage is high
            if allocated > 4.0:  # 4GB threshold
                if websocket_manager:
                    await websocket_manager.send_to_user(session.user_id, {
                        "type": MedicalImagingMessageType.GPU_MEMORY_WARNING,
                        "allocated_gb": allocated,
                    "reserved_gb": reserved,
                    "message": f"High GPU memory usage: {allocated:.1f}GB allocated",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error checking GPU memory: {e}")
    
    async def _cleanup_session_resources(self, session_id: str):
        """Cleanup resources for a specific session"""
        try:
            if session_id not in self._medical_sessions:
                return
            
            session = self._medical_sessions[session_id]
            
            # Clear GPU cache if available
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.info(f"GPU cache cleared for session {session_id}")
            
            # Force garbage collection
            gc.collect()
            
            # Send cleanup notification
            if websocket_manager:
                await websocket_manager.send_to_user(session.user_id, {
                    "type": MedicalImagingMessageType.RESOURCE_CLEANUP,
                    "session_id": session_id,
                "message": "Resources cleaned up successfully",
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error cleaning up session resources: {e}")
    
    async def _cleanup_user_resources(self, user_id: str):
        """Cleanup all resources for a user"""
        try:
            session_ids = list(self._user_sessions.get(user_id, set()))
            
            for session_id in session_ids:
                await self._cleanup_session_resources(session_id)
            
            logger.info(f"Cleaned up all resources for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up user resources: {e}")
    
    async def _handle_progress_update(self, connection_id: str, message: dict):
        """Handle progress update messages"""
        try:
            # Additional processing for progress updates if needed
            logger.debug(f"Processing progress update for connection {connection_id}")
            
        except Exception as e:
            logger.error(f"Error handling progress update: {e}")
    
    async def _handle_gpu_warning(self, connection_id: str, message: dict):
        """Handle GPU memory warnings"""
        try:
            # Force cleanup if memory is critically high
            allocated = message.get("allocated_gb", 0)
            if allocated > 6.0:  # 6GB critical threshold
                await self._emergency_gpu_cleanup()
                
        except Exception as e:
            logger.error(f"Error handling GPU warning: {e}")
    
    async def _emergency_gpu_cleanup(self):
        """Emergency GPU memory cleanup"""
        try:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                gc.collect()
                
                allocated_after = torch.cuda.memory_allocated() / 1024**3
                logger.warning(f"Emergency GPU cleanup completed. Memory after cleanup: {allocated_after:.1f}GB")
                
        except Exception as e:
            logger.error(f"Error in emergency GPU cleanup: {e}")
    
    def _start_monitoring_tasks(self):
        """Start background monitoring tasks"""
        # Start session monitoring task
        asyncio.create_task(self._monitor_sessions())
        asyncio.create_task(self._monitor_gpu_memory())
    
    async def _monitor_sessions(self):
        """Monitor active medical imaging sessions with disconnection handling"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                current_time = datetime.utcnow()
                stale_sessions = []
                disconnected_sessions = []
                
                # Check each active session
                for session_id, session in self._medical_sessions.items():
                    # Check if user still connected
                    if not await self._is_user_connected(session.user_id):
                        # Don't immediately clean up - allow reconnection within 30 minutes
                        if (current_time - session.last_activity).total_seconds() > 1800:
                            disconnected_sessions.append(session_id)
                        continue
                    
                    # Check for stale sessions (inactive for more than 30 minutes)
                    if (current_time - session.last_activity).total_seconds() > 1800:
                        stale_sessions.append(session_id)
                
                # Cleanup disconnected sessions that are old
                for session_id in disconnected_sessions:
                    logger.info(f"Cleaning up session for disconnected user: {session_id}")
                    await self.close_medical_session(session_id)
                
                # Cleanup stale sessions
                for session_id in stale_sessions:
                    logger.info(f"Cleaning up stale medical imaging session: {session_id}")
                    await self.close_medical_session(session_id)
                
                total_cleaned = len(stale_sessions) + len(disconnected_sessions)
                if total_cleaned > 0:
                    logger.info(f"Cleaned up {total_cleaned} medical imaging sessions")
                
            except Exception as e:
                logger.error(f"Error in session monitoring: {e}", exc_info=True)
                await asyncio.sleep(30)  # Brief pause before retrying
    
    async def _is_user_connected(self, user_id: str) -> bool:
        """Check if user has active WebSocket connections"""
        if websocket_manager:
            # Check if the WebSocket manager has a method to check user connections
            if hasattr(websocket_manager, 'has_user_connections'):
                return await websocket_manager.has_user_connections(user_id)
            elif hasattr(websocket_manager, 'get_user_connections'):
                connections = await websocket_manager.get_user_connections(user_id)
                return len(connections) > 0
        return False
    
    async def _monitor_gpu_memory(self):
        """Monitor GPU memory usage"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                
                if not TORCH_AVAILABLE or not torch.cuda.is_available():
                    continue
                
                allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                
                # If memory usage is high and no active sessions, cleanup
                if allocated > 2.0 and not self._medical_sessions:
                    await self._emergency_gpu_cleanup()
                
            except Exception as e:
                logger.error(f"Error in GPU memory monitoring: {e}")
                await asyncio.sleep(30)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active medical imaging sessions"""
        try:
            total_sessions = len(self._medical_sessions)
            active_users = len(self._user_sessions)
            
            # Calculate total images being processed
            total_images_processing = sum(
                session.total_images - session.processed_images 
                for session in self._medical_sessions.values()
            )
            
            gpu_memory = 0.0
            if TORCH_AVAILABLE and torch.cuda.is_available():
                gpu_memory = torch.cuda.memory_allocated() / 1024**3
            
            return {
                "total_sessions": total_sessions,
                "active_users": active_users,
                "images_in_queue": total_images_processing,
                "gpu_memory_gb": gpu_memory,
                "session_details": [
                    {
                        "session_id": session_id,
                        "user_id": session.user_id,
                        "case_id": session.case_id,
                        "progress": f"{session.processed_images}/{session.total_images}",
                        "current_stage": session.current_stage,
                        "last_activity": session.last_activity.isoformat()
                    }
                    for session_id, session in self._medical_sessions.items()
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {"error": str(e)}


# Create singleton instance
medical_imaging_websocket = MedicalImagingWebSocketAdapter()


# Convenience functions for easy integration
async def send_medical_progress(user_id: str, status: str, **kwargs):
    """Convenience function to send medical imaging progress"""
    await medical_imaging_websocket.send_progress_update(user_id, status, kwargs)


async def send_workflow_update(user_id: str, workflow_id: str, status: str, **kwargs):
    """Convenience function to send workflow updates"""
    await medical_imaging_websocket.send_workflow_status(user_id, workflow_id, status, kwargs)


async def send_medical_error(user_id: str, error_message: str, **kwargs):
    """Convenience function to send medical imaging errors"""
    await medical_imaging_websocket.send_error_notification(user_id, error_message, kwargs)


async def create_session(user_id: str, case_id: str, **kwargs) -> str:
    """Convenience function to create medical imaging session"""
    return await medical_imaging_websocket.create_medical_session(user_id, case_id, **kwargs)


async def close_session(session_id: str):
    """Convenience function to close medical imaging session"""
    await medical_imaging_websocket.close_medical_session(session_id)


# Cleanup function for application shutdown
async def cleanup_medical_websocket():
    """Cleanup function to be called on application shutdown"""
    try:
        # Close all active sessions
        session_ids = list(medical_imaging_websocket._medical_sessions.keys())
        for session_id in session_ids:
            await medical_imaging_websocket.close_medical_session(session_id)
        
        # Final GPU cleanup
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            gc.collect()
        
        logger.info("Medical imaging WebSocket adapter cleanup complete")
        
    except Exception as e:
        logger.error(f"Error during medical WebSocket cleanup: {e}")