"""
Voice Consultation Monitoring Routes
Endpoints for accessing voice consultation metrics and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.core.database.models import User
from app.api.routes.auth import get_current_active_user
from ..services.monitoring.monitoring_service import voice_monitoring_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["voice-monitoring"])


@router.get("/realtime")
async def get_realtime_metrics(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get real-time voice consultation metrics"""
    try:
        return voice_monitoring_service.get_real_time_stats()
    except Exception as e:
        logger.error(f"Failed to get real-time metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_metrics(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get metrics for a specific voice consultation session"""
    try:
        metrics = voice_monitoring_service.get_session_metrics(session_id)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session metrics not found"
            )
        
        # Verify user has access to this session
        if metrics.get("user_id") != current_user.user_id:
            # Check if user is admin
            if not getattr(current_user, "is_admin", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session metrics: {str(e)}"
        )


@router.get("/hourly")
async def get_hourly_metrics(
    hours: int = Query(default=24, ge=1, le=168),  # Max 1 week
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """Get hourly metrics for voice consultations"""
    try:
        return voice_monitoring_service.get_hourly_metrics(hours)
    except Exception as e:
        logger.error(f"Failed to get hourly metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hourly metrics: {str(e)}"
        )


@router.get("/providers")
async def get_provider_analytics(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get analytics by AI provider"""
    try:
        return voice_monitoring_service.get_provider_analytics()
    except Exception as e:
        logger.error(f"Failed to get provider analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get provider analytics: {str(e)}"
        )


@router.get("/dashboard")
async def get_monitoring_dashboard(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get comprehensive monitoring dashboard data"""
    try:
        # Get all monitoring data
        realtime = voice_monitoring_service.get_real_time_stats()
        hourly = voice_monitoring_service.get_hourly_metrics(24)
        providers = voice_monitoring_service.get_provider_analytics()
        
        # Calculate additional metrics
        total_sessions_24h = sum(h.get("sessions_started", 0) for h in hourly)
        total_errors_24h = sum(h.get("errors", 0) for h in hourly)
        error_rate = (total_errors_24h / total_sessions_24h * 100) if total_sessions_24h > 0 else 0
        
        # Get user-specific stats if not admin
        user_sessions = 0
        if not getattr(current_user, "is_admin", False):
            # Filter to show only user's sessions
            # This would require additional tracking in the monitoring service
            pass
        
        return {
            "realtime": realtime,
            "last_24_hours": {
                "total_sessions": total_sessions_24h,
                "total_errors": total_errors_24h,
                "error_rate_percent": round(error_rate, 2),
                "hourly_data": hourly
            },
            "providers": providers,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring dashboard: {str(e)}"
        )


@router.get("/health/performance")
async def get_performance_health(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get performance health metrics"""
    try:
        stats = voice_monitoring_service.get_real_time_stats()
        performance = stats.get("performance", {})
        
        # Define health thresholds
        health_status = "healthy"
        issues = []
        
        # Check transcription latency
        if "transcription_latency" in performance:
            p90 = performance["transcription_latency"].get("p90", 0)
            if p90 > 5000:  # 5 seconds
                health_status = "unhealthy"
                issues.append("High transcription latency")
            elif p90 > 3000:  # 3 seconds
                health_status = "degraded"
                issues.append("Elevated transcription latency")
        
        # Check AI response latency
        if "ai_response_latency" in performance:
            p90 = performance["ai_response_latency"].get("p90", 0)
            if p90 > 10000:  # 10 seconds
                health_status = "unhealthy"
                issues.append("High AI response latency")
            elif p90 > 5000:  # 5 seconds
                health_status = "degraded"
                issues.append("Elevated AI response latency")
        
        # Check error rate
        current_hour = stats.get("current_hour", {})
        sessions = current_hour.get("sessions_started", 0)
        errors = current_hour.get("errors", 0)
        
        if sessions > 0:
            error_rate = (errors / sessions) * 100
            if error_rate > 10:
                health_status = "unhealthy"
                issues.append(f"High error rate: {error_rate:.1f}%")
            elif error_rate > 5:
                health_status = "degraded"
                issues.append(f"Elevated error rate: {error_rate:.1f}%")
        
        return {
            "status": health_status,
            "issues": issues,
            "performance_metrics": performance,
            "error_metrics": {
                "sessions_this_hour": sessions,
                "errors_this_hour": errors,
                "error_rate_percent": round((errors / sessions * 100) if sessions > 0 else 0, 2)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance health: {str(e)}"
        )