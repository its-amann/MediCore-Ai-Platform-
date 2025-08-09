"""
Case ID utilities for consistent ID handling across frontend and backend.

This module provides utilities to:
- Validate case IDs and case numbers
- Convert between internal IDs and case numbers
- Ensure API consistency
"""

import re
from typing import Optional, Tuple, Union
from functools import wraps
from fastapi import HTTPException, status


class CaseIDValidator:
    """Validator for case IDs and case numbers."""
    
    # Standard format: C{YYYYMMDD}{NNNNN}
    STANDARD_PATTERN = re.compile(r'^C\d{8}\d{5}$')
    
    # Legacy formats
    LEGACY_PATTERNS = [
        re.compile(r'^[A-Z]{3}-\d{8}-\d{4}$'),  # MED-20231231-0001
        re.compile(r'^CASE-\d{4}-\d{2}-\d{2}-\d{3}$'),  # CASE-2023-12-31-001
        re.compile(r'^\d{13}$'),  # 2023123100001
    ]
    
    # Internal ID format (UUID or similar)
    INTERNAL_ID_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$|^[a-zA-Z0-9_-]+$')
    
    @classmethod
    def is_case_number(cls, value: str) -> bool:
        """Check if value is a case number (standard or legacy format)."""
        if not value:
            return False
            
        # Check standard format
        if cls.STANDARD_PATTERN.match(value):
            return True
            
        # Check legacy formats
        for pattern in cls.LEGACY_PATTERNS:
            if pattern.match(value):
                return True
                
        return False
    
    @classmethod
    def is_internal_id(cls, value: str) -> bool:
        """Check if value is an internal ID."""
        if not value:
            return False
            
        # If it's a case number, it's not an internal ID
        if cls.is_case_number(value):
            return False
            
        # Check internal ID pattern
        return bool(cls.INTERNAL_ID_PATTERN.match(value))
    
    @classmethod
    def identify_id_type(cls, value: str) -> str:
        """
        Identify the type of ID.
        
        Returns:
            str: 'case_number', 'internal_id', or 'unknown'
        """
        if cls.is_case_number(value):
            return 'case_number'
        elif cls.is_internal_id(value):
            return 'internal_id'
        else:
            return 'unknown'


def validate_case_identifier(func):
    """
    Decorator to validate case identifiers in API endpoints.
    
    Expects the decorated function to have 'case_id' as first parameter after self.
    """
    @wraps(func)
    async def wrapper(self, case_id: str, *args, **kwargs):
        id_type = CaseIDValidator.identify_id_type(case_id)
        
        if id_type == 'unknown':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid case identifier format: {case_id}"
            )
        
        # Add id_type to kwargs for use in the function
        kwargs['_id_type'] = id_type
        
        return await func(self, case_id, *args, **kwargs)
    
    return wrapper


class CaseIDConverter:
    """Convert between different case ID formats."""
    
    def __init__(self, case_numbering_service):
        """
        Initialize with a CaseNumberingService instance.
        
        Args:
            case_numbering_service: Instance of CaseNumberingService
        """
        self.service = case_numbering_service
    
    async def to_standard_format(self, case_id: str) -> Tuple[str, str]:
        """
        Convert any case identifier to standard format.
        
        Args:
            case_id: Case number or internal ID
            
        Returns:
            tuple: (internal_id, case_number)
        """
        return await self.service.translate_case_id(case_id)
    
    async def ensure_case_number(self, case_id: str) -> str:
        """
        Ensure we have a case number, converting if necessary.
        
        Args:
            case_id: Case number or internal ID
            
        Returns:
            str: Case number
        """
        if CaseIDValidator.is_case_number(case_id):
            return case_id
        
        _, case_number = await self.to_standard_format(case_id)
        return case_number
    
    async def ensure_internal_id(self, case_id: str) -> str:
        """
        Ensure we have an internal ID, converting if necessary.
        
        Args:
            case_id: Case number or internal ID
            
        Returns:
            str: Internal ID
        """
        if CaseIDValidator.is_internal_id(case_id):
            return case_id
        
        internal_id, _ = await self.to_standard_format(case_id)
        return internal_id


