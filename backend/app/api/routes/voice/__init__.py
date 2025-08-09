"""
Voice consultation microservice routes
"""

from .voice import router as voice_router
from .consultation import router as consultation_router
# from .monitoring import router as monitoring_router  # Not implemented yet
# from .gemini_live import router as gemini_live_router  # Not implemented yet
# from .websocket import router as websocket_router  # Not implemented yet

# Import the new voice consultation API routes
try:
    from app.microservices.voice_consultation.routes.voice_api_routes import router as new_voice_api_router
    new_api_available = True
except ImportError:
    new_api_available = False

# Create a combined router for voice microservice
from fastapi import APIRouter

router = APIRouter()
router.include_router(voice_router, tags=["voice"])
# DISABLED: Old consultation router - conflicts with new API
# router.include_router(consultation_router, prefix="/consultations", tags=["voice-consultations"])
# router.include_router(monitoring_router, prefix="/monitoring", tags=["voice-monitoring"])  # Not implemented yet
# router.include_router(gemini_live_router, prefix="/gemini-live", tags=["voice-gemini-live"])  # Not implemented yet
# router.include_router(websocket_router, tags=["voice-websocket"])  # Not implemented yet

# Include new voice consultation API if available
if new_api_available:
    router.include_router(new_voice_api_router, prefix="/consultation", tags=["voice-consultation-v2"])

__all__ = ["router", "voice_router", "consultation_router", "monitoring_router", "gemini_live_router", "websocket_router"]