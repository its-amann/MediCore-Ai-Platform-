"""
MCP Client Pool - Manages shared MCP client connections for all microservices
"""

import asyncio
from typing import Dict, Optional, Any, List
from contextlib import asynccontextmanager
import aiohttp
from datetime import datetime
from dataclasses import dataclass, field

from app.core.unified_logging import get_logger
from app.core.config import settings
from app.microservices.cases_chat.mcp_server.mcp_client import AsyncMCPClient

logger = get_logger(__name__)


@dataclass
class MCPClientConfig:
    """Configuration for an MCP client"""
    name: str
    host: str = "localhost"
    port: int = 8001
    max_connections: int = 10
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class MCPClientStats:
    """Statistics for an MCP client"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_request_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    @property
    def average_request_time(self) -> float:
        """Get average request time in seconds"""
        if self.total_requests == 0:
            return 0.0
        return self.total_request_time / self.total_requests
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage"""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100


class MCPClientPool:
    """Manages a pool of MCP client connections with load balancing and failover"""
    
    def __init__(self):
        self.clients: Dict[str, List[AsyncMCPClient]] = {}
        self.configs: Dict[str, MCPClientConfig] = {}
        self.stats: Dict[str, MCPClientStats] = {}
        self.client_locks: Dict[str, asyncio.Semaphore] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the MCP client pool"""
        if self._initialized:
            return
            
        logger.info("Initializing MCP Client Pool")
        
        # Register default MCP clients
        if settings.mcp_server_enabled:
            # Cases Chat MCP Client
            cases_config = MCPClientConfig(
                name="cases_mcp",
                host=settings.mcp_server_host,
                port=settings.mcp_server_port,
                max_connections=10
            )
            await self.register_client(cases_config)
        
        # TODO: Add other MCP clients (imaging, voice) when ready
        
        self._initialized = True
        logger.info("MCP Client Pool initialized")
    
    async def register_client(self, config: MCPClientConfig):
        """Register an MCP client configuration and create client pool"""
        if config.name in self.clients:
            logger.warning(f"MCP client {config.name} already registered, updating configuration")
            # Close existing clients
            await self._close_client_pool(config.name)
        
        self.configs[config.name] = config
        self.stats[config.name] = MCPClientStats()
        self.client_locks[config.name] = asyncio.Semaphore(config.max_connections)
        
        # Create client pool
        self.clients[config.name] = []
        for i in range(config.max_connections):
            client = AsyncMCPClient(config.host, config.port)
            self.clients[config.name].append(client)
        
        logger.info(f"Registered MCP client pool: {config.name} with {config.max_connections} connections")
    
    @asynccontextmanager
    async def get_client(self, client_name: str):
        """Get an MCP client from the pool as a context manager"""
        if client_name not in self.clients:
            raise ValueError(f"Unknown MCP client: {client_name}")
        
        # Use semaphore to limit concurrent connections
        async with self.client_locks[client_name]:
            # Get next available client (simple round-robin)
            client_pool = self.clients[client_name]
            if not client_pool:
                raise RuntimeError(f"No clients available for {client_name}")
            
            # Pop client from pool
            client = client_pool.pop(0)
            
            try:
                # Ensure client is connected
                if not client.connected:
                    await client.connect()
                
                yield client
                
            finally:
                # Return client to pool
                client_pool.append(client)
    
    async def execute_request(
        self,
        client_name: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        retry: bool = True
    ) -> Any:
        """Execute a request on an MCP client with retry logic"""
        if client_name not in self.clients:
            raise ValueError(f"Unknown MCP client: {client_name}")
        
        config = self.configs[client_name]
        stats = self.stats[client_name]
        
        last_error = None
        start_time = datetime.utcnow()
        
        for attempt in range(config.retry_attempts if retry else 1):
            try:
                async with self.get_client(client_name) as client:
                    # Execute request
                    result = await client.send_request(method, params)
                    
                    # Update stats
                    stats.total_requests += 1
                    stats.successful_requests += 1
                    stats.total_request_time += (datetime.utcnow() - start_time).total_seconds()
                    stats.last_request_time = datetime.utcnow()
                    
                    return result
                    
            except Exception as e:
                last_error = e
                logger.warning(
                    f"MCP request failed for {client_name}.{method} "
                    f"(attempt {attempt + 1}/{config.retry_attempts}): {e}"
                )
                
                if attempt < config.retry_attempts - 1 and retry:
                    await asyncio.sleep(config.retry_delay * (attempt + 1))
                    
        # All attempts failed
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.total_request_time += (datetime.utcnow() - start_time).total_seconds()
        stats.last_error = str(last_error)
        stats.last_error_time = datetime.utcnow()
        
        raise last_error
    
    async def health_check(self, client_name: str) -> bool:
        """Check health of a specific MCP client"""
        try:
            async with self.get_client(client_name) as client:
                response = await client.send_request("get_server_health", {})
                return response.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed for MCP client {client_name}: {e}")
            return False
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Check health of all MCP clients"""
        results = {}
        
        for client_name in self.clients:
            results[client_name] = {
                "healthy": await self.health_check(client_name),
                "stats": {
                    "total_requests": self.stats[client_name].total_requests,
                    "success_rate": self.stats[client_name].success_rate,
                    "average_request_time": self.stats[client_name].average_request_time,
                    "last_error": self.stats[client_name].last_error,
                    "last_error_time": self.stats[client_name].last_error_time.isoformat() 
                        if self.stats[client_name].last_error_time else None
                }
            }
        
        return results
    
    async def _close_client_pool(self, client_name: str):
        """Close all clients in a pool"""
        if client_name in self.clients:
            for client in self.clients[client_name]:
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.error(f"Error closing MCP client: {e}")
            
            self.clients[client_name].clear()
    
    async def close_all(self):
        """Close all client pools"""
        logger.info("Closing all MCP client pools")
        
        for client_name in list(self.clients.keys()):
            await self._close_client_pool(client_name)
        
        self.clients.clear()
        self.configs.clear()
        self.stats.clear()
        self.client_locks.clear()
        
        logger.info("All MCP client pools closed")
    
    def get_stats(self, client_name: str) -> Optional[MCPClientStats]:
        """Get statistics for a specific client"""
        return self.stats.get(client_name)
    
    def get_all_stats(self) -> Dict[str, MCPClientStats]:
        """Get statistics for all clients"""
        return self.stats.copy()


