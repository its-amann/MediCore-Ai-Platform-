"""
Collaboration Microservice

This microservice handles real-time collaboration features including:
- Video/audio conferencing rooms
- Real-time chat messaging
- Notifications
- AI assistant integration

Integration exports for main application.
"""

__version__ = "1.0.0"

# Note: collaboration_router is now defined in app/api/routes/collaboration
# Routes are consolidated there for consistency

# Export key services for main app integration
from .services.room_service import RoomService
from .services.chat_service import ChatService
from .services.notification_service import NotificationService
from .services.user_service import UserService
from .services.ai_integration_service import AIIntegrationService

# Export WebSocket handlers (using unified manager)
from .websocket import UnifiedWebSocketManager as WebSocketManager, ChatHandler, VideoHandler

# Export database client
from .database.database_client import DatabaseClient

# Export models
from .models import (
    Room,
    RoomType,
    UserType,
    Message,
    MessageType,
    Notification,
    NotificationType,
    RoomParticipant
)

# Export configuration
from .config import settings

__all__ = [
    # Version
    "__version__",
    
    # Services
    "RoomService",
    "ChatService",
    "NotificationService",
    "UserService",
    "AIIntegrationService",
    
    # WebSocket
    "WebSocketManager",
    "ChatHandler",
    "VideoHandler",
    
    # Database
    "DatabaseClient",
    
    # Models
    "Room",
    "RoomType",
    "UserType",
    "Message",
    "MessageType",
    "Notification",
    "NotificationType",
    "RoomParticipant",
    
    # Configuration
    "settings"
]