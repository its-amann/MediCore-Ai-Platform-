"""
Cases microservice routes
"""

from .cases import router as cases_router
from .chat import router as chat_router
from .media import router as media_router
from .doctors import router as doctors_router

# Create a combined router for cases microservice
from fastapi import APIRouter

router = APIRouter()
router.include_router(cases_router, prefix="/cases", tags=["cases"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(media_router, prefix="/media", tags=["cases-media"])
router.include_router(doctors_router, prefix="/doctors", tags=["cases-doctors"])

__all__ = ["router", "cases_router", "chat_router", "media_router", "doctors_router"]