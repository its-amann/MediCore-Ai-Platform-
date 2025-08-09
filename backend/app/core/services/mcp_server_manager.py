"""
MCP Server Manager - Manages MCP server lifecycle with health monitoring and recovery
"""

import asyncio
import os
import subprocess
import sys
import time
import signal
from pathlib import Path
from typing import Dict, Optional, List, Any
from enum import Enum
import psutil
import json
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.unified_logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class MCPServerState(Enum):
    """MCP Server states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    CRASHED = "crashed"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    module_path: str
    host: str = "localhost"
    port: int = 8001
    health_check_endpoint: str = "/health"
    startup_timeout: int = 30
    health_check_interval: int = 30
    max_restart_attempts: int = 3
    restart_backoff_base: float = 2.0
    env_vars: Dict[str, str] = field(default_factory=dict)
    command_args: List[str] = field(default_factory=list)


@dataclass
class MCPServerInfo:
    """Information about a running MCP server"""
    config: MCPServerConfig
    state: MCPServerState = MCPServerState.STOPPED
    process: Optional[subprocess.Popen] = None
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    restart_count: int = 0
    last_restart_time: Optional[datetime] = None
    error_message: Optional[str] = None


class MCPServerManager:
    """Manages MCP server processes with health monitoring and automatic recovery"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerInfo] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self.shutdown_event = asyncio.Event()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the MCP server manager"""
        if self._initialized:
            return
            
        logger.info("Initializing MCP Server Manager")
        
        # Register default MCP servers
        if settings.mcp_server_enabled:
            # Cases Chat MCP Server
            cases_mcp_config = MCPServerConfig(
                name="cases_mcp",
                module_path="app.microservices.cases_chat.mcp_server.run_mcp_server",
                host=settings.mcp_server_host,
                port=settings.mcp_server_port,
                env_vars={
                    "NEO4J_URI": settings.neo4j_uri,
                    "NEO4J_USER": settings.neo4j_user,
                    "NEO4J_PASSWORD": settings.neo4j_password,
                    "NEO4J_DATABASE": settings.neo4j_database,
                    "PYTHONPATH": str(Path.cwd()),
                    "LOG_LEVEL": settings.log_level
                }
            )
            self.register_server(cases_mcp_config)
        
        # TODO: Add other MCP servers (imaging, voice) when ready
        
        self._initialized = True
        logger.info("MCP Server Manager initialized")
    
    def register_server(self, config: MCPServerConfig):
        """Register an MCP server configuration"""
        if config.name in self.servers:
            logger.warning(f"MCP server {config.name} already registered, updating configuration")
        
        self.servers[config.name] = MCPServerInfo(config=config)
        logger.info(f"Registered MCP server: {config.name}")
    
    async def start_server(self, server_name: str) -> bool:
        """Start a specific MCP server"""
        if server_name not in self.servers:
            logger.error(f"Unknown MCP server: {server_name}")
            return False
        
        server_info = self.servers[server_name]
        
        if server_info.state in [MCPServerState.RUNNING, MCPServerState.STARTING]:
            logger.warning(f"MCP server {server_name} is already {server_info.state.value}")
            return True
        
        logger.info(f"Starting MCP server: {server_name}")
        server_info.state = MCPServerState.STARTING
        server_info.error_message = None
        
        try:
            # Prepare environment variables
            env = os.environ.copy()
            env.update(server_info.config.env_vars)
            
            # Build command
            cmd = [sys.executable, "-m", server_info.config.module_path]
            cmd.extend(server_info.config.command_args)
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            server_info.process = process
            server_info.pid = process.pid
            server_info.start_time = datetime.utcnow()
            
            # Start output monitoring tasks
            asyncio.create_task(self._monitor_output(server_name, process.stdout, "stdout"))
            asyncio.create_task(self._monitor_output(server_name, process.stderr, "stderr"))
            
            # Wait for server to be ready
            if await self._wait_for_server_ready(server_name):
                server_info.state = MCPServerState.RUNNING
                logger.info(f"MCP server {server_name} started successfully (PID: {server_info.pid})")
                
                # Start health monitoring
                if server_name in self.health_check_tasks:
                    self.health_check_tasks[server_name].cancel()
                self.health_check_tasks[server_name] = asyncio.create_task(
                    self._health_check_loop(server_name)
                )
                
                return True
            else:
                # Server failed to start
                await self._stop_server_process(server_info)
                server_info.state = MCPServerState.CRASHED
                server_info.error_message = "Failed to start - health check timeout"
                logger.error(f"MCP server {server_name} failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Error starting MCP server {server_name}: {e}", exc_info=True)
            server_info.state = MCPServerState.CRASHED
            server_info.error_message = str(e)
            return False
    
    async def stop_server(self, server_name: str, timeout: int = 10) -> bool:
        """Stop a specific MCP server gracefully"""
        if server_name not in self.servers:
            logger.error(f"Unknown MCP server: {server_name}")
            return False
        
        server_info = self.servers[server_name]
        
        if server_info.state == MCPServerState.STOPPED:
            logger.warning(f"MCP server {server_name} is already stopped")
            return True
        
        logger.info(f"Stopping MCP server: {server_name}")
        server_info.state = MCPServerState.STOPPING
        
        # Cancel health check task
        if server_name in self.health_check_tasks:
            self.health_check_tasks[server_name].cancel()
            del self.health_check_tasks[server_name]
        
        # Stop the process
        success = await self._stop_server_process(server_info, timeout)
        
        server_info.state = MCPServerState.STOPPED
        server_info.process = None
        server_info.pid = None
        
        logger.info(f"MCP server {server_name} stopped")
        return success
    
    async def restart_server(self, server_name: str) -> bool:
        """Restart a specific MCP server"""
        logger.info(f"Restarting MCP server: {server_name}")
        
        # Stop the server
        await self.stop_server(server_name)
        
        # Wait a bit before restarting
        await asyncio.sleep(2)
        
        # Start the server
        return await self.start_server(server_name)
    
    async def start_all(self):
        """Start all registered MCP servers"""
        logger.info("Starting all MCP servers")
        
        tasks = []
        for server_name in self.servers:
            tasks.append(self.start_server(server_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Started {success_count}/{len(self.servers)} MCP servers")
    
    async def stop_all(self):
        """Stop all MCP servers"""
        logger.info("Stopping all MCP servers")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        tasks = []
        for server_name in self.servers:
            tasks.append(self.stop_server(server_name))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("All MCP servers stopped")
    
    async def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific MCP server"""
        if server_name not in self.servers:
            return {"error": f"Unknown server: {server_name}"}
        
        server_info = self.servers[server_name]
        
        status = {
            "name": server_name,
            "state": server_info.state.value,
            "pid": server_info.pid,
            "start_time": server_info.start_time.isoformat() if server_info.start_time else None,
            "uptime": str(datetime.utcnow() - server_info.start_time) if server_info.start_time else None,
            "last_health_check": server_info.last_health_check.isoformat() if server_info.last_health_check else None,
            "health_check_failures": server_info.health_check_failures,
            "restart_count": server_info.restart_count,
            "last_restart_time": server_info.last_restart_time.isoformat() if server_info.last_restart_time else None,
            "error_message": server_info.error_message,
            "config": {
                "host": server_info.config.host,
                "port": server_info.config.port,
                "module": server_info.config.module_path
            }
        }
        
        # Add process metrics if running
        if server_info.pid and server_info.state == MCPServerState.RUNNING:
            try:
                process = psutil.Process(server_info.pid)
                status["metrics"] = {
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "num_threads": process.num_threads(),
                    "open_files": len(process.open_files())
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return status
    
    async def get_all_server_status(self) -> Dict[str, Any]:
        """Get status of all MCP servers"""
        statuses = {}
        
        for server_name in self.servers:
            statuses[server_name] = await self.get_server_status(server_name)
        
        return {
            "servers": statuses,
            "total": len(self.servers),
            "running": sum(1 for s in self.servers.values() if s.state == MCPServerState.RUNNING),
            "stopped": sum(1 for s in self.servers.values() if s.state == MCPServerState.STOPPED),
            "unhealthy": sum(1 for s in self.servers.values() if s.state == MCPServerState.UNHEALTHY)
        }
    
    async def _wait_for_server_ready(self, server_name: str) -> bool:
        """Wait for server to be ready by checking health endpoint"""
        server_info = self.servers[server_name]
        config = server_info.config
        
        start_time = time.time()
        url = f"http://{config.host}:{config.port}{config.health_check_endpoint}"
        
        logger.info(f"Waiting for MCP server {server_name} to be ready at {url}")
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < config.startup_timeout:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            logger.info(f"MCP server {server_name} is ready")
                            return True
                except:
                    pass
                
                # Check if process is still alive
                if server_info.process and server_info.process.poll() is not None:
                    logger.error(f"MCP server {server_name} process died during startup")
                    return False
                
                await asyncio.sleep(1)
        
        logger.error(f"MCP server {server_name} startup timeout")
        return False
    
    async def _health_check_loop(self, server_name: str):
        """Continuous health check loop for a server"""
        server_info = self.servers[server_name]
        config = server_info.config
        url = f"http://{config.host}:{config.port}{config.health_check_endpoint}"
        
        logger.info(f"Starting health check loop for MCP server {server_name}")
        
        async with aiohttp.ClientSession() as session:
            while not self.shutdown_event.is_set() and server_info.state == MCPServerState.RUNNING:
                try:
                    # Perform health check
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            # Healthy
                            server_info.last_health_check = datetime.utcnow()
                            server_info.health_check_failures = 0
                            
                            if server_info.state == MCPServerState.UNHEALTHY:
                                server_info.state = MCPServerState.RUNNING
                                logger.info(f"MCP server {server_name} recovered")
                        else:
                            # Unhealthy response
                            raise Exception(f"Health check returned status {response.status}")
                            
                except Exception as e:
                    # Health check failed
                    server_info.health_check_failures += 1
                    logger.warning(
                        f"Health check failed for MCP server {server_name}: {e} "
                        f"(failures: {server_info.health_check_failures})"
                    )
                    
                    if server_info.health_check_failures >= 3:
                        server_info.state = MCPServerState.UNHEALTHY
                        server_info.error_message = f"Health check failures: {server_info.health_check_failures}"
                        
                        # Attempt restart if within limits
                        if server_info.restart_count < config.max_restart_attempts:
                            await self._attempt_restart(server_name)
                        else:
                            logger.error(
                                f"MCP server {server_name} exceeded max restart attempts "
                                f"({config.max_restart_attempts})"
                            )
                
                # Wait for next check
                await asyncio.sleep(config.health_check_interval)
        
        logger.info(f"Health check loop ended for MCP server {server_name}")
    
    async def _attempt_restart(self, server_name: str):
        """Attempt to restart a failed server with exponential backoff"""
        server_info = self.servers[server_name]
        
        # Calculate backoff time
        backoff_time = server_info.config.restart_backoff_base ** server_info.restart_count
        
        logger.info(
            f"Attempting restart of MCP server {server_name} "
            f"(attempt {server_info.restart_count + 1}/{server_info.config.max_restart_attempts}) "
            f"after {backoff_time}s backoff"
        )
        
        await asyncio.sleep(backoff_time)
        
        server_info.restart_count += 1
        server_info.last_restart_time = datetime.utcnow()
        
        # Restart the server
        if await self.restart_server(server_name):
            logger.info(f"Successfully restarted MCP server {server_name}")
            # Don't reset restart count immediately - wait for stable operation
        else:
            logger.error(f"Failed to restart MCP server {server_name}")
    
    async def _stop_server_process(self, server_info: MCPServerInfo, timeout: int = 10) -> bool:
        """Stop a server process gracefully, then forcefully if needed"""
        if not server_info.process:
            return True
        
        try:
            # Try graceful shutdown first
            if sys.platform == "win32":
                # On Windows, send CTRL_BREAK_EVENT
                server_info.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # On Unix, send SIGTERM
                server_info.process.terminate()
            
            # Wait for process to exit
            try:
                server_info.process.wait(timeout=timeout)
                logger.info(f"MCP server process {server_info.pid} terminated gracefully")
                return True
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                logger.warning(f"MCP server process {server_info.pid} did not terminate gracefully, forcing kill")
                server_info.process.kill()
                server_info.process.wait(timeout=5)
                return True
                
        except Exception as e:
            logger.error(f"Error stopping MCP server process {server_info.pid}: {e}")
            return False
    
    async def _monitor_output(self, server_name: str, stream, stream_name: str):
        """Monitor and log server output"""
        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(None, stream.readline)
                if not line:
                    break
                
                line = line.strip()
                if line:
                    logger.info(f"MCP[{server_name}] {stream_name}: {line}")
                    
        except Exception as e:
            logger.error(f"Error monitoring {stream_name} for MCP server {server_name}: {e}")


# Global instance
_mcp_server_manager: Optional[MCPServerManager] = None


async def get_mcp_server_manager() -> MCPServerManager:
    """Get the global MCP server manager instance"""
    global _mcp_server_manager
    
    if _mcp_server_manager is None:
        _mcp_server_manager = MCPServerManager()
        await _mcp_server_manager.initialize()
    
    return _mcp_server_manager