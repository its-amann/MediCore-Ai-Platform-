"""
Authentication utilities for the collaboration microservice

This module now uses the shared authentication dependencies for consistency
across all microservices.
"""

from typing import Dict, Any, Optional
import logging

# Import all shared authentication dependencies
from app.core.auth.shared_dependencies import (
    get_current_user,
    get_current_user_id,
    get_current_username,
    get_optional_user,
    require_role,
    get_admin_user,
    security
)

logger = logging.getLogger(__name__)

# Re-export all shared dependencies for backward compatibility
__all__ = [
    'get_current_user',
    'get_current_user_id', 
    'get_current_username',
    'get_optional_user',
    'require_role',
    'get_admin_user',
    'security'
]

# Additional collaboration-specific authentication helpers can be added here if needed