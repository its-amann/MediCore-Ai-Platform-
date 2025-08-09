"""
Utility functions for Neo4j data handling
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def convert_neo4j_datetime(value: Any) -> str:
    """
    Convert Neo4j DateTime object to ISO string format
    
    Args:
        value: Neo4j DateTime object or string
        
    Returns:
        ISO formatted datetime string
    """
    if value is None:
        return None
    
    # Check if it's a Neo4j DateTime object
    if hasattr(value, 'iso_format'):
        return value.iso_format()
    elif hasattr(value, 'to_native'):
        # Convert to Python datetime then to ISO string
        native_dt = value.to_native()
        return native_dt.isoformat() if native_dt else None
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, str):
        return value
    else:
        # Try to convert to string as fallback
        return str(value)


def sanitize_neo4j_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize Neo4j record by converting DateTime objects to strings
    
    Args:
        record: Dictionary from Neo4j query result
        
    Returns:
        Sanitized dictionary with DateTime objects converted to strings
    """
    if not record:
        return record
    
    sanitized = {}
    
    for key, value in record.items():
        if value is None:
            sanitized[key] = None
        elif hasattr(value, 'iso_format') or hasattr(value, 'to_native'):
            # Neo4j DateTime object
            sanitized[key] = convert_neo4j_datetime(value)
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_neo4j_record(value)
        elif isinstance(value, list):
            # Handle lists (might contain DateTime objects)
            sanitized[key] = [
                sanitize_neo4j_record(item) if isinstance(item, dict) 
                else convert_neo4j_datetime(item) if hasattr(item, 'iso_format') or hasattr(item, 'to_native')
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


def ensure_user_fields(record: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
    """
    Ensure user ID field is properly populated
    
    Args:
        record: Report record from database
        user_id: Optional user ID to populate if missing
        
    Returns:
        Record with ensured user fields
    """
    # Ensure userId field exists
    if 'userId' not in record or not record['userId']:
        # Try to get from other fields
        if record.get('user_id'):
            record['userId'] = record['user_id']
        elif user_id:
            record['userId'] = user_id
        else:
            # This shouldn't happen but log it
            logger.warning(f"Report {record.get('id', 'unknown')} has no userId")
    
    return record