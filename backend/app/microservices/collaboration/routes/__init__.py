"""
Routes module for the Collaboration Microservice.

This module is kept for reference but routes are now consolidated in app/api/routes/collaboration.
The individual route files here define the service logic that the API routes use.
"""

# Import individual routers for reference
from .room_routes import router as room_router
from .chat_routes import router as chat_router
from .notification_routes import router as notification_router
from .user_routes import router as user_router
from .screen_share_routes import router as screen_share_router

# Note: The main collaboration_router is no longer created here.
# All routes are now consolidated in app/api/routes/collaboration

__all__ = [
    "room_router",
    "chat_router",
    "notification_router",
    "user_router",
    "screen_share_router"
]