"""
Enhanced case management routes with PUT endpoint
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ...models.case_models import CaseResponse, CaseCreate, CaseUpdate
from ...core.dependencies import get_storage_service, get_case_service
from ...core.exceptions import CaseNotFoundError, ValidationError
from ...services.storage.neo4j_storage import UnifiedNeo4jStorage
from ...services.case_management.case_service import CaseService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    storage: UnifiedNeo4jStorage = Depends(get_storage_service),
    case_service: CaseService = Depends(get_case_service)
) -> CaseResponse:
    """
    Create a new medical case
    
    Args:
        case_data: Case creation data
        
    Returns:
        Created case with generated ID and case number
    """
    try:
        # Create case through service
        case = await case_service.create_case(case_data)
        logger.info(f"Created case {case.id} with number {case.case_number}")
        return case
        
    except ValidationError as e:
        logger.error(f"Validation error creating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create case"
        )


@router.get("/", response_model=Dict[str, Any])
async def list_cases(
    skip: int = Query(0, ge=0, description="Number of cases to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of cases"),
    status: Optional[str] = Query(None, description="Filter by status"),
    urgency_level: Optional[str] = Query(None, description="Filter by urgency level"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> Dict[str, Any]:
    """
    List cases with filtering and pagination
    
    Returns:
        Dictionary with cases array and total count
    """
    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if urgency_level:
            filters["urgency_level"] = urgency_level
        if patient_id:
            filters["patient_id"] = patient_id
        
        # If search is provided, use search endpoint
        if search:
            cases, total = await storage.search_cases(
                query=search,
                filters=filters,
                skip=skip,
                limit=limit
            )
        else:
            # Regular listing
            cases, total = await storage.list_cases(
                skip=skip,
                limit=limit,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order
            )
        
        return {
            "cases": cases,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error listing cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cases"
        )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    include_stats: bool = Query(False, description="Include case statistics"),
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> CaseResponse:
    """
    Get a specific case by ID
    
    Args:
        case_id: Case ID
        include_stats: Whether to include case statistics
        
    Returns:
        Case details
    """
    try:
        case = await storage.get_case(case_id)
        if not case:
            raise CaseNotFoundError(case_id)
        
        # Add statistics if requested
        if include_stats:
            stats = await storage.get_case_statistics(case_id)
            case.metadata = case.metadata or {}
            case.metadata["statistics"] = stats
        
        return case
        
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get case"
        )


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case_full(
    case_id: str,
    case_data: CaseCreate,
    storage: UnifiedNeo4jStorage = Depends(get_storage_service),
    case_service: CaseService = Depends(get_case_service)
) -> CaseResponse:
    """
    Full update of a case (PUT endpoint)
    
    This replaces all case fields with the provided data.
    Use PATCH for partial updates.
    
    Args:
        case_id: Case ID to update
        case_data: Complete case data
        
    Returns:
        Updated case
    """
    try:
        # Check if case exists
        existing_case = await storage.get_case(case_id)
        if not existing_case:
            raise CaseNotFoundError(case_id)
        
        # Create full update data
        update_data = CaseUpdate(
            title=case_data.title,
            description=case_data.description,
            patient_age=case_data.patient_age,
            patient_gender=case_data.patient_gender,
            status=case_data.status,
            urgency_level=case_data.urgency_level,
            medical_category=case_data.medical_category,
            symptoms=case_data.symptoms,
            medical_history=case_data.medical_history,
            current_medications=case_data.current_medications,
            allergies=case_data.allergies,
            metadata=case_data.metadata
        )
        
        # Update through service
        updated_case = await case_service.update_case(case_id, update_data)
        logger.info(f"Full update of case {case_id}")
        return updated_case
        
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except ValidationError as e:
        logger.error(f"Validation error updating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update case"
        )


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case_partial(
    case_id: str,
    case_update: CaseUpdate,
    storage: UnifiedNeo4jStorage = Depends(get_storage_service),
    case_service: CaseService = Depends(get_case_service)
) -> CaseResponse:
    """
    Partial update of a case (PATCH endpoint)
    
    Only updates the fields provided in the request.
    
    Args:
        case_id: Case ID to update
        case_update: Partial update data
        
    Returns:
        Updated case
    """
    try:
        # Check if case exists
        existing_case = await storage.get_case(case_id)
        if not existing_case:
            raise CaseNotFoundError(case_id)
        
        # Update through service
        updated_case = await case_service.update_case(case_id, case_update)
        logger.info(f"Partial update of case {case_id}")
        return updated_case
        
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except ValidationError as e:
        logger.error(f"Validation error updating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update case"
        )


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    permanent: bool = Query(False, description="Permanently delete (vs archive)"),
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> None:
    """
    Delete or archive a case
    
    Args:
        case_id: Case ID to delete
        permanent: If true, permanently delete. Otherwise, archive.
    """
    try:
        # Check if case exists
        existing_case = await storage.get_case(case_id)
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        if permanent:
            # Permanent deletion
            deleted = await storage.delete_case(case_id)
            if deleted:
                logger.info(f"Permanently deleted case {case_id}")
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete case"
                )
        else:
            # Archive the case
            archived = await storage.archive_case(case_id)
            if archived:
                logger.info(f"Archived case {case_id}")
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to archive case"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete case"
        )


@router.post("/{case_id}/restore", response_model=CaseResponse)
async def restore_case(
    case_id: str,
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> CaseResponse:
    """
    Restore an archived case
    
    Args:
        case_id: Case ID to restore
        
    Returns:
        Restored case
    """
    try:
        # Check if case exists
        existing_case = await storage.get_case(case_id)
        if not existing_case:
            raise CaseNotFoundError(case_id)
        
        if existing_case.status != "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case is not archived"
            )
        
        # Restore the case
        restored = await storage.restore_case(case_id)
        if restored:
            case = await storage.get_case(case_id)
            logger.info(f"Restored case {case_id}")
            return case
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore case"
            )
            
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore case"
        )


@router.get("/{case_id}/messages", response_model=Dict[str, Any])
async def get_case_messages(
    case_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    include_system: bool = Query(True, description="Include system messages"),
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> Dict[str, Any]:
    """
    Get messages for a case
    
    Args:
        case_id: Case ID
        limit: Maximum messages to return
        offset: Number of messages to skip
        include_system: Whether to include system messages
        
    Returns:
        Dictionary with messages and metadata
    """
    try:
        # Check if case exists
        case = await storage.get_case(case_id)
        if not case:
            raise CaseNotFoundError(case_id)
        
        # Get messages
        messages = await storage.get_case_messages(
            case_id=case_id,
            limit=limit,
            offset=offset,
            include_system=include_system
        )
        
        # Get total count
        total_count = await storage.get_message_count(case_id)
        
        return {
            "messages": messages,
            "total": total_count,
            "case_id": case_id,
            "offset": offset,
            "limit": limit
        }
        
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting messages for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get case messages"
        )


@router.get("/{case_id}/attachments", response_model=List[Dict[str, Any]])
async def get_case_attachments(
    case_id: str,
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> List[Dict[str, Any]]:
    """
    Get attachments for a case
    
    Args:
        case_id: Case ID
        
    Returns:
        List of attachments
    """
    try:
        # Check if case exists
        case = await storage.get_case(case_id)
        if not case:
            raise CaseNotFoundError(case_id)
        
        # Get attachments
        attachments = await storage.get_case_attachments(case_id)
        return attachments
        
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting attachments for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get case attachments"
        )


@router.delete("/{case_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_attachment(
    case_id: str,
    attachment_id: str,
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> None:
    """
    Delete an attachment from a case
    
    Args:
        case_id: Case ID
        attachment_id: Attachment ID to delete
    """
    try:
        # Check if case exists
        case = await storage.get_case(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        # Delete attachment
        deleted = await storage.delete_attachment(case_id, attachment_id)
        if deleted:
            logger.info(f"Deleted attachment {attachment_id} from case {case_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment {attachment_id} not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting attachment {attachment_id} from case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete attachment"
        )


@router.get("/{case_id}/statistics", response_model=Dict[str, Any])
async def get_case_statistics(
    case_id: str,
    storage: UnifiedNeo4jStorage = Depends(get_storage_service)
) -> Dict[str, Any]:
    """
    Get statistics for a case
    
    Args:
        case_id: Case ID
        
    Returns:
        Case statistics including message counts, timings, etc.
    """
    try:
        stats = await storage.get_case_statistics(case_id)
        return stats
        
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting statistics for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get case statistics"
        )