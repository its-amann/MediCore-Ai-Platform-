"""
Core Authentication Module

Provides unified authentication utilities for the entire application.
"""

from .token_validator import (
    UnifiedTokenValidator,
    TokenValidationResult,
    token_validator
)

from .shared_dependencies import (
    get_current_user,
    get_current_user_id,
    get_current_username,
    get_optional_user,
    require_role,
    get_admin_user,
    get_doctor_user,
    get_patient_user
)

__all__ = [
    'UnifiedTokenValidator',
    'TokenValidationResult',
    'token_validator',
    'get_current_user',
    'get_current_user_id',
    'get_current_username',
    'get_optional_user',
    'require_role',
    'get_admin_user',
    'get_doctor_user',
    'get_patient_user'
]