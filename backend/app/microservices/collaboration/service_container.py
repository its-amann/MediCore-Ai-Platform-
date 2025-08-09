"""
Service Container for Collaboration Microservice
Provides dependency injection and service lifecycle management
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """
    Service container for managing microservice dependencies and lifecycle.
    Provides a centralized location for service registration and retrieval.
    """
    
    def __init__(self):
        """Initialize the service container"""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._initialized = False
        self._config: Dict[str, Any] = {}
        
    def register(self, name: str, service: Any) -> None:
        """
        Register a service instance
        
        Args:
            name: Service name/identifier
            service: Service instance
        """
        self._services[name] = service
        logger.debug(f"Registered service: {name}")
        
    def register_factory(self, name: str, factory: callable) -> None:
        """
        Register a service factory for lazy initialization
        
        Args:
            name: Service name/identifier
            factory: Callable that returns the service instance
        """
        self._factories[name] = factory
        logger.debug(f"Registered factory for service: {name}")
        
    def get(self, name: str, service_type: Optional[Type[T]] = None) -> Optional[T]:
        """
        Get a service by name
        
        Args:
            name: Service name/identifier
            service_type: Optional type hint for better IDE support
            
        Returns:
            Service instance or None if not found
        """
        # Check if service is already instantiated
        if name in self._services:
            return self._services[name]
            
        # Check if we have a factory for this service
        if name in self._factories:
            try:
                service = self._factories[name]()
                self._services[name] = service
                logger.debug(f"Created service from factory: {name}")
                return service
            except Exception as e:
                logger.error(f"Failed to create service {name} from factory: {e}")
                return None
                
        logger.warning(f"Service not found: {name}")
        return None
        
    def get_required(self, name: str, service_type: Optional[Type[T]] = None) -> T:
        """
        Get a required service by name (raises exception if not found)
        
        Args:
            name: Service name/identifier
            service_type: Optional type hint for better IDE support
            
        Returns:
            Service instance
            
        Raises:
            RuntimeError: If service is not found
        """
        service = self.get(name, service_type)
        if service is None:
            raise RuntimeError(f"Required service not found: {name}")
        return service
        
    def has(self, name: str) -> bool:
        """
        Check if a service is registered
        
        Args:
            name: Service name/identifier
            
        Returns:
            True if service is registered, False otherwise
        """
        return name in self._services or name in self._factories
        
    def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
        
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize all services with optional configuration
        
        Args:
            config: Optional configuration dictionary
        """
        if self._initialized:
            logger.warning("Service container already initialized")
            return
            
        # Set configuration
        if config:
            self._config.update(config)
            
        # Initialize services that need async initialization
        for name, service in self._services.items():
            if hasattr(service, 'initialize') and callable(getattr(service, 'initialize')):
                try:
                    await service.initialize()
                    logger.info(f"Initialized service: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize service {name}: {e}")
                    raise
                    
        self._initialized = True
        logger.info("Service container initialized successfully")
        
    async def shutdown(self) -> None:
        """
        Shutdown all services gracefully
        """
        if not self._initialized:
            return
            
        # Shutdown services in reverse order
        for name, service in reversed(list(self._services.items())):
            if hasattr(service, 'shutdown') and callable(getattr(service, 'shutdown')):
                try:
                    await service.shutdown()
                    logger.info(f"Shutdown service: {name}")
                except Exception as e:
                    logger.error(f"Error shutting down service {name}: {e}")
                    
        self._initialized = False
        logger.info("Service container shutdown complete")
        
    def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on all services
        
        Returns:
            Dictionary with service names as keys and health status as values
        """
        health_status = {}
        
        for name, service in self._services.items():
            try:
                if hasattr(service, 'health_check') and callable(getattr(service, 'health_check')):
                    health_status[name] = service.health_check()
                elif hasattr(service, 'is_connected') and callable(getattr(service, 'is_connected')):
                    health_status[name] = service.is_connected()
                else:
                    # Assume service is healthy if no health check method
                    health_status[name] = True
            except Exception as e:
                logger.error(f"Health check failed for service {name}: {e}")
                health_status[name] = False
                
        return health_status
        
    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._factories.clear()
        self._config.clear()
        self._initialized = False
    
    # Convenience methods for getting specific services
    
    def get_room_service(self):
        """Get the room service instance"""
        return self.get('room_service')
    
    def get_chat_service(self):
        """Get the chat service instance"""
        return self.get('chat_service')
    
    def get_notification_service(self):
        """Get the notification service instance"""
        return self.get('notification_service')
    
    def get_user_service(self):
        """Get the user service instance"""
        return self.get('user_service')
    
    def get_screen_share_service(self):
        """Get the screen share service instance"""
        return self.get('screen_share_service')
    
    def get_webrtc_service(self):
        """Get the WebRTC service instance"""
        return self.get('webrtc_service')
    
    def get_video_service(self):
        """Get the video service instance"""
        return self.get('video_service')
    
    def get_websocket_manager(self):
        """Get the WebSocket manager instance"""
        return self.get('websocket_manager')
    
    def get_db_client(self):
        """Get the database client instance"""
        return self.get('db_client')
    
    @classmethod
    def get_instance(cls) -> 'ServiceContainer':
        """Get the global service container instance"""
        return service_container
        

# Global service container instance
service_container = ServiceContainer()


@asynccontextmanager
async def managed_service_container(config: Optional[Dict[str, Any]] = None):
    """
    Context manager for service container lifecycle
    
    Args:
        config: Optional configuration dictionary
        
    Example:
        async with managed_service_container({'debug': True}) as container:
            service = container.get('my_service')
            # Use service...
    """
    try:
        await service_container.initialize(config)
        yield service_container
    finally:
        await service_container.shutdown()