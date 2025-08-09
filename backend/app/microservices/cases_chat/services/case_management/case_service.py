"""
Case management service
"""
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from ...models.case_models import CaseResponse, CaseCreate, CaseUpdate
from ..storage.neo4j_storage import UnifiedNeo4jStorage
from ...core.exceptions import ValidationError, CaseNotFoundError

logger = logging.getLogger(__name__)


class CaseService:
    """Service for managing medical cases"""
    
    def __init__(self, storage: UnifiedNeo4jStorage):
        self.storage = storage
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the case service"""
        self.initialized = True
        logger.info("Case service initialized")
    
    async def create_case(self, case_data: CaseCreate) -> CaseResponse:
        """
        Create a new case with validation
        
        Args:
            case_data: Case creation data
            
        Returns:
            Created case
        """
        # Validate case data
        self._validate_case_data(case_data)
        
        # Create case in storage
        case = await self.storage.create_case(case_data)
        
        logger.info(f"Created case {case.id} with number {case.case_number}")
        return case
    
    async def get_case(self, case_id: str) -> CaseResponse:
        """
        Get a case by ID
        
        Args:
            case_id: Case ID
            
        Returns:
            Case object
            
        Raises:
            CaseNotFoundError: If case not found
        """
        case = await self.storage.get_case(case_id)
        if not case:
            raise CaseNotFoundError(case_id)
        return case
    
    async def update_case(self, case_id: str, update_data: CaseUpdate) -> CaseResponse:
        """
        Update a case
        
        Args:
            case_id: Case ID
            update_data: Update data
            
        Returns:
            Updated case
            
        Raises:
            CaseNotFoundError: If case not found
        """
        # Check if case exists
        existing_case = await self.storage.get_case(case_id)
        if not existing_case:
            raise CaseNotFoundError(case_id)
        
        # Validate update data
        self._validate_update_data(update_data, existing_case)
        
        # Update case
        updated_case = await self.storage.update_case(case_id, update_data)
        if not updated_case:
            raise CaseNotFoundError(case_id)
        
        logger.info(f"Updated case {case_id}")
        return updated_case
    
    async def delete_case(self, case_id: str, permanent: bool = False) -> bool:
        """
        Delete or archive a case
        
        Args:
            case_id: Case ID
            permanent: If true, permanently delete. Otherwise, archive.
            
        Returns:
            Success status
        """
        if permanent:
            success = await self.storage.delete_case(case_id)
            if success:
                logger.info(f"Permanently deleted case {case_id}")
        else:
            success = await self.storage.archive_case(case_id)
            if success:
                logger.info(f"Archived case {case_id}")
        
        return success
    
    async def search_cases(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[CaseResponse], int]:
        """
        Search cases
        
        Args:
            query: Search query
            filters: Optional filters
            skip: Number of results to skip
            limit: Maximum results to return
            
        Returns:
            Tuple of (cases, total count)
        """
        return await self.storage.search_cases(query, filters, skip, limit)
    
    async def generate_case_number(self, patient_id: str) -> str:
        """
        Generate a unique case number
        
        Args:
            patient_id: Patient ID (for potential custom numbering schemes)
            
        Returns:
            Generated case number
        """
        # Get next case number from storage
        case_number = await self.storage.get_next_case_number()
        
        # Ensure uniqueness
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            exists = await self.storage.check_case_number_exists(case_number)
            if not exists:
                return case_number
            
            # Generate new number if exists
            attempt += 1
            # Add suffix for uniqueness
            case_number = f"{case_number}-{attempt}"
        
        raise ValidationError(f"Failed to generate unique case number after {max_attempts} attempts")
    
    async def get_case_statistics(self, case_id: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a case
        
        Args:
            case_id: Case ID
            
        Returns:
            Case statistics
        """
        stats = await self.storage.get_case_statistics(case_id)
        
        # Add calculated metrics
        if stats.get("created_at") and stats.get("last_message_time"):
            created_at = datetime.fromisoformat(stats["created_at"])
            last_message = datetime.fromisoformat(stats["last_message_time"])
            stats["duration_hours"] = (last_message - created_at).total_seconds() / 3600
        
        # Add response rate
        if stats.get("message_count", 0) > 0 and stats.get("has_doctor_response"):
            # Rough estimate - could be refined with actual counting
            stats["response_rate"] = 0.5  # Assuming 50% are doctor responses
        else:
            stats["response_rate"] = 0
        
        return stats
    
    def _validate_case_data(self, case_data: CaseCreate) -> None:
        """
        Validate case creation data
        
        Args:
            case_data: Case data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields
        if not case_data.title or not case_data.title.strip():
            raise ValidationError("Case title is required")
        
        if not case_data.description or not case_data.description.strip():
            raise ValidationError("Case description is required")
        
        if not case_data.patient_id:
            raise ValidationError("Patient ID is required")
        
        # Validate age if provided
        if case_data.patient_age is not None:
            if case_data.patient_age < 0 or case_data.patient_age > 150:
                raise ValidationError("Invalid patient age")
        
        # Validate gender if provided
        if case_data.patient_gender:
            valid_genders = ["male", "female", "other", "prefer_not_to_say"]
            if case_data.patient_gender.lower() not in valid_genders:
                raise ValidationError(f"Invalid gender. Must be one of: {valid_genders}")
        
        # Validate status
        valid_statuses = ["active", "in_progress", "resolved", "archived"]
        if case_data.status and case_data.status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        
        # Validate urgency level
        valid_urgency_levels = ["low", "medium", "high", "critical"]
        if case_data.urgency_level and case_data.urgency_level not in valid_urgency_levels:
            raise ValidationError(f"Invalid urgency level. Must be one of: {valid_urgency_levels}")
    
    def _validate_update_data(self, update_data: CaseUpdate, existing_case: CaseResponse) -> None:
        """
        Validate case update data
        
        Args:
            update_data: Update data to validate
            existing_case: Existing case for reference
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate title if provided
        if update_data.title is not None and not update_data.title.strip():
            raise ValidationError("Case title cannot be empty")
        
        # Validate description if provided
        if update_data.description is not None and not update_data.description.strip():
            raise ValidationError("Case description cannot be empty")
        
        # Validate age if provided
        if update_data.patient_age is not None:
            if update_data.patient_age < 0 or update_data.patient_age > 150:
                raise ValidationError("Invalid patient age")
        
        # Validate gender if provided
        if update_data.patient_gender is not None:
            valid_genders = ["male", "female", "other", "prefer_not_to_say"]
            if update_data.patient_gender.lower() not in valid_genders:
                raise ValidationError(f"Invalid gender. Must be one of: {valid_genders}")
        
        # Validate status transitions
        if update_data.status:
            valid_statuses = ["active", "in_progress", "resolved", "archived"]
            if update_data.status not in valid_statuses:
                raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
            
            # Validate status transitions
            if existing_case.status == "archived" and update_data.status != "active":
                raise ValidationError("Archived cases can only be restored to active status")
            
            if existing_case.status == "resolved" and update_data.status == "active":
                logger.warning(f"Reopening resolved case {existing_case.id}")
        
        # Validate urgency level if provided
        if update_data.urgency_level:
            valid_urgency_levels = ["low", "medium", "high", "critical"]
            if update_data.urgency_level not in valid_urgency_levels:
                raise ValidationError(f"Invalid urgency level. Must be one of: {valid_urgency_levels}")