class APIResponseNormalizer:
    """Normalize API responses to include both ID formats."""
    
    @staticmethod
    def normalize_case_response(
        case_data: dict,
        include_internal_id: bool = True,
        include_case_number: bool = True
    ) -> dict:
        """
        Normalize case response to include consistent ID fields.
        
        Args:
            case_data: Raw case data
            include_internal_id: Whether to include internal ID
            include_case_number: Whether to include case number
            
        Returns:
            dict: Normalized case data
        """
        normalized = case_data.copy()
        
        # Ensure consistent field names
        if 'id' in normalized and include_internal_id:
            normalized['internal_id'] = normalized.get('id')
        
        if 'case_number' in normalized and include_case_number:
            # Ensure case_number is present and properly formatted
            pass
        
        # Add display fields
        if 'case_number' in normalized:
            normalized['display_id'] = normalized['case_number']
            normalized['formatted_case_number'] = CaseIDFormatter.format_for_display(
                normalized['case_number']
            )
        
        return normalized
    
    @staticmethod
    def normalize_case_list(
        cases: list,
        include_internal_id: bool = False,
        include_case_number: bool = True
    ) -> list:
        """
        Normalize a list of cases.
        
        Args:
            cases: List of case data
            include_internal_id: Whether to include internal IDs
            include_case_number: Whether to include case numbers
            
        Returns:
            list: Normalized cases
        """
        return [
            APIResponseNormalizer.normalize_case_response(
                case,
                include_internal_id,
                include_case_number
            )
            for case in cases
        ]


class CaseIDFormatter:
    """Format case IDs for display."""
    
    @staticmethod
    def format_for_display(case_number: str) -> str:
        """
        Format case number for user-friendly display.
        
        Examples:
            C2023123100001 -> C-20231231-00001
            
        Args:
            case_number: Standard format case number
            
        Returns:
            str: Formatted case number
        """
        if not case_number or not case_number.startswith('C'):
            return case_number
        
        # Extract components
        if len(case_number) == 14:  # C + YYYYMMDD + NNNNN
            prefix = case_number[0]
            date = case_number[1:9]
            sequence = case_number[9:]
            
            # Format date
            year = date[:4]
            month = date[4:6]
            day = date[6:8]
            
            return f"{prefix}-{year}{month}{day}-{sequence}"
        
        return case_number
    
    @staticmethod
    def format_for_search(case_number: str) -> str:
        """
        Format case number for search (remove formatting).
        
        Examples:
            C-20231231-00001 -> C2023123100001
            
        Args:
            case_number: Formatted case number
            
        Returns:
            str: Standard format case number
        """
        if not case_number:
            return case_number
        
        # Remove all non-alphanumeric characters
        return re.sub(r'[^A-Z0-9]', '', case_number.upper())


# Middleware for automatic case ID handling
class CaseIDMiddleware:
    """Middleware to automatically handle case ID conversions in requests."""
    
    def __init__(self, case_numbering_service):
        self.converter = CaseIDConverter(case_numbering_service)
    
    async def process_request(self, request_data: dict) -> dict:
        """
        Process request data to handle case IDs.
        
        Args:
            request_data: Incoming request data
            
        Returns:
            dict: Processed request data
        """
        # Look for case_id fields and ensure they're in the correct format
        if 'case_id' in request_data:
            case_id = request_data['case_id']
            
            # If the endpoint expects internal IDs, convert case numbers
            if CaseIDValidator.is_case_number(case_id):
                request_data['case_id'] = await self.converter.ensure_internal_id(case_id)
                request_data['case_number'] = case_id
            
        return request_data
    
    async def process_response(self, response_data: Union[dict, list]) -> Union[dict, list]:
        """
        Process response data to include both ID formats.
        
        Args:
            response_data: Outgoing response data
            
        Returns:
            Processed response data
        """
        if isinstance(response_data, dict):
            return APIResponseNormalizer.normalize_case_response(response_data)
        elif isinstance(response_data, list):
            return APIResponseNormalizer.normalize_case_list(response_data)
        
        return response_data


# Export main components
__all__ = [
    'CaseIDValidator',
    'CaseIDConverter',
    'APIResponseNormalizer',
    'CaseIDFormatter',
    'CaseIDMiddleware',
    'validate_case_identifier'
]