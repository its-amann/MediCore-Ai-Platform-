"""
Common routes shared across all microservices
"""

from .websocket import router as websocket_router
from .health import router as health_router
from .doctors import router as doctors_router
from .medical_context import router as medical_context_router
from .logs import router as logs_router
from .mcp_management import router as mcp_management_router

__all__ = [
    "websocket_router",
    "health_router", 
    "doctors_router",
    "medical_context_router",
    "logs_router",
    "mcp_management_router"
]