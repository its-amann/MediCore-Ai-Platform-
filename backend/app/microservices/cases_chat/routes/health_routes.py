"""
Health Check Routes
Provides health status and monitoring endpoints
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any, List
import logging
from datetime import datetime

from ..dependencies import (
    get_storage_service, get_doctor_service, 
    get_mcp_client, get_websocket_adapter
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["health", "monitoring"]
)


@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """
    Basic health check endpoint
    
    Returns:
        Service health status
    """
    return {
        "service": "cases_chat",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.SERVICE_VERSION
    }


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    storage = Depends(get_storage_service),
    doctor_service = Depends(get_doctor_service),
    mcp_client = Depends(get_mcp_client),
    ws_adapter = Depends(get_websocket_adapter)
):
    """
    Detailed health check with dependency status
    
    Returns:
        Detailed health information for all components
    """
    health_status = {
        "service": "cases_chat",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.SERVICE_VERSION,
        "overall_status": "healthy",
        "components": {}
    }
    
    # Check storage (Neo4j)
    try:
        storage_healthy = await storage.health_check()
        health_status["components"]["storage"] = {
            "status": "healthy" if storage_healthy else "unhealthy",
            "type": "neo4j",
            "message": "Connected" if storage_healthy else "Connection failed"
        }
    except Exception as e:
        health_status["components"]["storage"] = {
            "status": "unhealthy",
            "type": "neo4j",
            "message": str(e)
        }
        health_status["overall_status"] = "degraded"
    
    # Check AI services
    try:
        ai_status = await doctor_service.health_check()
        health_status["components"]["ai_services"] = {
            "status": "healthy" if ai_status["healthy"] else "unhealthy",
            "providers": ai_status.get("providers", {}),
            "message": ai_status.get("message", "")
        }
    except Exception as e:
        health_status["components"]["ai_services"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["overall_status"] = "degraded"
    
    # Check MCP server
    try:
        if mcp_client:
            mcp_healthy = mcp_client.is_available()
            health_status["components"]["mcp_server"] = {
                "status": "healthy" if mcp_healthy else "unhealthy",
                "message": "Connected" if mcp_healthy else "Not available"
            }
        else:
            health_status["components"]["mcp_server"] = {
                "status": "disabled",
                "message": "MCP client not configured"
            }
    except Exception as e:
        health_status["components"]["mcp_server"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # Check WebSocket
    try:
        ws_stats = ws_adapter.ws_manager.get_stats()
        health_status["components"]["websocket"] = {
            "status": "healthy",
            "connections": ws_stats["total_connections"],
            "users": ws_stats["total_users"],
            "rooms": ws_stats["total_rooms"]
        }
    except Exception as e:
        health_status["components"]["websocket"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["overall_status"] = "degraded"
    
    # Determine overall status
    if any(comp.get("status") == "unhealthy" 
           for comp in health_status["components"].values()):
        health_status["overall_status"] = "unhealthy"
    
    return health_status


@router.get("/ready", response_model=Dict[str, bool])
async def readiness_check(
    storage = Depends(get_storage_service),
    doctor_service = Depends(get_doctor_service)
):
    """
    Readiness check for load balancer
    
    Returns:
        Ready status
    """
    try:
        # Check critical dependencies
        storage_ready = await storage.health_check()
        ai_ready = (await doctor_service.health_check())["healthy"]
        
        ready = storage_ready and ai_ready
        
        return {
            "ready": ready,
            "storage_ready": storage_ready,
            "ai_services_ready": ai_ready
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "ready": False,
            "storage_ready": False,
            "ai_services_ready": False
        }


@router.get("/live", response_model=Dict[str, bool])
async def liveness_check():
    """
    Liveness check for container orchestration
    
    Returns:
        Live status
    """
    return {"live": True}


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    storage = Depends(get_storage_service),
    doctor_service = Depends(get_doctor_service),
    ws_adapter = Depends(get_websocket_adapter)
):
    """
    Get service metrics for monitoring
    
    Returns:
        Service metrics and statistics
    """
    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "cases_chat"
        }
        
        # Storage metrics
        try:
            storage_metrics = await storage.get_metrics()
            metrics["storage"] = storage_metrics
        except:
            metrics["storage"] = {"error": "Failed to get storage metrics"}
        
        # AI service metrics
        try:
            ai_metrics = await doctor_service.get_metrics()
            metrics["ai_services"] = ai_metrics
        except:
            metrics["ai_services"] = {"error": "Failed to get AI metrics"}
        
        # WebSocket metrics
        try:
            ws_stats = ws_adapter.ws_manager.get_stats()
            metrics["websocket"] = ws_stats
        except:
            metrics["websocket"] = {"error": "Failed to get WebSocket metrics"}
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/dependencies", response_model=List[Dict[str, Any]])
async def list_dependencies():
    """
    List all service dependencies and their status
    
    Returns:
        List of dependencies with configuration info
    """
    dependencies = [
        {
            "name": "Neo4j Database",
            "type": "database",
            "required": True,
            "configured": bool(settings.NEO4J_URI),
            "uri": settings.NEO4J_URI if settings.NEO4J_URI else "Not configured"
        },
        {
            "name": "Groq API",
            "type": "ai_provider",
            "required": True,
            "configured": bool(settings.GROQ_API_KEY),
            "models": ["mixtral-8x7b-32768", "llama3-70b-8192"]
        },
        {
            "name": "Gemini API",
            "type": "ai_provider", 
            "required": False,
            "configured": bool(settings.GEMINI_API_KEY),
            "models": ["gemini-1.5-flash", "gemini-1.5-pro"]
        },
        {
            "name": "MCP Server",
            "type": "microservice",
            "required": False,
            "configured": bool(settings.MCP_SERVER_URL),
            "url": settings.MCP_SERVER_URL if settings.MCP_SERVER_URL else "Not configured"
        },
        {
            "name": "WebSocket Manager",
            "type": "core_service",
            "required": True,
            "configured": True,
            "description": "Unified WebSocket management"
        }
    ]
    
    return dependencies