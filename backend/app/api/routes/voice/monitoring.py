"""
Monitoring routes for voice consultation service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta

from app.core.database.models import User
from app.api.routes.auth import get_current_active_user
from app.microservices.voice_consultation.services.monitoring.monitoring_service import VoiceConsultationMonitoringService as MonitoringService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice-monitoring"])

# Service instance
_monitoring_service = None

def get_monitoring_service() -> MonitoringService:
    """Get or create monitoring service"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


@router.get("/health", response_model=Dict[str, Any])
async def get_service_health(
    current_user: User = Depends(get_current_active_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """Get voice consultation service health status"""
    try:
        health_status = monitoring_service.get_health_status()
        return health_status
        
    except Exception as e:
        logger.error(f"Error getting health status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health status: {str(e)}"
        )


@router.get("/metrics", response_model=Dict[str, Any])
async def get_service_metrics(
    time_range: str = "1h",
    current_user: User = Depends(get_current_active_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """Get service metrics for specified time range"""
    try:
        # Parse time range
        time_ranges = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        if time_range not in time_ranges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time range. Must be one of: {list(time_ranges.keys())}"
            )
            
        metrics = monitoring_service.get_metrics(time_ranges[time_range])
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/provider-stats", response_model=Dict[str, Any])
async def get_provider_statistics(
    current_user: User = Depends(get_current_active_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """Get AI provider usage statistics"""
    try:
        stats = monitoring_service.get_provider_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting provider stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get provider statistics: {str(e)}"
        )


@router.get("/errors", response_model=List[Dict[str, Any]])
async def get_recent_errors(
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """Get recent errors from the service"""
    try:
        errors = monitoring_service.get_recent_errors(limit=limit)
        return errors
        
    except Exception as e:
        logger.error(f"Error getting recent errors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent errors: {str(e)}"
        )


@router.post("/reset-metrics")
async def reset_metrics(
    current_user: User = Depends(get_current_active_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """Reset monitoring metrics (admin only)"""
    try:
        # Check if user is admin (you might want to implement proper admin check)
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
            
        monitoring_service.reset_metrics()
        return {"message": "Metrics reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset metrics: {str(e)}"
        )