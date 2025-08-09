"""
Service Container - Centralized dependency injection and service management
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar, Callable
from threading import Lock
import asyncio

from app.microservices.cases_chat.services.neo4j_storage.unified_cases_chat_storage import UnifiedCasesChatStorage
from app.api.dependencies.database import get_sync_driver
from app.microservices.cases_chat.services.groq_doctors.doctor_service import DoctorService
from app.microservices.cases_chat.services.media_handler.media_handler import MediaHandler
from app.microservices.cases_chat.services.case_numbering.case_number_generator import CaseNumberGenerator
from app.microservices.cases_chat.websocket_adapter import CasesChatWebSocketAdapter

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """
    Centralized service container implementing singleton pattern for all services.
    Provides lazy initialization, thread-safe access, and lifecycle management.
    """
    
    _instance: Optional['ServiceContainer'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'ServiceContainer':
        """Thread-safe singleton implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the service container"""
        if not hasattr(self, '_initialized'):
            self._services: Dict[str, Any] = {}
            self._factories: Dict[str, Callable[[], Any]] = {}
            self._service_lock = Lock()
            self._initialized = True
            self._register_default_factories()
            logger.info("Service container initialized")
    
    def _register_default_factories(self):
        """Register default service factories"""
        # Storage service factory
        self._factories['storage'] = lambda: UnifiedCasesChatStorage(get_sync_driver())
        
        # Doctor service factory
        self._factories['doctor'] = lambda: DoctorService()
        
        # Media handler factory
        self._factories['media'] = lambda: MediaHandler()
        
        # Case number generator factory
        self._factories['case_number'] = self._create_case_number_generator
        
        # WebSocket adapter factory
        self._factories['websocket'] = lambda: CasesChatWebSocketAdapter()
    
    def _create_case_number_generator(self) -> CaseNumberGenerator:
        """Create case number generator with driver dependency"""
        driver = get_sync_driver()
        return CaseNumberGenerator(driver)
    
    def register_factory(self, name: str, factory: Callable[[], T]):
        """
        Register a service factory
        
        Args:
            name: Service name
            factory: Factory function that creates the service
        """
        with self._service_lock:
            self._factories[name] = factory
            logger.info(f"Registered factory for service: {name}")
    
    def register_service(self, name: str, service: T):
        """
        Register a service instance directly
        
        Args:
            name: Service name
            service: Service instance
        """
        with self._service_lock:
            self._services[name] = service
            logger.info(f"Registered service instance: {name}")
    
    def get_service(self, name: str, service_type: Optional[Type[T]] = None) -> T:
        """
        Get a service by name with lazy initialization
        
        Args:
            name: Service name
            service_type: Optional type hint for better IDE support
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service is not registered
        """
        with self._service_lock:
            # Return existing service if available
            if name in self._services:
                return self._services[name]
            
            # Create service using factory if available
            if name in self._factories:
                logger.info(f"Creating service: {name}")
                service = self._factories[name]()
                self._services[name] = service
                return service
            
            raise ValueError(f"Service '{name}' not registered")
    
    def has_service(self, name: str) -> bool:
        """Check if a service is registered"""
        return name in self._services or name in self._factories
    
    def reset_service(self, name: str):
        """Reset a specific service (useful for testing)"""
        with self._service_lock:
            if name in self._services:
                # Attempt to close/cleanup the service if possible
                service = self._services[name]
                if hasattr(service, 'close'):
                    try:
                        service.close()
                    except Exception as e:
                        logger.warning(f"Error closing service {name}: {e}")
                
                del self._services[name]
                logger.info(f"Reset service: {name}")
    
    def reset_all(self):
        """Reset all services (useful for testing)"""
        with self._service_lock:
            # Close all services that support it
            for name, service in self._services.items():
                if hasattr(service, 'close'):
                    try:
                        service.close()
                    except Exception as e:
                        logger.warning(f"Error closing service {name}: {e}")
            
            self._services.clear()
            logger.info("Reset all services")
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)"""
        with cls._lock:
            if cls._instance:
                cls._instance.reset_all()
            cls._instance = None
    
    # Convenience methods for common services
    
    def get_storage_service(self) -> UnifiedCasesChatStorage:
        """Get the storage service"""
        return self.get_service('storage', UnifiedCasesChatStorage)
    
    def get_doctor_service(self) -> DoctorService:
        """Get the doctor service"""
        return self.get_service('doctor', DoctorService)
    
    def get_media_handler(self) -> MediaHandler:
        """Get the media handler"""
        return self.get_service('media', MediaHandler)
    
    def get_case_number_generator(self) -> CaseNumberGenerator:
        """Get the case number generator"""
        return self.get_service('case_number', CaseNumberGenerator)
    
    def get_websocket_adapter(self) -> CasesChatWebSocketAdapter:
        """Get the WebSocket adapter"""
        return self.get_service('websocket', CasesChatWebSocketAdapter)
    
    async def close_async_services(self):
        """Close all async services properly"""
        with self._service_lock:
            for name, service in self._services.items():
                if hasattr(service, 'close_async'):
                    try:
                        await service.close_async()
                        logger.info(f"Closed async service: {name}")
                    except Exception as e:
                        logger.error(f"Error closing async service {name}: {e}")
                elif hasattr(service, 'close'):
                    try:
                        # Try to close sync services
                        if asyncio.iscoroutinefunction(service.close):
                            await service.close()
                        else:
                            service.close()
                        logger.info(f"Closed service: {name}")
                    except Exception as e:
                        logger.error(f"Error closing service {name}: {e}")


# Global service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """Get the global service container instance"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
    return _service_container


# Convenience functions for direct service access
def get_storage_service() -> UnifiedCasesChatStorage:
    """Get the storage service from the global container"""
    return get_service_container().get_storage_service()


def get_doctor_service() -> DoctorService:
    """Get the doctor service from the global container"""
    return get_service_container().get_doctor_service()


def get_media_handler() -> MediaHandler:
    """Get the media handler from the global container"""
    return get_service_container().get_media_handler()


def get_case_number_generator() -> CaseNumberGenerator:
    """Get the case number generator from the global container"""
    return get_service_container().get_case_number_generator()


def get_websocket_adapter() -> CasesChatWebSocketAdapter:
    """Get the WebSocket adapter from the global container"""
    return get_service_container().get_websocket_adapter()