# Global instance
_mcp_client_pool: Optional[MCPClientPool] = None


async def get_mcp_client_pool() -> MCPClientPool:
    """Get the global MCP client pool instance"""
    global _mcp_client_pool
    
    if _mcp_client_pool is None:
        _mcp_client_pool = MCPClientPool()
        await _mcp_client_pool.initialize()
    
    return _mcp_client_pool


# Convenience functions for common operations
async def execute_mcp_request(
    client_name: str,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    retry: bool = True
) -> Any:
    """Execute an MCP request using the global client pool"""
    pool = await get_mcp_client_pool()
    return await pool.execute_request(client_name, method, params, retry)


async def get_case_context(case_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get case context from MCP server"""
    try:
        # Get case history
        history = await execute_mcp_request(
            "cases_mcp",
            "get_case_history",
            {
                "case_id": case_id,
                "user_id": user_id,
                "include_chat": True,
                "include_analysis": True
            }
        )
        
        # Get similar cases
        similar_cases = await execute_mcp_request(
            "cases_mcp",
            "find_similar_cases",
            {
                "case_id": case_id,
                "user_id": user_id,
                "similarity_threshold": 0.5,
                "limit": 5
            }
        )
        
        # Get symptom patterns
        patterns = await execute_mcp_request(
            "cases_mcp",
            "analyze_patterns",
            {
                "user_id": user_id,
                "pattern_type": "symptoms"
            }
        )
        
        return {
            "case_history": history,
            "similar_cases": similar_cases,
            "symptom_patterns": patterns,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting case context: {e}")
        return None