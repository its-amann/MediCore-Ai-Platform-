"""
Medical context retrieval API routes
Provides endpoints for accessing patient medical history and similar cases
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.api.routes.auth import get_current_active_user
from app.core.database.models import User
from app.microservices.cases_chat.mcp_server.medical_history_service import (
    get_medical_history_service, MedicalHistoryService
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_medical_cases(
    query: str = Query(..., description="Search query for cases"),
    status_filter: Optional[str] = Query(None, description="Filter by case status"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority"),
    date_from: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date filter (ISO format)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    current_user: User = Depends(get_current_active_user)
):
    """Search patient's medical cases based on symptoms, conditions, or keywords"""
    try:
        service = get_medical_history_service()
        
        # Build filters
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if priority_filter:
            filters["priority"] = priority_filter
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        
        # Search cases
        cases = await service.search_cases(
            user_id=current_user.user_id,
            query=query,
            filters=filters,
            limit=limit
        )
        
        return cases
        
    except Exception as e:
        logger.error(f"Error searching medical cases: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search medical cases: {str(e)}"
        )


@router.get("/case/{case_id}/history", response_model=Dict[str, Any])
async def get_case_medical_history(
    case_id: str,
    include_chat: bool = Query(True, description="Include chat consultations"),
    include_analysis: bool = Query(True, description="Include analysis data"),
    current_user: User = Depends(get_current_active_user)
):
    """Get complete medical history for a specific case"""
    try:
        service = get_medical_history_service()
        
        history = await service.get_case_history(
            case_id=case_id,
            user_id=current_user.user_id,
            include_chat=include_chat,
            include_analysis=include_analysis
        )
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving case history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve case history: {str(e)}"
        )


@router.get("/similar-cases", response_model=List[Dict[str, Any]])
async def find_similar_medical_cases(
    case_id: Optional[str] = Query(None, description="Reference case ID"),
    symptoms: Optional[List[str]] = Query(None, description="List of symptoms to match"),
    similarity_threshold: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity score"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results to return"),
    include_all_users: bool = Query(False, description="Search across all users (admin only)"),
    current_user: User = Depends(get_current_active_user)
):
    """Find cases similar to a given case or set of symptoms"""
    try:
        if not case_id and not symptoms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either case_id or symptoms must be provided"
            )
        
        service = get_medical_history_service()
        
        # For privacy, only search within user's own cases unless admin
        user_id = None if include_all_users else current_user.user_id
        
        similar_cases = await service.find_similar_cases(
            case_id=case_id,
            symptoms=symptoms,
            user_id=user_id,
            similarity_threshold=similarity_threshold,
            limit=limit
        )
        
        return similar_cases
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar cases: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar cases: {str(e)}"
        )


@router.get("/timeline", response_model=List[Dict[str, Any]])
async def get_patient_medical_timeline(
    date_from: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date filter (ISO format)"),
    current_user: User = Depends(get_current_active_user)
):
    """Get timeline of all medical cases for the current patient"""
    try:
        service = get_medical_history_service()
        
        timeline = await service.get_patient_timeline(
            user_id=current_user.user_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return timeline
        
    except Exception as e:
        logger.error(f"Error retrieving patient timeline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve patient timeline: {str(e)}"
        )


@router.get("/patterns/{pattern_type}", response_model=Dict[str, Any])
async def analyze_medical_patterns(
    pattern_type: str = Path(..., description="Type of pattern to analyze (symptoms, conditions, treatments)"),
    current_user: User = Depends(get_current_active_user)
):
    """Analyze patterns in patient's medical history"""
    try:
        if pattern_type not in ["symptoms", "conditions", "treatments"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid pattern type. Must be one of: symptoms, conditions, treatments"
            )
        
        service = get_medical_history_service()
        
        patterns = await service.analyze_patterns(
            user_id=current_user.user_id,
            pattern_type=pattern_type
        )
        
        return patterns
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing patterns: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze patterns: {str(e)}"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_medical_statistics(
    current_user: User = Depends(get_current_active_user)
):
    """Get statistical insights about patient's medical cases"""
    try:
        service = get_medical_history_service()
        
        stats = await service.get_case_statistics(user_id=current_user.user_id)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get("/context/{case_id}", response_model=Dict[str, Any])
async def get_consultation_context(
    case_id: str,
    include_similar_cases: bool = Query(True, description="Include similar cases"),
    similar_cases_limit: int = Query(3, ge=1, le=10, description="Number of similar cases to include"),
    include_timeline: bool = Query(True, description="Include patient timeline"),
    timeline_days: int = Query(30, ge=1, le=365, description="Days of timeline to include"),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive medical context for AI doctor consultation"""
    try:
        service = get_medical_history_service()
        
        # Get current case history
        case_history = await service.get_case_history(
            case_id=case_id,
            user_id=current_user.user_id,
            include_chat=True,
            include_analysis=True
        )
        
        if not case_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        context = {
            "case_history": case_history,
            "similar_cases": [],
            "patient_timeline": [],
            "pattern_analysis": None
        }
        
        # Get similar cases if requested
        if include_similar_cases:
            similar_cases = await service.find_similar_cases(
                case_id=case_id,
                user_id=current_user.user_id,
                similarity_threshold=0.5,
                limit=similar_cases_limit
            )
            context["similar_cases"] = similar_cases
        
        # Get patient timeline if requested
        if include_timeline:
            from datetime import datetime, timedelta
            date_to = datetime.utcnow().isoformat()
            date_from = (datetime.utcnow() - timedelta(days=timeline_days)).isoformat()
            
            timeline = await service.get_patient_timeline(
                user_id=current_user.user_id,
                date_from=date_from,
                date_to=date_to
            )
            context["patient_timeline"] = timeline
        
        # Get symptom patterns
        patterns = await service.analyze_patterns(
            user_id=current_user.user_id,
            pattern_type="symptoms"
        )
        context["pattern_analysis"] = patterns
        
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving consultation context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve consultation context: {str(e)}"
        )


# Health check endpoint for MCP service
@router.get("/health")
async def medical_context_health():
    """Check if medical context service is healthy"""
    try:
        service = get_medical_history_service()
        # Try a simple operation to verify service is working
        stats = await service.get_case_statistics(user_id=None)
        
        return {
            "status": "healthy",
            "service": "medical_context",
            "total_cases": stats.get("total_cases", 0)
        }
    except Exception as e:
        logger.error(f"Medical context service health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "medical_context",
            "error": str(e)
        }