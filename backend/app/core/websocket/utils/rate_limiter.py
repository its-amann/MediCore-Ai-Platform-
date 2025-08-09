"""
WebSocket Rate Limiter

Implements rate limiting for WebSocket connections to prevent DOS attacks
and ensure fair resource usage.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import ipaddress
from app.core.unified_logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    # Connection limits
    max_connections_per_ip: int = 10
    max_connections_per_user: int = 5
    max_connections_global: int = 1000
    
    # Request rate limits
    max_messages_per_minute: int = 60
    max_messages_per_second: int = 10
    
    # Time windows
    cleanup_interval: int = 300  # 5 minutes
    ban_duration: int = 3600  # 1 hour
    
    # Burst allowance
    burst_multiplier: float = 1.5
    
    # Whitelist for trusted IPs (e.g., internal services)
    whitelisted_ips: list = field(default_factory=list)
    
    # Different limits for authenticated users
    authenticated_multiplier: float = 2.0


@dataclass
class ConnectionInfo:
    """Track connection information"""
    ip: str
    user_id: Optional[str]
    connected_at: datetime
    last_message: datetime
    message_count: int = 0
    violations: int = 0


class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        
        # Connection tracking
        self.connections_by_ip: Dict[str, set] = defaultdict(set)
        self.connections_by_user: Dict[str, set] = defaultdict(set)
        self.connection_info: Dict[str, ConnectionInfo] = {}
        
        # Rate tracking
        self.message_counts: Dict[str, list] = defaultdict(list)  # connection_id -> timestamps
        self.banned_ips: Dict[str, datetime] = {}
        self.banned_users: Dict[str, datetime] = {}
        
        # Global metrics
        self.total_connections = 0
        self.total_messages = 0
        self.total_violations = 0
        
        # Cleanup task
        self._cleanup_task = None
        self._running = False
    
    async def start(self):
        """Start the rate limiter cleanup task"""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("WebSocket rate limiter started")
    
    async def stop(self):
        """Stop the rate limiter cleanup task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket rate limiter stopped")
    
    def is_ip_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for whitelist_entry in self.config.whitelisted_ips:
                if "/" in whitelist_entry:
                    # CIDR notation
                    if ip_obj in ipaddress.ip_network(whitelist_entry):
                        return True
                else:
                    # Single IP
                    if str(ip_obj) == whitelist_entry:
                        return True
        except Exception as e:
            logger.error(f"Error checking IP whitelist: {e}")
        return False
    
    async def check_connection_allowed(
        self,
        connection_id: str,
        ip: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a new connection is allowed
        
        Args:
            connection_id: Unique connection identifier
            ip: Client IP address
            user_id: Optional authenticated user ID
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check if IP is whitelisted
        if self.is_ip_whitelisted(ip):
            return True, None
        
        # Check if IP is banned
        if ip in self.banned_ips:
            ban_expiry = self.banned_ips[ip]
            if datetime.utcnow() < ban_expiry:
                remaining = int((ban_expiry - datetime.utcnow()).total_seconds())
                return False, f"IP banned for {remaining} seconds"
            else:
                # Ban expired
                del self.banned_ips[ip]
        
        # Check if user is banned
        if user_id and user_id in self.banned_users:
            ban_expiry = self.banned_users[user_id]
            if datetime.utcnow() < ban_expiry:
                remaining = int((ban_expiry - datetime.utcnow()).total_seconds())
                return False, f"User banned for {remaining} seconds"
            else:
                # Ban expired
                del self.banned_users[user_id]
        
        # Check global connection limit
        if self.total_connections >= self.config.max_connections_global:
            return False, "Global connection limit reached"
        
        # Check per-IP connection limit
        ip_connections = len(self.connections_by_ip[ip])
        if ip_connections >= self.config.max_connections_per_ip:
            return False, f"Too many connections from IP ({ip_connections}/{self.config.max_connections_per_ip})"
        
        # Check per-user connection limit
        if user_id:
            user_connections = len(self.connections_by_user[user_id])
            max_user_connections = int(self.config.max_connections_per_user * self.config.authenticated_multiplier)
            if user_connections >= max_user_connections:
                return False, f"Too many connections for user ({user_connections}/{max_user_connections})"
        
        return True, None
    
    async def on_connect(
        self,
        connection_id: str,
        ip: str,
        user_id: Optional[str] = None
    ):
        """
        Record a new connection
        
        Args:
            connection_id: Unique connection identifier
            ip: Client IP address
            user_id: Optional authenticated user ID
        """
        now = datetime.utcnow()
        
        # Track connection
        self.connections_by_ip[ip].add(connection_id)
        if user_id:
            self.connections_by_user[user_id].add(connection_id)
        
        self.connection_info[connection_id] = ConnectionInfo(
            ip=ip,
            user_id=user_id,
            connected_at=now,
            last_message=now
        )
        
        self.total_connections += 1
        
        logger.info(
            f"WebSocket connection established: {connection_id} "
            f"(IP: {ip}, User: {user_id or 'anonymous'})"
        )
    
    async def on_disconnect(self, connection_id: str):
        """
        Remove a connection
        
        Args:
            connection_id: Connection to remove
        """
        if connection_id not in self.connection_info:
            return
        
        info = self.connection_info[connection_id]
        
        # Remove from tracking
        self.connections_by_ip[info.ip].discard(connection_id)
        if info.user_id:
            self.connections_by_user[info.user_id].discard(connection_id)
        
        # Clean up empty sets
        if not self.connections_by_ip[info.ip]:
            del self.connections_by_ip[info.ip]
        if info.user_id and not self.connections_by_user[info.user_id]:
            del self.connections_by_user[info.user_id]
        
        # Remove connection info and message history
        del self.connection_info[connection_id]
        if connection_id in self.message_counts:
            del self.message_counts[connection_id]
        
        self.total_connections -= 1
        
        logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def check_message_allowed(
        self,
        connection_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a message is allowed based on rate limits
        
        Args:
            connection_id: Connection sending the message
            
        Returns:
            Tuple of (allowed, reason)
        """
        if connection_id not in self.connection_info:
            return False, "Unknown connection"
        
        info = self.connection_info[connection_id]
        
        # Check if IP is whitelisted
        if self.is_ip_whitelisted(info.ip):
            return True, None
        
        now = datetime.utcnow()
        
        # Get message timestamps for this connection
        timestamps = self.message_counts[connection_id]
        
        # Remove old timestamps (older than 1 minute)
        cutoff_minute = now - timedelta(minutes=1)
        timestamps[:] = [ts for ts in timestamps if ts > cutoff_minute]
        
        # Check per-minute limit
        max_per_minute = self.config.max_messages_per_minute
        if info.user_id:
            max_per_minute = int(max_per_minute * self.config.authenticated_multiplier)
        
        if len(timestamps) >= max_per_minute:
            info.violations += 1
            self.total_violations += 1
            
            # Ban if too many violations
            if info.violations >= 3:
                await self._ban_connection(connection_id, "Rate limit violations")
                return False, "Connection banned due to rate limit violations"
            
            return False, f"Rate limit exceeded ({len(timestamps)}/{max_per_minute} messages per minute)"
        
        # Check per-second limit (burst protection)
        cutoff_second = now - timedelta(seconds=1)
        recent_messages = sum(1 for ts in timestamps if ts > cutoff_second)
        
        max_per_second = int(self.config.max_messages_per_second * self.config.burst_multiplier)
        if info.user_id:
            max_per_second = int(max_per_second * self.config.authenticated_multiplier)
        
        if recent_messages >= max_per_second:
            info.violations += 1
            self.total_violations += 1
            return False, f"Burst limit exceeded ({recent_messages}/{max_per_second} messages per second)"
        
        return True, None
    
    async def on_message(self, connection_id: str):
        """
        Record a message from a connection
        
        Args:
            connection_id: Connection that sent the message
        """
        if connection_id not in self.connection_info:
            return
        
        now = datetime.utcnow()
        
        # Update connection info
        info = self.connection_info[connection_id]
        info.last_message = now
        info.message_count += 1
        
        # Track message timestamp
        self.message_counts[connection_id].append(now)
        
        self.total_messages += 1
    
    async def _ban_connection(self, connection_id: str, reason: str):
        """
        Ban a connection's IP and user
        
        Args:
            connection_id: Connection to ban
            reason: Reason for the ban
        """
        if connection_id not in self.connection_info:
            return
        
        info = self.connection_info[connection_id]
        ban_expiry = datetime.utcnow() + timedelta(seconds=self.config.ban_duration)
        
        # Ban IP
        self.banned_ips[info.ip] = ban_expiry
        
        # Ban user if authenticated
        if info.user_id:
            self.banned_users[info.user_id] = ban_expiry
        
        logger.warning(
            f"Banned connection {connection_id} (IP: {info.ip}, User: {info.user_id}) "
            f"for {self.config.ban_duration} seconds. Reason: {reason}"
        )
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old data"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                
                now = datetime.utcnow()
                
                # Clean up expired bans
                expired_ips = [
                    ip for ip, expiry in self.banned_ips.items()
                    if now > expiry
                ]
                for ip in expired_ips:
                    del self.banned_ips[ip]
                    logger.info(f"Removed expired ban for IP: {ip}")
                
                expired_users = [
                    user_id for user_id, expiry in self.banned_users.items()
                    if now > expiry
                ]
                for user_id in expired_users:
                    del self.banned_users[user_id]
                    logger.info(f"Removed expired ban for user: {user_id}")
                
                # Clean up old message timestamps
                cutoff = now - timedelta(minutes=5)
                for connection_id, timestamps in list(self.message_counts.items()):
                    timestamps[:] = [ts for ts in timestamps if ts > cutoff]
                    if not timestamps and connection_id not in self.connection_info:
                        # Remove empty entries for disconnected connections
                        del self.message_counts[connection_id]
                
                logger.debug(
                    f"Rate limiter cleanup complete. "
                    f"Active connections: {self.total_connections}, "
                    f"Banned IPs: {len(self.banned_ips)}, "
                    f"Banned users: {len(self.banned_users)}"
                )
                
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {e}")
    
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        return {
            "total_connections": self.total_connections,
            "total_messages": self.total_messages,
            "total_violations": self.total_violations,
            "connections_by_ip": {
                ip: len(connections)
                for ip, connections in self.connections_by_ip.items()
            },
            "connections_by_user": {
                user_id: len(connections)
                for user_id, connections in self.connections_by_user.items()
            },
            "banned_ips": len(self.banned_ips),
            "banned_users": len(self.banned_users),
            "config": {
                "max_connections_per_ip": self.config.max_connections_per_ip,
                "max_connections_per_user": self.config.max_connections_per_user,
                "max_messages_per_minute": self.config.max_messages_per_minute,
                "ban_duration": self.config.ban_duration
            }
        }