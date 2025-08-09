"""
Validation utilities for the Collaboration microservice
"""

import re
from typing import Optional, List
from datetime import datetime


def validate_room_name(name: str) -> bool:
    """
    Validate room name
    - Must be 1-100 characters
    - Can contain letters, numbers, spaces, hyphens, and underscores
    - Cannot start or end with spaces
    """
    if not name or len(name) > 100:
        return False
    
    # Remove leading/trailing spaces
    name = name.strip()
    if not name:
        return False
    
    # Check for valid characters
    pattern = r'^[\w\s\-]+$'
    return bool(re.match(pattern, name))


def validate_message_content(content: str, max_length: int = 5000) -> bool:
    """
    Validate message content
    - Must not be empty
    - Must not exceed max length
    - Must contain at least one non-whitespace character
    """
    if not content:
        return False
    
    if len(content) > max_length:
        return False
    
    # Check if content has at least one non-whitespace character
    if not content.strip():
        return False
    
    return True


def validate_email(email: str) -> bool:
    """
    Validate email address format
    """
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format
    - Accepts international format with optional + prefix
    - Accepts numbers with spaces, hyphens, or parentheses
    """
    if not phone:
        return False
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Check if it starts with optional + and contains only digits
    pattern = r'^\+?\d{7,15}$'
    return bool(re.match(pattern, cleaned))


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength
    Returns (is_valid, error_message)
    
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        return False, "Password must contain at least one special character"
    
    return True, None


def validate_username(username: str) -> bool:
    """
    Validate username format
    - 3-30 characters long
    - Can contain letters, numbers, underscores, and hyphens
    - Must start with a letter
    """
    if not username or len(username) < 3 or len(username) > 30:
        return False
    
    pattern = r'^[a-zA-Z][a-zA-Z0-9_\-]*$'
    return bool(re.match(pattern, username))


def validate_url(url: str) -> bool:
    """
    Validate URL format
    """
    if not url:
        return False
    
    # Basic URL regex pattern
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    return bool(re.match(pattern, url))


def validate_datetime_range(
    start: datetime,
    end: datetime,
    max_duration_hours: Optional[int] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate datetime range
    Returns (is_valid, error_message)
    """
    if start >= end:
        return False, "Start time must be before end time"
    
    if start < datetime.utcnow():
        return False, "Start time cannot be in the past"
    
    if max_duration_hours:
        duration = (end - start).total_seconds() / 3600
        if duration > max_duration_hours:
            return False, f"Duration cannot exceed {max_duration_hours} hours"
    
    return True, None


def sanitize_html(content: str) -> str:
    """
    Basic HTML sanitization to prevent XSS
    This is a simple implementation - consider using a proper library like bleach
    """
    # Remove script tags
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove event handlers
    content = re.sub(r'\bon\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
    
    return content


def validate_file_extension(
    filename: str,
    allowed_extensions: List[str]
) -> bool:
    """
    Validate file extension against allowed list
    """
    if not filename:
        return False
    
    # Get file extension
    parts = filename.rsplit('.', 1)
    if len(parts) != 2:
        return False
    
    extension = parts[1].lower()
    return extension in [ext.lower() for ext in allowed_extensions]


def validate_file_size(size_bytes: int, max_size_mb: float = 10.0) -> bool:
    """
    Validate file size
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return 0 < size_bytes <= max_size_bytes


def validate_mentions(mentions: List[str]) -> List[str]:
    """
    Validate and clean mention list
    - Remove duplicates
    - Remove empty strings
    - Limit to reasonable number
    """
    if not mentions:
        return []
    
    # Clean and deduplicate
    cleaned = list(set(m.strip() for m in mentions if m and m.strip()))
    
    # Limit to 20 mentions
    return cleaned[:20]


def validate_emoji(emoji: str) -> bool:
    """
    Validate emoji string
    - Should be a single emoji or short emoji sequence
    """
    if not emoji:
        return False
    
    # Simple check - emoji should be 1-4 characters
    # (some emojis like flags are multiple characters)
    return 1 <= len(emoji) <= 4