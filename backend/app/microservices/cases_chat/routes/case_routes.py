"""
Case Management Routes
Handles CRUD operations for medical cases
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..models import (
    CaseCreate, CaseUpdate, CaseResponse, CaseStatus, CasePriority
)
from ..dependencies import get_current_user_id, get_storage_service, get_case_service
from ..utils.validators import validate_case_data
from ..utils.error_handlers import handle_storage_error

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cases",
    tags=["cases"]
)


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service),
    case_service = Depends(get_case_service)
):
    """
    Create a new medical case
    
    Args:
        case_data: Case creation data
        user_id: Current user ID from auth
        storage: Storage service instance
        case_service: Case management service
        
    Returns:
        Created case data with generated ID and case number
    """
    try:
        # Validate case data
        validated_data = validate_case_data(case_data)
        
        # Generate case number
        case_number = await case_service.generate_case_number(user_id)
        
        # Create case in storage
        case_id = await storage.create_case(
            user_id=user_id,
            case_data=validated_data,
            case_number=case_number
        )
        
        # Retrieve and return created case
        case = await storage.get_case(case_id)
        
        logger.info(f"Created case {case_id} for user {user_id}")
        return CaseResponse(**case)
        
    except ValueError as e:
        logger.error(f"Validation error creating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise handle_storage_error(e)


@router.get("/", response_model=List[CaseResponse])
async def list_cases(
    user_id: str = Depends(get_current_user_id),
    status: Optional[CaseStatus] = Query(None, description="Filter by case status"),
    priority: Optional[CasePriority] = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of cases to return"),
    offset: int = Query(0, ge=0, description="Number of cases to skip"),
    storage = Depends(get_storage_service)
):
    """
    List cases for the current user with optional filtering
    
    Args:
        user_id: Current user ID
        status: Optional status filter
        priority: Optional priority filter
        limit: Maximum results to return
        offset: Number of results to skip
        storage: Storage service instance
        
    Returns:
        List of cases matching filters
    """
    try:
        cases = await storage.list_user_cases(
            user_id=user_id,
            status=status,
            priority=priority,
            limit=limit,
            offset=offset
        )
        
        return [CaseResponse(**case) for case in cases]
        
    except Exception as e:
        logger.error(f"Error listing cases: {e}")
        raise handle_storage_error(e)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service)
):
    """
    Get a specific case by ID
    
    Args:
        case_id: Case ID
        user_id: Current user ID
        storage: Storage service instance
        
    Returns:
        Case data
    """
    try:
        case = await storage.get_case(case_id)
        
        # Verify user owns this case
        if case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        return CaseResponse(**case)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case {case_id}: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        raise handle_storage_error(e)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service)
):
    """
    Update a case
    
    Args:
        case_id: Case ID to update
        case_update: Update data
        user_id: Current user ID
        storage: Storage service instance
        
    Returns:
        Updated case data
    """
    try:
        # Verify user owns this case
        existing_case = await storage.get_case(case_id)
        if existing_case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        # Update case
        update_data = case_update.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            # Handle status changes
            if "status" in update_data and update_data["status"] == CaseStatus.CLOSED:
                update_data["closed_at"] = datetime.utcnow()
            
            await storage.update_case(case_id, update_data)
        
        # Return updated case
        updated_case = await storage.get_case(case_id)
        return CaseResponse(**updated_case)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case {case_id}: {e}")
        raise handle_storage_error(e)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service)
):
    """
    Delete a case (soft delete - sets status to archived)
    
    Args:
        case_id: Case ID to delete
        user_id: Current user ID
        storage: Storage service instance
    """
    try:
        # Verify user owns this case
        existing_case = await storage.get_case(case_id)
        if existing_case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        # Soft delete by archiving
        await storage.update_case(case_id, {
            "status": CaseStatus.ARCHIVED,
            "updated_at": datetime.utcnow(),
            "archived_at": datetime.utcnow()
        })
        
        logger.info(f"Archived case {case_id} for user {user_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting case {case_id}: {e}")
        raise handle_storage_error(e)


@router.get("/{case_id}/chat-sessions", response_model=List[Dict[str, Any]])
async def list_case_chat_sessions(
    case_id: str,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service)
):
    """
    List all chat sessions for a case
    
    Args:
        case_id: Case ID
        user_id: Current user ID
        storage: Storage service instance
        
    Returns:
        List of chat sessions
    """
    try:
        # Verify user owns this case
        case = await storage.get_case(case_id)
        if case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        sessions = await storage.get_case_chat_sessions(case_id)
        return sessions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing chat sessions for case {case_id}: {e}")
        raise handle_storage_error(e)


@router.post("/{case_id}/close", response_model=CaseResponse)
async def close_case(
    case_id: str,
    outcome: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service)
):
    """
    Close a case with optional outcome
    
    Args:
        case_id: Case ID to close
        outcome: Optional case outcome description
        user_id: Current user ID
        storage: Storage service instance
        
    Returns:
        Updated case data
    """
    try:
        # Verify user owns this case
        case = await storage.get_case(case_id)
        if case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        if case.get("status") == CaseStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case is already closed"
            )
        
        # Close the case
        update_data = {
            "status": CaseStatus.CLOSED,
            "closed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if outcome:
            update_data["outcome"] = outcome
        
        await storage.update_case(case_id, update_data)
        
        # Return updated case
        updated_case = await storage.get_case(case_id)
        logger.info(f"Closed case {case_id} for user {user_id}")
        
        return CaseResponse(**updated_case)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing case {case_id}: {e}")
        raise handle_storage_error(e)