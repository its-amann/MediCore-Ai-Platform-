"""
Debug endpoints for medical imaging - temporary for troubleshooting
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from app.api.routes.auth import get_current_user
from app.core.database.models import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/medical-imaging", tags=["medical-imaging-debug"])


@router.get("/reports/recent/all", response_model=dict)
async def get_recent_reports(
    limit: int = Query(default=10, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent reports across all patients for debugging
    """
    try:
        from app.microservices.medical_imaging.services.neo4j_report_storage import get_neo4j_storage
        
        neo4j_storage = get_neo4j_storage()
        reports = neo4j_storage.get_recent_reports(limit)
        
        return {
            "total_reports": len(reports),
            "limit": limit,
            "reports": reports
        }
        
    except Exception as e:
        logger.error(f"Error retrieving recent reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )