"""
WebSocket Extensions Package

This package contains extensions that provide specialized WebSocket functionality
for different microservices and use cases.
"""

from .base_wrapper import BaseWrapper

# Note: Specific wrappers (CollaborationWrapper, MedicalImagingWrapper, etc.) 
# are not imported here to avoid circular dependencies.
# They should be imported directly when needed.

__all__ = [
    'BaseWrapper'
]