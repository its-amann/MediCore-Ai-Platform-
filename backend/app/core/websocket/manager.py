"""
Enhanced WebSocket Manager with Extension Support

This module provides an enhanced WebSocket manager that maintains backward
compatibility while adding support for extensions and plugins.
"""

import logging
import asyncio
import os
from typing import Dict, Set, List, Optional, Any, Callable, Type
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from fastapi import WebSocket, WebSocketDisconnect

# Import legacy components for backward compatibility
from ..websocket_legacy import (
    MessageType as LegacyMessageType,
    ConnectionInfo as LegacyConnectionInfo,
    WebSocketManager as LegacyWebSocketManager
)

from .config import WebSocketConfig, default_config, env_config
from .handlers.base_handler import BaseHandler
from .extensions.base_wrapper import BaseWrapper
from .utils.message_router import MessageRouter
from .utils.auth import WebSocketAuth
from .utils.rate_limiter import WebSocketRateLimiter, RateLimitConfig
from .utils.error_handler import websocket_error_handler, WebSocketError, WebSocketErrorCode
from .token_refresh import WebSocketTokenRefresh

logger = logging.getLogger(__name__)


@dataclass
class ExtensionRegistry:
    """Registry for WebSocket extensions"""
    extensions: Dict[str, BaseWrapper] = field(default_factory=dict)
    handlers: Dict[str, BaseHandler] = field(default_factory=dict)
    message_handlers: Dict[str, List[Callable]] = field(default_factory=dict)
    
    def register_extension(self, name: str, extension: BaseWrapper):
        """Register a WebSocket extension"""
        self.extensions[name] = extension
        logger.info(f"Registered WebSocket extension: {name}")
    
    def register_handler(self, name: str, handler: BaseHandler):
        """Register a message handler"""
        self.handlers[name] = handler
        logger.info(f"Registered WebSocket handler: {name}")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
        logger.info(f"Registered message handler for type: {message_type}")
    
    def get_extension(self, name: str) -> Optional[BaseWrapper]:
        """Get an extension by name"""
        return self.extensions.get(name)
    
    def get_handler(self, name: str) -> Optional[BaseHandler]:
        """Get a handler by name"""
        return self.handlers.get(name)
    
    def get_message_handlers(self, message_type: str) -> List[Callable]:
        """Get all handlers for a message type"""
        return self.message_handlers.get(message_type, [])


