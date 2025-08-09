"""
Medical Imaging Microservice
Handles medical image analysis, report generation, and embeddings
"""

__version__ = "1.0.0"

import os
from .models import *
from .services import *


def initialize_medical_imaging():
    """Initialize medical imaging microservice components"""
    try:
        from app.core.config import settings as main_settings
        from app.microservices.medical_imaging.utils.websocket_auth import init_websocket_auth
        
        # Use main app's JWT settings for consistency
        secret_key = main_settings.secret_key
        algorithm = main_settings.algorithm
        
        # Initialize WebSocket authentication
        init_websocket_auth(secret_key, algorithm)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Medical imaging initialized with main JWT settings")
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to initialize medical imaging: {e}")
        # Fall back to environment variables if main settings not available
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        
        from app.microservices.medical_imaging.utils.websocket_auth import init_websocket_auth
        init_websocket_auth(secret_key, algorithm)


__all__ = [
    "initialize_medical_imaging"
]