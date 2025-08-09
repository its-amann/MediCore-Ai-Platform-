"""
Collaboration microservice routes
"""

from .rooms import router as rooms_router
from .media import router as media_router
from .notifications import router as notifications_router
from .chat import router as chat_router

# Create a combined router for collaboration microservice
from fastapi import APIRouter

router = APIRouter()

# Include all sub-routers
router.include_router(rooms_router, prefix="/rooms", tags=["collaboration-rooms"])
router.include_router(media_router, prefix="/media", tags=["collaboration-media"])
router.include_router(notifications_router, prefix="/notifications", tags=["collaboration-notifications"])
router.include_router(chat_router, prefix="/chat", tags=["collaboration-chat"])

__all__ = ["router", "rooms_router", "media_router", "notifications_router", "chat_router"]