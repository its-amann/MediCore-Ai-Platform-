"""
Base WebSocket Extension Wrapper

Abstract base class for WebSocket extensions that wrap microservice functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import logging
import asyncio

if TYPE_CHECKING:
    from ..manager import WebSocketManager

logger = logging.getLogger(__name__)


class BaseWrapper(ABC):
    """
    Abstract base class for WebSocket extensions
    
    Extensions provide specialized WebSocket functionality for microservices
    while integrating with the unified WebSocket architecture.
    """
    
    def __init__(self, name: str, priority: int = 100):
        """
        Initialize the extension wrapper
        
        Args:
            name: Unique name for this extension
            priority: Extension priority (lower = higher priority)
        """
        self.name = name
        self.priority = priority
        self.enabled = True
        self.initialized = False
        self.manager: Optional['WebSocketManager'] = None
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Extension metrics
        self._metrics = {
            'connections_handled': 0,
            'messages_processed': 0,
            'errors_count': 0,
            'last_activity': None
        }
    
    def set_manager(self, manager: 'WebSocketManager'):
        """Set the WebSocket manager reference"""
        self.manager = manager
        self.logger.info(f"Extension {self.name} attached to manager")
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]):
        """
        Initialize the extension with configuration
        
        Args:
            config: Extension configuration
        """
        self.config = config
        self.initialized = True
        self.logger.info(f"Extension {self.name} initialized")
    
    @abstractmethod
    async def shutdown(self):
        """Shutdown the extension and cleanup resources"""
        self.enabled = False
        self.initialized = False
        self.logger.info(f"Extension {self.name} shutdown")
    
    async def on_connect(self, connection_id: str, user_id: str, username: str, **kwargs):
        """
        Called when a new WebSocket connection is established
        
        Args:
            connection_id: The new connection ID
            user_id: User identifier
            username: Username
            **kwargs: Additional connection parameters
        """
        if not self.enabled or not self.initialized:
            return
        
        self._metrics['connections_handled'] += 1
        self._update_activity()
        self.logger.debug(f"Connection event for {connection_id}")
    
    async def on_disconnect(self, connection_id: str, user_id: str, username: str):
        """
        Called when a WebSocket connection is closed
        
        Args:
            connection_id: The closed connection ID
            user_id: User identifier
            username: Username
        """
        if not self.enabled or not self.initialized:
            return
        
        self._update_activity()
        self.logger.debug(f"Disconnection event for {connection_id}")
    
    async def on_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Called when a WebSocket message is received
        
        Args:
            connection_id: The connection ID that sent the message
            message: The message payload
            
        Returns:
            bool: True if the message was handled, False otherwise
        """
        if not self.enabled or not self.initialized:
            return False
        
        message_type = message.get("type", "")
        
        if self.can_handle_message(message_type):
            try:
                self._metrics['messages_processed'] += 1
                self._update_activity()
                return await self.handle_message(connection_id, message)
            except Exception as e:
                self._metrics['errors_count'] += 1
                self.logger.error(f"Error handling message {message_type}: {e}")
                return False
        
        return False
    
    @abstractmethod
    def can_handle_message(self, message_type: str) -> bool:
        """
        Check if this extension can handle a message type
        
        Args:
            message_type: The type of message
            
        Returns:
            bool: True if this extension can handle the message
        """
        pass
    
    @abstractmethod
    async def handle_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Handle a WebSocket message
        
        Args:
            connection_id: The connection ID that sent the message
            message: The message payload
            
        Returns:
            bool: True if the message was handled successfully
        """
        pass
    
    def get_supported_message_types(self) -> List[str]:
        """
        Get list of message types this extension supports
        
        Returns:
            List of supported message types
        """
        return []
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific connection
        
        Args:
            connection_id: Target connection ID
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        if not self.manager:
            self.logger.error("No manager reference available")
            return False
        
        try:
            legacy_manager = self.manager.get_legacy_manager()
            return await legacy_manager._send_message(connection_id, message)
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """
        Broadcast a message to all connections in a room
        
        Args:
            room_id: Target room ID
            message: Message to broadcast
            exclude_connection: Connection ID to exclude from broadcast
        """
        if not self.manager:
            self.logger.error("No manager reference available")
            return
        
        try:
            await self.manager.broadcast_to_room(room_id, message, exclude_connection)
        except Exception as e:
            self.logger.error(f"Failed to broadcast to room {room_id}: {e}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """
        Send a message to all connections of a specific user
        
        Args:
            user_id: Target user ID
            message: Message to send
        """
        if not self.manager:
            self.logger.error("No manager reference available")
            return
        
        try:
            await self.manager.send_to_user(user_id, message)
        except Exception as e:
            self.logger.error(f"Failed to send to user {user_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get extension statistics
        
        Returns:
            Dictionary of extension statistics
        """
        return {
            'name': self.name,
            'enabled': self.enabled,
            'initialized': self.initialized,
            'priority': self.priority,
            'supported_types': self.get_supported_message_types(),
            'metrics': self._metrics.copy()
        }
    
    def enable(self):
        """Enable the extension"""
        self.enabled = True
        self.logger.info(f"Extension {self.name} enabled")
    
    def disable(self):
        """Disable the extension"""
        self.enabled = False
        self.logger.info(f"Extension {self.name} disabled")
    
    def _update_activity(self):
        """Update last activity timestamp"""
        from datetime import datetime
        self._metrics['last_activity'] = datetime.utcnow().isoformat()
    
    # Utility methods for subclasses
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection"""
        if not self.manager:
            return None
        
        legacy_manager = self.manager.get_legacy_manager()
        return legacy_manager._connections.get(connection_id)
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if a user is online"""
        if not self.manager:
            return False
        
        return self.manager.is_user_online(user_id)
    
    def get_room_connections(self, room_id: str) -> List[str]:
        """Get connections in a room"""
        if not self.manager:
            return []
        
        return self.manager.get_room_connections(room_id)


