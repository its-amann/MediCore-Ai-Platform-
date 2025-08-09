"""
Organized API routes by microservice
"""

# Import all microservice routers
from .auth import auth_router
from .cases import router as cases_router
from .medical_imaging import router as medical_imaging_router
from .collaboration import router as collaboration_router
from .voice import router as voice_router

# Import common routers
from .common import (
    websocket_router,
    health_router,
    doctors_router,
    medical_context_router,
    logs_router,
    mcp_management_router
)

__all__ = [
    # Microservice routers
    "auth_router",
    "cases_router",
    "medical_imaging_router",
    "collaboration_router", 
    "voice_router",
    # Common routers
    "websocket_router",
    "health_router",
    "doctors_router",
    "medical_context_router",
    "logs_router",
    "mcp_management_router"
]