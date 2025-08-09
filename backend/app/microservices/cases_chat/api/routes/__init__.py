"""
Main API router for Cases Chat microservice
"""
from fastapi import APIRouter
from .cases import router as cases_router
from .chat import router as chat_router
from .media import router as media_router
from .doctors import router as doctors_router
from .websocket import router as websocket_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Register all route modules
api_router.include_router(cases_router, prefix="/cases", tags=["cases"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(media_router, prefix="/media", tags=["media"])
api_router.include_router(doctors_router, prefix="/doctors", tags=["doctors"])
api_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])

__all__ = ["api_router"]