class MicroserviceWrapper(BaseWrapper):
    """
    Base wrapper for microservice integrations
    
    This class provides common functionality for wrapping existing
    microservice WebSocket managers.
    """
    
    def __init__(self, name: str, microservice_manager, priority: int = 100):
        """
        Initialize the microservice wrapper
        
        Args:
            name: Extension name
            microservice_manager: The microservice's WebSocket manager
            priority: Extension priority
        """
        super().__init__(name, priority)
        self.microservice_manager = microservice_manager
        self._message_type_mapping: Dict[str, str] = {}
    
    def add_message_type_mapping(self, unified_type: str, microservice_type: str):
        """
        Add a mapping from unified message type to microservice message type
        
        Args:
            unified_type: Message type in the unified system
            microservice_type: Message type in the microservice
        """
        self._message_type_mapping[unified_type] = microservice_type
        self.logger.debug(f"Added message type mapping: {unified_type} -> {microservice_type}")
    
    def translate_message_type(self, message_type: str) -> str:
        """
        Translate message type from unified to microservice format
        
        Args:
            message_type: Unified message type
            
        Returns:
            Microservice message type
        """
        return self._message_type_mapping.get(message_type, message_type)
    
    async def forward_to_microservice(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Forward a message to the microservice manager
        
        Args:
            connection_id: Connection ID
            message: Message to forward
            
        Returns:
            bool: True if forwarded successfully
        """
        try:
            # Translate message type if needed
            original_type = message.get("type", "")
            translated_type = self.translate_message_type(original_type)
            
            if translated_type != original_type:
                message = message.copy()
                message["type"] = translated_type
            
            # Forward to microservice
            if hasattr(self.microservice_manager, 'handle_message'):
                await self.microservice_manager.handle_message(connection_id, message)
                return True
            
            self.logger.warning(f"Microservice manager has no handle_message method")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to forward message to microservice: {e}")
            return False


class AsyncEventWrapper(BaseWrapper):
    """
    Wrapper that handles events asynchronously with queuing
    
    This wrapper can queue messages and events for processing to avoid
    blocking the main WebSocket message loop.
    """
    
    def __init__(self, name: str, max_queue_size: int = 1000, priority: int = 100):
        """
        Initialize the async event wrapper
        
        Args:
            name: Extension name
            max_queue_size: Maximum size of the event queue
            priority: Extension priority
        """
        super().__init__(name, priority)
        self.max_queue_size = max_queue_size
        self._event_queue: Optional[asyncio.Queue] = None
        self._processor_task: Optional[asyncio.Task] = None
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize the async wrapper with event processing"""
        await super().initialize(config)
        
        # Create event queue and start processor
        self._event_queue = asyncio.Queue(maxsize=self.max_queue_size)
        self._processor_task = asyncio.create_task(self._process_events())
        
        self.logger.info(f"Async event processor started for {self.name}")
    
    async def shutdown(self):
        """Shutdown the async wrapper and stop event processing"""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        await super().shutdown()
        self.logger.info(f"Async event processor stopped for {self.name}")
    
    async def queue_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Queue an event for asynchronous processing
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        if not self._event_queue:
            self.logger.warning("Event queue not initialized")
            return
        
        try:
            event = {
                'type': event_type,
                'data': event_data,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            await self._event_queue.put(event)
            self.logger.debug(f"Queued event: {event_type}")
            
        except asyncio.QueueFull:
            self.logger.warning(f"Event queue full, dropping event: {event_type}")
            self._metrics['errors_count'] += 1
    
    async def _process_events(self):
        """Process events from the queue"""
        while self.enabled and self.initialized:
            try:
                if not self._event_queue:
                    break
                
                # Get event with timeout
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                # Process the event
                await self.process_event(event)
                
            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
                self._metrics['errors_count'] += 1
    
    @abstractmethod
    async def process_event(self, event: Dict[str, Any]):
        """
        Process a queued event
        
        Args:
            event: Event to process
        """
        pass