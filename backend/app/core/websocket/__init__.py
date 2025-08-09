"""
Unified WebSocket Architecture for Medical AI System

This package provides a unified WebSocket architecture that supports:
- Core WebSocket management with connection lifecycle
- Extension system for microservice integration
- Plugin architecture for custom functionality
- Backward compatibility with existing implementations
"""

from .manager import WebSocketManager, websocket_manager
from .config import WebSocketConfig
from .handlers.base_handler import BaseHandler
from .handlers.connection_handler import ConnectionHandler
from .extensions.base_wrapper import BaseWrapper
from .utils.auth import WebSocketAuth
from .utils.message_router import MessageRouter

# Maintain backward compatibility
# This ensures existing imports continue to work
from ..websocket_legacy import (
    MessageType,
    ConnectionInfo,
    websocket_manager as legacy_websocket_manager,
    cleanup_websocket_manager
)

__all__ = [
    'WebSocketManager',
    'websocket_manager',
    'WebSocketConfig',
    'BaseHandler',
    'ConnectionHandler',
    'BaseWrapper',
    'WebSocketAuth',
    'MessageRouter',
    # Legacy compatibility
    'MessageType',
    'ConnectionInfo',
    'legacy_websocket_manager',
    'cleanup_websocket_manager'
]