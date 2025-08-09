"""
Core components for Cases Chat microservice
"""

from .service_container import (
    ServiceContainer,
    get_service_container,
    get_storage_service,
    get_doctor_service,
    get_media_handler,
    get_case_number_generator,
    get_websocket_adapter
)

__all__ = [
    'ServiceContainer',
    'get_service_container',
    'get_storage_service',
    'get_doctor_service',
    'get_media_handler',
    'get_case_number_generator',
    'get_websocket_adapter'
]