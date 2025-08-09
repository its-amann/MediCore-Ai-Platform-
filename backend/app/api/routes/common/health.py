"""
Health check routes for system status monitoring
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import os
import psutil
from datetime import datetime

from app.core.config import settings

router = APIRouter()

# Local dependency to check database status
def get_database_status():
    """Get database connection status without circular import"""
    # For now, just return a simple status
    # This avoids the circular import issue
    return {
        "connected": False,  # Will be updated when database is properly initialized
        "client_available": False
    }

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Unified Medical AI Platform",
        "version": settings.app_version
    }

@router.get("/health/detailed")
async def detailed_health_check(
    db_status: Dict = Depends(get_database_status)
) -> Dict[str, Any]:
    """Detailed health check with component status"""
    
    # Check system resources
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Check critical services
    services_status = {
        "database": {
            "connected": db_status["connected"],
            "type": "neo4j",
            "status": "healthy" if db_status["connected"] else "degraded"
        },
        "ai_service": {
            "status": "healthy" if settings.gemini_api_key else "degraded",
            "provider": "gemini"
        },
        "mcp_server": {
            "enabled": settings.mcp_server_enabled,
            "status": "optional"
        }
    }
    
    # Overall health determination
    critical_services_ok = (
        services_status["ai_service"]["status"] == "healthy"
        # Database is optional for some operations
    )
    
    return {
        "status": "healthy" if critical_services_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Unified Medical AI Platform",
        "version": settings.app_version,
        "environment": {
            "debug": settings.debug,
            "host": settings.host,
            "port": settings.port
        },
        "system": {
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "cpu_count": psutil.cpu_count()
        },
        "services": services_status,
        "features": {
            "websocket": True,
            "file_upload": True,
            "ai_consultation": services_status["ai_service"]["status"] == "healthy",
            "case_management": services_status["database"]["status"] == "healthy"
        }
    }

@router.get("/ready")
async def readiness_check(
    db_status: Dict = Depends(get_database_status)
) -> Dict[str, Any]:
    """Readiness probe for container orchestration"""
    
    # Check if essential services are ready
    is_ready = (
        settings.gemini_api_key and  # AI service configured
        (db_status["connected"] or True)  # Database optional for basic operations
    )
    
    if not is_ready:
        return {
            "ready": False,
            "reason": "Essential services not available",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat()
    }