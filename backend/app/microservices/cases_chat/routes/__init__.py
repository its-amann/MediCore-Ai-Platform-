"""
Cases Chat Routes Module
Exports all route handlers for the Cases Chat microservice
"""
from .case_routes import router as case_router
from .chat_routes import router as chat_router
from .websocket_routes import router as websocket_router
from .health_routes import router as health_router

__all__ = [
    "case_router",
    "chat_router", 
    "websocket_router",
    "health_router"
]