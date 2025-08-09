"""
Integration module for the Collaboration Microservice.

This module provides integration points for the main application,
handles cross-service communication, and exports collaboration functionality.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import HTTPException, status
import httpx

from .config import settings
from .database.database_client import DatabaseClient
from .services.room_service import RoomService
from .services.chat_service import ChatService
from .services.notification_service import NotificationService
from .services.user_service import UserService
from .services.ai_integration_service import AIIntegrationService
from .services.screen_share_service import ScreenShareService
from .services.video_service import VideoService
from .services.webrtc_service import WebRTCService
from .websocket.unified_websocket_adapter import UnifiedWebSocketManager
from .models import Room, RoomType, UserType, Message, Notification
from .service_container import service_container

logger = logging.getLogger(__name__)


class CollaborationIntegration:
    """
    Integration class for connecting the collaboration microservice
    with the main medical AI platform.
    """
    
    def __init__(self):
        """Initialize the integration service."""
        self.db_client = None
        self.room_service = None
        self.chat_service = None
        self.notification_service = None
        self.user_service = None
        self.ai_integration_service = None
        self.screen_share_service = None
        self.video_service = None
        self.webrtc_service = None
        self.websocket_manager = None
        self._http_client = None
        
    async def initialize(self, unified_neo4j_client=None, neo4j_driver=None):
        """
        Initialize all services and connections using unified system resources.
        
        Args:
            unified_neo4j_client: The unified system's Neo4j client to use (legacy)
            neo4j_driver: Direct Neo4j driver from UnifiedDatabaseManager
        """
        try:
            # Initialize database client with proper dependency injection
            if neo4j_driver:
                logger.info("Using shared Neo4j driver from UnifiedDatabaseManager")
                # Create database client with the provided driver
                self.db_client = DatabaseClient(neo4j_driver=neo4j_driver)
                
                # Update the global storage instance to use the shared driver
                from .database.neo4j_storage import CollaborationStorage, set_collaboration_storage
                
                # Create a new storage instance with a wrapper that has the driver
                class DriverWrapper:
                    def __init__(self, driver):
                        self.driver = driver
                        
                    async def run_query(self, query, params=None):
                        """Run a query using the driver"""
                        # Using sync driver in async context
                        def _run():
                            with self.driver.session() as session:
                                result = session.run(query, params or {})
                                # Return the raw records, not just data()
                                return list(result)
                        
                        # Run in thread to avoid blocking
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, _run)
                            
                    async def run_write_query(self, query, params=None):
                        """Run a write query using the driver"""
                        # Using sync driver in async context
                        def _run():
                            with self.driver.session() as session:
                                result = session.run(query, params or {})
                                # Return the raw records, not just data()
                                return list(result)
                        
                        # Run in thread to avoid blocking
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, _run)
                            
                    def get_session(self):
                        """Get a session from the driver"""
                        return self.driver.session()
                
                wrapper = DriverWrapper(neo4j_driver)
                new_storage = CollaborationStorage(neo4j_client=wrapper)
                
                # Set the global storage instance
                set_collaboration_storage(new_storage)
                
                # Also set the storage on the db_client
                self.db_client.storage = new_storage
            elif unified_neo4j_client:
                logger.info("Using unified system's Neo4j client for collaboration service")
                
                # Extract the driver from the unified client if it has one
                driver = None
                if hasattr(unified_neo4j_client, 'driver'):
                    driver = unified_neo4j_client.driver
                else:
                    # The unified_neo4j_client might be the driver itself
                    driver = unified_neo4j_client
                
                # Create database client with the provided driver
                self.db_client = DatabaseClient(neo4j_driver=driver)
                
                # Update the global storage instance to use the unified client
                from .database.neo4j_storage import CollaborationStorage, set_collaboration_storage
                
                # Create a new storage instance with the unified client
                new_storage = CollaborationStorage(neo4j_client=unified_neo4j_client)
                
                # Set the global storage instance
                set_collaboration_storage(new_storage)
                
                # Update our database client's storage reference
                self.db_client.storage = new_storage
                
                # Connect and initialize constraints
                await self.db_client.connect()
            else:
                # Standalone initialization for development/testing
                logger.warning("No unified Neo4j client provided, initializing standalone")
                self.db_client = DatabaseClient()
                await self.db_client.connect()
            
            # Initialize WebSocket manager first
            self.websocket_manager = UnifiedWebSocketManager()
            
            # Initialize async components of websocket manager
            await self.websocket_manager.initialize()
            
            # Initialize services with the database client and WebSocket manager
            self.room_service = RoomService(self.db_client)
            self.chat_service = ChatService(self.db_client)
            self.notification_service = NotificationService(
                self.db_client, 
                websocket_manager=self.websocket_manager
            )
            self.user_service = UserService()  # UserService uses collaboration_storage directly
            self.ai_integration_service = AIIntegrationService()  # AIIntegrationService initialization
            
            # Initialize screen share service with dependencies
            self.screen_share_service = ScreenShareService(
                room_service=self.room_service,
                notification_service=self.notification_service,
                webrtc_service=None,  # Will be set later when WebRTC service is initialized
                chat_service=self.chat_service
            )
            
            # Initialize WebRTC service with screen share service
            self.webrtc_service = WebRTCService(screen_share_service=self.screen_share_service)
            
            # Now update screen share service with WebRTC service reference
            self.screen_share_service.webrtc_service = self.webrtc_service
            
            # Initialize video service with dependencies
            self.video_service = VideoService(
                db_client=self.db_client,
                redis_client=None,  # Redis client can be added later if needed
                screen_share_service=self.screen_share_service
            )
            
            # Register services in the container
            service_container.register('db_client', self.db_client)
            service_container.register('websocket_manager', self.websocket_manager)
            service_container.register('room_service', self.room_service)
            service_container.register('chat_service', self.chat_service)
            service_container.register('notification_service', self.notification_service)
            service_container.register('user_service', self.user_service)
            service_container.register('ai_integration_service', self.ai_integration_service)
            service_container.register('screen_share_service', self.screen_share_service)
            service_container.register('webrtc_service', self.webrtc_service)
            service_container.register('video_service', self.video_service)
            
            # Initialize HTTP client for cross-service communication (local communication within unified app)
            self._http_client = httpx.AsyncClient(
                base_url="http://localhost:8000",  # Local communication within unified app
                timeout=30.0
            )
            service_container.register('http_client', self._http_client)
            
            logger.info("Collaboration integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize collaboration integration: {e}")
            raise
    
    async def shutdown(self):
        """
        Cleanup and shutdown all services.
        
        This should be called during application shutdown.
        """
        try:
            # Close HTTP client
            if self._http_client:
                await self._http_client.aclose()
            
            # Disconnect WebSocket connections
            if self.websocket_manager:
                await self.websocket_manager.disconnect_all()
            
            # Close database connection
            if self.db_client:
                await self.db_client.disconnect()
                
            logger.info("Collaboration integration shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during collaboration integration shutdown: {e}")
    
    # Room Management Integration
    
    async def create_room_for_case(
        self,
        case_id: str,
        created_by: str,
        participants: List[str],
        room_type: RoomType = RoomType.CASE_DISCUSSION
    ) -> Room:
        """
        Create a collaboration room for a medical case.
        
        Args:
            case_id: The medical case ID
            created_by: User ID of the room creator
            participants: List of user IDs to invite
            room_type: Type of room to create
            
        Returns:
            Created room object
        """
        # Verify case exists through main app API
        try:
            response = await self._http_client.get(f"/api/v1/cases/{case_id}")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Case {case_id} not found"
                )
        except httpx.RequestError as e:
            logger.error(f"Failed to verify case {case_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to verify case"
            )
        
        # Create room with case context
        room_name = f"Case {case_id} - {room_type.value.title()}"
        room = await self.room_service.create_room(
            name=room_name,
            created_by=created_by,
            room_type=room_type,
            max_participants=settings.ROOM_MAX_PARTICIPANTS,
            metadata={"case_id": case_id}
        )
        
        # Add participants
        for participant_id in participants:
            await self.room_service.add_participant(
                room.id,
                participant_id,
                UserType.doctor  # Default to doctor, can be enhanced
            )
        
        # Send notifications
        await self._notify_participants(room, participants, created_by)
        
        return room
    
    # User Integration
    
    async def sync_user_from_main_app(self, user_id: str) -> Dict[str, Any]:
        """
        Sync user data from the main application.
        
        Args:
            user_id: The user ID to sync
            
        Returns:
            User data dictionary
        """
        try:
            response = await self._http_client.get(f"/api/v1/users/{user_id}")
            if response.status_code == 200:
                user_data = response.json()
                
                # Update local user record
                await self.user_service.update_user(
                    user_id=user_id,
                    name=user_data.get("name"),
                    email=user_data.get("email"),
                    user_type=UserType[user_data.get("role", "doctor")],
                    metadata=user_data
                )
                
                return user_data
            else:
                logger.warning(f"User {user_id} not found in main app")
                return None
                
        except Exception as e:
            logger.error(f"Failed to sync user {user_id}: {e}")
            return None
    
    # Notification Integration
    
    async def send_collaboration_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Send a notification through both local and main app notification systems.
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            metadata: Additional metadata
            
        Returns:
            Created notification object
        """
        # Create local notification
        notification = await self.notification_service.create_notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            metadata=metadata or {}
        )
        
        # Forward to main app notification system
        try:
            await self._http_client.post(
                "/api/v1/notifications",
                json={
                    "user_id": user_id,
                    "type": f"collaboration_{notification_type}",
                    "title": title,
                    "message": message,
                    "metadata": {
                        **(metadata or {}),
                        "collaboration_notification_id": str(notification.id),
                        "source": "collaboration_microservice"
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to forward notification to main app: {e}")
        
        return notification
    
    # AI Integration
    
    async def get_ai_suggestions_for_case(
        self,
        case_id: str,
        context: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get AI suggestions for a case discussion.
        
        Args:
            case_id: The medical case ID
            context: Current discussion context
            user_id: Requesting user ID
            
        Returns:
            AI suggestions and recommendations
        """
        try:
            # Get case details from main app
            case_response = await self._http_client.get(f"/api/v1/cases/{case_id}")
            if case_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Case {case_id} not found"
                )
            
            case_data = case_response.json()
            
            # Get AI suggestions through main app's AI service
            ai_response = await self._http_client.post(
                "/api/v1/ai/suggestions",
                json={
                    "case_id": case_id,
                    "context": context,
                    "user_id": user_id,
                    "case_data": case_data,
                    "request_type": "collaboration_assistance"
                }
            )
            
            if ai_response.status_code == 200:
                return ai_response.json()
            else:
                logger.error(f"AI service returned error: {ai_response.status_code}")
                return {
                    "suggestions": [],
                    "error": "Failed to get AI suggestions"
                }
                
        except Exception as e:
            logger.error(f"Failed to get AI suggestions for case {case_id}: {e}")
            return {
                "suggestions": [],
                "error": str(e)
            }
    
    # WebSocket Integration
    
    async def broadcast_to_case_participants(
        self,
        case_id: str,
        message_type: str,
        data: Dict[str, Any]
    ):
        """
        Broadcast a message to all participants in case-related rooms.
        
        Args:
            case_id: The medical case ID
            message_type: Type of message to broadcast
            data: Message data
        """
        # Find all rooms related to this case
        rooms = await self.room_service.get_rooms_by_metadata({"case_id": case_id})
        
        for room in rooms:
            await self.websocket_manager.broadcast_to_room(
                room.id,
                {
                    "type": message_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "collaboration_integration"
                }
            )
    
    # Helper Methods
    
    async def _notify_participants(
        self,
        room: Room,
        participant_ids: List[str],
        created_by: str
    ):
        """Send notifications to room participants."""
        creator_name = await self._get_user_name(created_by)
        
        for participant_id in participant_ids:
            if participant_id != created_by:
                await self.send_collaboration_notification(
                    user_id=participant_id,
                    notification_type="room_invitation",
                    title="New Collaboration Room",
                    message=f"{creator_name} invited you to join '{room.name}'",
                    metadata={
                        "room_id": str(room.id),
                        "room_type": room.room_type.value,
                        "created_by": created_by
                    }
                )
    
    async def _get_user_name(self, user_id: str) -> str:
        """Get user name from local cache or main app."""
        # Try local cache first
        user = await self.user_service.get_user(user_id)
        if user and user.name:
            return user.name
        
        # Sync from main app
        user_data = await self.sync_user_from_main_app(user_id)
        if user_data:
            return user_data.get("name", "Unknown User")
        
        return "Unknown User"


# Global integration instance
collaboration_integration = CollaborationIntegration()


# Export convenience functions for main app integration

async def create_case_collaboration_room(
    case_id: str,
    created_by: str,
    participants: List[str],
    room_type: str = "case_discussion"
) -> Dict[str, Any]:
    """
    Convenience function to create a collaboration room for a case.
    
    This function can be imported and used directly by the main app.
    """
    room = await collaboration_integration.create_room_for_case(
        case_id=case_id,
        created_by=created_by,
        participants=participants,
        room_type=RoomType[room_type]
    )
    
    return {
        "room_id": str(room.id),
        "name": room.name,
        "type": room.room_type.value,
        "created_at": room.created_at.isoformat(),
        "join_url": f"/collaboration/rooms/{room.id}"
    }


async def notify_collaboration_event(
    user_ids: List[str],
    event_type: str,
    title: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Send collaboration notifications to multiple users.
    
    Returns list of notification IDs.
    """
    notification_ids = []
    
    for user_id in user_ids:
        notification = await collaboration_integration.send_collaboration_notification(
            user_id=user_id,
            notification_type=event_type,
            title=title,
            message=message,
            metadata=metadata
        )
        notification_ids.append(str(notification.id))
    
    return notification_ids


async def get_active_rooms_for_case(case_id: str) -> List[Dict[str, Any]]:
    """
    Get all active collaboration rooms for a specific case.
    """
    rooms = await collaboration_integration.room_service.get_rooms_by_metadata(
        {"case_id": case_id}
    )
    
    active_rooms = []
    for room in rooms:
        if room.is_active:
            participants = await collaboration_integration.room_service.get_room_participants(
                room.id
            )
            active_rooms.append({
                "room_id": str(room.id),
                "name": room.name,
                "type": room.room_type.value,
                "participant_count": len(participants),
                "created_at": room.created_at.isoformat()
            })
    
    return active_rooms