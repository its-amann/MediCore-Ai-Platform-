"""
Base WebSocket Handler

Abstract base class for WebSocket message handlers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """
    Abstract base class for WebSocket message handlers
    
    Handlers process specific types of WebSocket messages and can be
    registered with the WebSocket manager or extensions.
    """
    
    def __init__(self, name: str):
        """
        Initialize the handler
        
        Args:
            name: Unique name for this handler
        """
        self.name = name
        self.enabled = True
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def handle(self, connection_id: str, message: Dict[str, Any], manager) -> bool:
        """
        Handle a WebSocket message
        
        Args:
            connection_id: The connection ID that sent the message
            message: The message payload
            manager: The WebSocket manager instance
            
        Returns:
            bool: True if the message was handled, False to continue processing
        """
        pass
    
    @abstractmethod
    def can_handle(self, message_type: str) -> bool:
        """
        Check if this handler can process a message type
        
        Args:
            message_type: The type of message
            
        Returns:
            bool: True if this handler can process the message
        """
        pass
    
    async def on_connect(self, connection_id: str, user_id: str, username: str, **kwargs):
        """
        Called when a new connection is established
        
        Args:
            connection_id: The new connection ID
            user_id: User identifier
            username: Username
            **kwargs: Additional connection parameters
        """
        pass
    
    async def on_disconnect(self, connection_id: str, user_id: str, username: str):
        """
        Called when a connection is closed
        
        Args:
            connection_id: The closed connection ID
            user_id: User identifier
            username: Username
        """
        pass
    
    async def initialize(self, config: Dict[str, Any]):
        """
        Initialize the handler with configuration
        
        Args:
            config: Handler configuration
        """
        self.logger.info(f"Initializing handler: {self.name}")
    
    async def shutdown(self):
        """Shutdown the handler and cleanup resources"""
        self.logger.info(f"Shutting down handler: {self.name}")
    
    def get_supported_message_types(self) -> List[str]:
        """
        Get list of message types this handler supports
        
        Returns:
            List of supported message types
        """
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get handler statistics
        
        Returns:
            Dictionary of handler statistics
        """
        return {
            'name': self.name,
            'enabled': self.enabled,
            'supported_types': self.get_supported_message_types()
        }
    
    def enable(self):
        """Enable the handler"""
        self.enabled = True
        self.logger.info(f"Handler {self.name} enabled")
    
    def disable(self):
        """Disable the handler"""
        self.enabled = False
        self.logger.info(f"Handler {self.name} disabled")


class MessageTypeHandler(BaseHandler):
    """
    Handler that processes specific message types
    
    This is a convenience class for handlers that process one or more
    specific message types.
    """
    
    def __init__(self, name: str, message_types: List[str]):
        """
        Initialize the message type handler
        
        Args:
            name: Handler name
            message_types: List of message types to handle
        """
        super().__init__(name)
        self.message_types = set(message_types)
    
    def can_handle(self, message_type: str) -> bool:
        """Check if this handler can process a message type"""
        return message_type in self.message_types
    
    def get_supported_message_types(self) -> List[str]:
        """Get supported message types"""
        return list(self.message_types)
    
    def add_message_type(self, message_type: str):
        """Add a new message type to handle"""
        self.message_types.add(message_type)
        self.logger.info(f"Added message type {message_type} to handler {self.name}")
    
    def remove_message_type(self, message_type: str):
        """Remove a message type from handling"""
        self.message_types.discard(message_type)
        self.logger.info(f"Removed message type {message_type} from handler {self.name}")


class CompositeHandler(BaseHandler):
    """
    Handler that combines multiple handlers
    
    This handler can contain multiple child handlers and route messages
    to the appropriate child handler.
    """
    
    def __init__(self, name: str):
        """Initialize the composite handler"""
        super().__init__(name)
        self.child_handlers: Dict[str, BaseHandler] = {}
    
    def add_handler(self, handler: BaseHandler):
        """Add a child handler"""
        self.child_handlers[handler.name] = handler
        self.logger.info(f"Added child handler {handler.name} to {self.name}")
    
    def remove_handler(self, handler_name: str):
        """Remove a child handler"""
        if handler_name in self.child_handlers:
            del self.child_handlers[handler_name]
            self.logger.info(f"Removed child handler {handler_name} from {self.name}")
    
    def can_handle(self, message_type: str) -> bool:
        """Check if any child handler can process the message type"""
        return any(handler.can_handle(message_type) for handler in self.child_handlers.values())
    
    async def handle(self, connection_id: str, message: Dict[str, Any], manager) -> bool:
        """Route message to appropriate child handler"""
        if not self.enabled:
            return False
        
        message_type = message.get("type", "")
        
        for handler in self.child_handlers.values():
            if handler.enabled and handler.can_handle(message_type):
                try:
                    handled = await handler.handle(connection_id, message, manager)
                    if handled:
                        return True
                except Exception as e:
                    self.logger.error(f"Child handler {handler.name} failed: {e}")
        
        return False
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize all child handlers"""
        await super().initialize(config)
        
        for handler in self.child_handlers.values():
            try:
                await handler.initialize(config.get(handler.name, {}))
            except Exception as e:
                self.logger.error(f"Failed to initialize child handler {handler.name}: {e}")
    
    async def shutdown(self):
        """Shutdown all child handlers"""
        for handler in self.child_handlers.values():
            try:
                await handler.shutdown()
            except Exception as e:
                self.logger.error(f"Failed to shutdown child handler {handler.name}: {e}")
        
        await super().shutdown()
    
    def get_supported_message_types(self) -> List[str]:
        """Get all supported message types from child handlers"""
        types = set()
        for handler in self.child_handlers.values():
            types.update(handler.get_supported_message_types())
        return list(types)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get composite handler statistics"""
        stats = super().get_stats()
        stats['child_handlers'] = {
            name: handler.get_stats() 
            for name, handler in self.child_handlers.items()
        }
        return stats