class WebSocketManager:
    """
    Enhanced WebSocket Manager with Extension Support
    
    This manager extends the legacy WebSocket manager with:
    - Extension system for microservice integration
    - Plugin architecture for custom functionality
    - Backward compatibility with existing code
    - Advanced connection management
    """
    
    def __init__(self, config: Optional[WebSocketConfig] = None):
        """Initialize the enhanced WebSocket manager"""
        # Use env_config by default to respect environment variables
        self.config = config or env_config
        logger.info(f"WebSocket Manager initialized with auth_required={self.config.auth_required}, auth_mode={self.config.auth_mode}")
        
        # Initialize legacy manager for backward compatibility
        self._legacy_manager = LegacyWebSocketManager()
        
        # Extension system
        self._registry = ExtensionRegistry()
        self._message_router = MessageRouter()
        self._auth = WebSocketAuth(self.config)
        
        # Token refresh manager
        self._token_refresh = WebSocketTokenRefresh(self)
        
        # Rate limiter with environment configuration
        rate_limit_config = RateLimitConfig(
            max_connections_per_ip=int(os.getenv('WS_MAX_CONNECTIONS_PER_IP', '20')),
            max_connections_per_user=int(os.getenv('WS_MAX_CONNECTIONS_PER_USER', '10')),
            max_messages_per_minute=int(os.getenv('WS_MAX_MESSAGES_PER_MINUTE', '120')),
            max_messages_per_second=int(os.getenv('WS_MAX_MESSAGES_PER_SECOND', '20')),
            ban_duration=int(os.getenv('WS_RATE_LIMIT_BAN_DURATION', '3600')),
            whitelisted_ips=os.getenv('WS_RATE_LIMIT_WHITELIST', '127.0.0.1,::1,localhost').split(',')
        )
        
        # Check if rate limiting is enabled
        if os.getenv('WS_RATE_LIMIT_ENABLED', 'true').lower() == 'true':
            self._rate_limiter = WebSocketRateLimiter(rate_limit_config)
            logger.info(f"WebSocket rate limiting enabled with config: {rate_limit_config}")
        else:
            self._rate_limiter = None
            logger.warning("WebSocket rate limiting is DISABLED - not recommended for production")
        
        # Extension lifecycle
        self._extensions_initialized = False
        self._shutdown_requested = False
        
        # Metrics and monitoring
        self._metrics = {
            'connections_total': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'extensions_loaded': 0,
            'errors_total': 0
        }
        
        logger.info("Enhanced WebSocket Manager initialized")
    
    async def initialize(self):
        """Initialize the manager and all extensions"""
        if self._extensions_initialized:
            return
        
        logger.info("Initializing WebSocket manager and extensions...")
        
        # Start token monitoring
        if hasattr(self, '_token_refresh'):
            await self._token_refresh.start_monitoring()
        
        # Start rate limiter
        if hasattr(self, '_rate_limiter'):
            await self._rate_limiter.start()
        
        # Initialize extensions in priority order
        for ext_config in self.config.get_sorted_extensions():
            if ext_config.name in self._registry.extensions:
                extension = self._registry.extensions[ext_config.name]
                try:
                    await extension.initialize(ext_config.config)
                    logger.info(f"Initialized extension: {ext_config.name}")
                except Exception as e:
                    logger.error(f"Failed to initialize extension {ext_config.name}: {e}")
        
        self._extensions_initialized = True
        logger.info("WebSocket manager initialization complete")
    
    def register_extension(self, name: str, extension: BaseWrapper, config: Optional[Dict[str, Any]] = None):
        """Register a WebSocket extension"""
        from .config import ExtensionConfig
        
        # Register extension in registry
        self._registry.register_extension(name, extension)
        
        # Register extension configuration
        ext_config = ExtensionConfig(
            name=name,
            enabled=True,
            config=config or {},
            priority=getattr(extension, 'priority', 100)
        )
        self.config.register_extension(name, ext_config)
        
        # Set up extension with manager reference
        extension.set_manager(self)
        
        self._metrics['extensions_loaded'] += 1
        logger.info(f"Registered extension: {name}")
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler (backward compatibility)"""
        self._registry.register_message_handler(message_type, handler)
        # Also register with legacy manager if it's a valid legacy type
        if hasattr(self._legacy_manager, 'register_handler'):
            try:
                # Try to convert to legacy type, but ignore if it's a custom type
                legacy_type = LegacyMessageType(message_type)
                self._legacy_manager.register_handler(legacy_type, handler)
            except ValueError:
                # This is a custom message type, just log it
                logger.debug(f"Custom message type '{message_type}' registered (not in legacy types)")
    
    async def connect(self, websocket: WebSocket, user_id: str, username: str, **kwargs) -> str:
        """
        Enhanced connection method with extension support
        
        Args:
            websocket: WebSocket connection
            user_id: User identifier
            username: Username
            **kwargs: Additional connection parameters for extensions
            
        Returns:
            Connection ID
        """
        # Extract client IP from WebSocket
        client_ip = "unknown"
        if hasattr(websocket, 'client') and websocket.client:
            client_ip = websocket.client.host
        elif hasattr(websocket, 'headers'):
            # Try to get from headers (X-Forwarded-For, X-Real-IP)
            client_ip = websocket.headers.get('X-Forwarded-For', 
                       websocket.headers.get('X-Real-IP', client_ip))
        
        # Generate temporary connection ID for rate limiting check
        temp_connection_id = str(uuid.uuid4())
        
        # Check rate limiting BEFORE authentication
        if hasattr(self, '_rate_limiter'):
            allowed, reason = await self._rate_limiter.check_connection_allowed(
                temp_connection_id, client_ip, user_id
            )
            if not allowed:
                logger.warning(f"WebSocket connection rejected by rate limiter: {reason} (IP: {client_ip})")
                raise WebSocketError(
                    f"Connection rejected: {reason}",
                    WebSocketErrorCode.RATE_LIMIT_EXCEEDED,
                    {"ip": client_ip, "user_id": user_id}
                )
        
        # Authenticate if required
        authenticated_user_id = user_id
        authenticated_username = username
        
        # Check if this is a testing connection (skip authentication)
        testing_mode = kwargs.get("testing_mode", False)
        
        logger.info(f"WebSocket connect attempt - auth_required={self.config.auth_required}, testing_mode={testing_mode}, has_token={'token' in kwargs}")
        
        if self.config.auth_required and not testing_mode:
            logger.debug(f"WebSocket authentication required - checking credentials with auth_mode={self.config.auth_mode}")
            auth_result = await self._auth.authenticate_connection(websocket, **kwargs)
            logger.info(f"WebSocket auth result: is_valid={auth_result.is_valid}, user_id={auth_result.user_id}, error={auth_result.error_message}")
            if not auth_result.is_valid:
                logger.warning(f"WebSocket authentication failed: {auth_result.error_message}")
                # Don't close the WebSocket here - let the route handler do it
                raise WebSocketError(
                    f"Authentication failed: {auth_result.error_message}",
                    WebSocketErrorCode.AUTH_FAILED,
                    {"user_id": user_id}
                )
            
            # Use authenticated user information if available
            if auth_result.user_id:
                authenticated_user_id = auth_result.user_id
            if auth_result.username:
                authenticated_username = auth_result.username
                
            logger.info(f"WebSocket authentication successful for user: {authenticated_username} (ID: {authenticated_user_id})")
        elif testing_mode:
            logger.info(f"WebSocket testing mode - skipping authentication for user: {username} (ID: {user_id})")
        else:
            logger.info(f"WebSocket authentication disabled - using provided credentials: {username} (ID: {user_id})")
        
        # Use legacy manager for core connection handling with authenticated user info
        try:
            connection_id = await self._legacy_manager.connect(websocket, authenticated_user_id, authenticated_username)
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            raise
        
        # Register connection with rate limiter
        if hasattr(self, '_rate_limiter'):
            await self._rate_limiter.on_connect(connection_id, client_ip, authenticated_user_id)
        
        # Add connection to token monitoring if authenticated with token
        if self.config.auth_required and not testing_mode and 'token' in kwargs:
            token = kwargs.get('token')
            if token and hasattr(self, '_token_refresh'):
                # Get user info with token expiry
                user_info = {
                    'user_id': authenticated_user_id,
                    'username': authenticated_username,
                    'token_exp': getattr(auth_result, 'user_info', {}).get('token_exp') if 'auth_result' in locals() else None
                }
                await self._token_refresh.add_connection(connection_id, token, user_info)
        
        # Notify extensions of new connection
        for ext_name, extension in self._registry.extensions.items():
            if self.config.is_extension_enabled(ext_name):
                try:
                    await extension.on_connect(connection_id, authenticated_user_id, authenticated_username, **kwargs)
                except Exception as e:
                    logger.error(f"Extension {ext_name} failed on_connect: {e}")
        
        self._metrics['connections_total'] += 1
        logger.info(f"Enhanced connection established: {connection_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Enhanced disconnect with extension notifications"""
        # Get connection info before disconnection
        connection = self._legacy_manager._connections.get(connection_id)
        if connection:
            user_id = connection.user_id
            username = connection.username
            
            # Remove from token monitoring
            if hasattr(self, '_token_refresh'):
                await self._token_refresh.remove_connection(connection_id)
            
            # Remove from rate limiter
            if hasattr(self, '_rate_limiter'):
                await self._rate_limiter.on_disconnect(connection_id)
            
            # Notify extensions of disconnection
            for ext_name, extension in self._registry.extensions.items():
                if self.config.is_extension_enabled(ext_name):
                    try:
                        await extension.on_disconnect(connection_id, user_id, username)
                    except Exception as e:
                        logger.error(f"Extension {ext_name} failed on_disconnect: {e}")
        
        # Use legacy manager for core disconnection
        await self._legacy_manager.disconnect(connection_id)
        logger.info(f"Enhanced disconnection complete: {connection_id}")
    
    async def handle_message(self, connection_id: str, message: dict):
        """Enhanced message handling with extension support"""
        try:
            # Check rate limiting
            if hasattr(self, '_rate_limiter'):
                allowed, reason = await self._rate_limiter.check_message_allowed(connection_id)
                if not allowed:
                    logger.warning(f"Message rejected by rate limiter for {connection_id}: {reason}")
                    await self._send_error(connection_id, f"Rate limit exceeded: {reason}")
                    return
                
                # Record message for rate limiting
                await self._rate_limiter.on_message(connection_id)
            
            # Update metrics
            self._metrics['messages_received'] += 1
            
            # Route through message router first
            routed = await self._message_router.route_message(connection_id, message, self)
            if routed:
                return
            
            # Check for extension handlers
            message_type = message.get("type")
            
            # Handle token refresh message
            if message_type == "token_refresh" and hasattr(self, '_token_refresh'):
                new_token = message.get("token")
                if new_token:
                    await self._token_refresh.handle_token_refreshed(connection_id, new_token)
                return
            
            if message_type:
                handlers = self._registry.get_message_handlers(message_type)
                for handler in handlers:
                    try:
                        await handler(connection_id, message, self)
                    except Exception as e:
                        logger.error(f"Extension handler failed for {message_type}: {e}")
                        self._metrics['errors_total'] += 1
                
                # If we have extension handlers, don't fall back to legacy
                if handlers:
                    return
            
            # Fall back to legacy manager
            await self._legacy_manager.handle_message(connection_id, message)
            
        except Exception as e:
            self._metrics['errors_total'] += 1
            
            # Get connection info for context
            connection = self._legacy_manager._connections.get(connection_id)
            user_id = connection.user_id if connection else None
            
            # Handle error with centralized handler
            error_response = await websocket_error_handler.handle_error(
                error=e,
                connection_id=connection_id,
                user_id=user_id,
                context={"message": message}
            )
            
            # Send error response to client
            await self._send_message(connection_id, error_response)
            
            # Check if connection should be closed
            if websocket_error_handler.should_close_connection(e):
                close_code = websocket_error_handler.get_close_code(e)
                logger.info(f"Closing connection {connection_id} due to error: {e}")
                # Note: Don't close here, let the route handler do it by raising
                raise WebSocketError(str(e), close_code)
    
    async def _send_message(self, connection_id: str, message: dict):
        """Send message to client (backward compatibility)"""
        return await self._legacy_manager._send_message(connection_id, message)
    
    async def _send_error(self, connection_id: str, error_message: str):
        """Send error message to client"""
        await self._legacy_manager._send_error(connection_id, error_message)
    
    # Delegate common operations to legacy manager for backward compatibility
    async def join_room(self, connection_id: str, room_id: str):
        """Join a room (backward compatibility)"""
        return await self._legacy_manager.join_room(connection_id, room_id)
    
    async def leave_room(self, connection_id: str, room_id: str):
        """Leave a room (backward compatibility)"""
        return await self._legacy_manager.leave_room(connection_id, room_id)
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_connection: Optional[str] = None):
        """Broadcast to room (backward compatibility)"""
        self._metrics['messages_sent'] += 1
        return await self._legacy_manager.broadcast_to_room(room_id, message, exclude_connection)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send to user (backward compatibility)"""
        self._metrics['messages_sent'] += 1
        return await self._legacy_manager.send_to_user(user_id, message)
    
    async def send_notification(self, user_id: str, notification: dict):
        """Send notification (backward compatibility)"""
        return await self._legacy_manager.send_notification(user_id, notification)
    
    def get_online_users(self) -> List[dict]:
        """Get online users (backward compatibility)"""
        return self._legacy_manager.get_online_users()
    
    def get_room_connections(self, room_id: str) -> List[str]:
        """Get room connections (backward compatibility)"""
        return self._legacy_manager.get_room_connections(room_id)
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user is online (backward compatibility)"""
        return self._legacy_manager.is_user_online(user_id)
    
    def get_connection_stats(self) -> dict:
        """Get enhanced connection statistics"""
        legacy_stats = self._legacy_manager.get_connection_stats()
        
        # Add extension metrics
        extension_stats = {}
        for ext_name, extension in self._registry.extensions.items():
            if hasattr(extension, 'get_stats'):
                try:
                    extension_stats[ext_name] = extension.get_stats()
                except Exception as e:
                    logger.error(f"Failed to get stats from extension {ext_name}: {e}")
                    extension_stats[ext_name] = {"error": str(e)}
        
        # Add rate limiter stats
        rate_limiter_stats = {}
        if hasattr(self, '_rate_limiter'):
            rate_limiter_stats = self._rate_limiter.get_stats()
        
        # Add error handler stats
        error_stats = websocket_error_handler.get_error_stats()
        
        return {
            **legacy_stats,
            'enhanced_metrics': self._metrics,
            'extensions': extension_stats,
            'extensions_count': len(self._registry.extensions),
            'handlers_count': len(self._registry.handlers),
            'rate_limiter': rate_limiter_stats,
            'error_handler': error_stats,
        }
    
    async def shutdown(self):
        """Enhanced shutdown with extension cleanup"""
        if self._shutdown_requested:
            return
        
        self._shutdown_requested = True
        logger.info("Shutting down enhanced WebSocket manager...")
        
        # Shutdown extensions in reverse priority order
        extensions = list(self._registry.extensions.items())
        extensions.reverse()
        
        for ext_name, extension in extensions:
            try:
                await extension.shutdown()
                logger.info(f"Extension {ext_name} shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down extension {ext_name}: {e}")
        
        # Shutdown token refresh manager
        if hasattr(self, '_token_refresh'):
            await self._token_refresh.shutdown()
        
        # Shutdown rate limiter
        if hasattr(self, '_rate_limiter'):
            await self._rate_limiter.stop()
        
        # Shutdown legacy manager
        await self._legacy_manager.shutdown()
        logger.info("Enhanced WebSocket manager shutdown complete")
    
    # Extension access methods
    def get_extension(self, name: str) -> Optional[BaseWrapper]:
        """Get a registered extension"""
        return self._registry.get_extension(name)
    
    def get_legacy_manager(self) -> LegacyWebSocketManager:
        """Get access to the legacy manager for advanced use cases"""
        return self._legacy_manager
    
    @property
    def _connections(self) -> Dict[str, Any]:
        """Access to legacy manager connections for backward compatibility"""
        return self._legacy_manager._connections
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self._metrics.copy()


# Create the singleton instance with environment configuration
websocket_manager = WebSocketManager(config=env_config)
logger.info(f"WebSocket singleton created with auth_required={websocket_manager.config.auth_required}")

# Cleanup function for application shutdown
async def cleanup_websocket_manager():
    """Cleanup function to be called on application shutdown"""
    await websocket_manager.shutdown()