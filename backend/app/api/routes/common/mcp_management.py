"""
MCP Management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.core.unified_logging import get_logger
# from app.api.dependencies.auth import get_current_user_optional  # TODO: Function doesn't exist
from typing import Optional
from app.api.routes.auth import get_current_user
from app.core.database.models import User

# Create optional version
async def get_current_user_optional(user: Optional[User] = None) -> Optional[User]:
    try:
        return user
    except:
        return None
from app.core.services.mcp_server_manager import get_mcp_server_manager
from app.core.services.mcp_client_pool import get_mcp_client_pool

logger = get_logger(__name__)

router = APIRouter()


class MCPServerAction(BaseModel):
    """MCP Server action request"""
    action: str  # start, stop, restart
    server_name: str


class MCPTestRequest(BaseModel):
    """MCP test request"""
    client_name: str
    method: str
    params: Optional[Dict[str, Any]] = None


@router.get("/mcp/servers/status")
async def get_mcp_servers_status(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get status of all MCP servers"""
    try:
        manager = await get_mcp_server_manager()
        return await manager.get_all_server_status()
    except Exception as e:
        logger.error(f"Error getting MCP servers status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/servers/{server_name}/status")
async def get_mcp_server_status(
    server_name: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get status of a specific MCP server"""
    try:
        manager = await get_mcp_server_manager()
        return await manager.get_server_status(server_name)
    except Exception as e:
        logger.error(f"Error getting MCP server status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/servers/action")
async def mcp_server_action(
    request: MCPServerAction,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Perform action on MCP server (start, stop, restart)"""
    try:
        manager = await get_mcp_server_manager()
        
        if request.action == "start":
            success = await manager.start_server(request.server_name)
        elif request.action == "stop":
            success = await manager.stop_server(request.server_name)
        elif request.action == "restart":
            success = await manager.restart_server(request.server_name)
        else:
            raise ValueError(f"Invalid action: {request.action}")
        
        return {
            "success": success,
            "action": request.action,
            "server_name": request.server_name,
            "status": await manager.get_server_status(request.server_name)
        }
        
    except Exception as e:
        logger.error(f"Error performing MCP server action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/clients/status")
async def get_mcp_clients_status(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get status of all MCP clients"""
    try:
        pool = await get_mcp_client_pool()
        return await pool.health_check_all()
    except Exception as e:
        logger.error(f"Error getting MCP clients status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/clients/{client_name}/stats")
async def get_mcp_client_stats(
    client_name: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get statistics for a specific MCP client"""
    try:
        pool = await get_mcp_client_pool()
        stats = pool.get_stats(client_name)
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"Client {client_name} not found")
        
        return {
            "client_name": client_name,
            "total_requests": stats.total_requests,
            "successful_requests": stats.successful_requests,
            "failed_requests": stats.failed_requests,
            "success_rate": stats.success_rate,
            "average_request_time": stats.average_request_time,
            "last_request_time": stats.last_request_time.isoformat() if stats.last_request_time else None,
            "last_error": stats.last_error,
            "last_error_time": stats.last_error_time.isoformat() if stats.last_error_time else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MCP client stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/test")
async def test_mcp_request(
    request: MCPTestRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Test an MCP request"""
    try:
        pool = await get_mcp_client_pool()
        result = await pool.execute_request(
            request.client_name,
            request.method,
            request.params
        )
        
        return {
            "success": True,
            "client_name": request.client_name,
            "method": request.method,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error testing MCP request: {e}")
        return {
            "success": False,
            "client_name": request.client_name,
            "method": request.method,
            "error": str(e)
        }