"""
WebSocket Token Refresh Manager

Monitors token expiry for WebSocket connections and notifies clients
when tokens need to be refreshed.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
import jwt
from app.core.config import settings
from app.core.unified_logging import get_logger

logger = get_logger(__name__)


class WebSocketTokenRefresh:
    """Manages token refresh for WebSocket connections"""
    
    def __init__(self, websocket_manager):
        """
        Initialize token refresh manager
        
        Args:
            websocket_manager: Reference to the WebSocket manager
        """
        self.websocket_manager = websocket_manager
        self.refresh_tasks: Dict[str, asyncio.Task] = {}
        self.monitored_connections: Set[str] = set()
        self._shutdown = False
        
        # Configuration
        self.refresh_threshold = 300  # 5 minutes before expiry
        self.check_interval = 60  # Check every minute
        
        # Start monitoring task
        self._monitor_task = None
    
    async def start_monitoring(self):
        """Start the token monitoring task"""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_tokens())
            logger.info("WebSocket token monitoring started")
    
    async def add_connection(self, connection_id: str, token: str, user_info: Dict[str, any]):
        """
        Add a connection for token monitoring
        
        Args:
            connection_id: WebSocket connection ID
            token: JWT token to monitor
            user_info: User information including token expiry
        """
        try:
            # Get token expiry from user_info
            token_exp = user_info.get("token_exp")
            if not token_exp:
                # Try to decode token to get expiry
                try:
                    payload = jwt.decode(
                        token,
                        settings.secret_key,
                        algorithms=[settings.algorithm],
                        options={"verify_exp": False}
                    )
                    token_exp = payload.get("exp")
                except Exception as e:
                    logger.error(f"Failed to decode token for monitoring: {e}")
                    return
            
            if token_exp:
                # Calculate when to send refresh notification
                exp_time = datetime.fromtimestamp(token_exp)
                refresh_time = exp_time - timedelta(seconds=self.refresh_threshold)
                now = datetime.utcnow()
                
                if refresh_time > now:
                    # Schedule refresh notification
                    delay = (refresh_time - now).total_seconds()
                    task = asyncio.create_task(
                        self._schedule_refresh_notification(connection_id, delay)
                    )
                    self.refresh_tasks[connection_id] = task
                    self.monitored_connections.add(connection_id)
                    
                    logger.info(
                        f"Scheduled token refresh notification for {connection_id} "
                        f"in {delay:.0f} seconds"
                    )
                else:
                    # Token already needs refresh
                    await self._send_refresh_notification(connection_id)
                    
        except Exception as e:
            logger.error(f"Error adding connection for token monitoring: {e}")
    
    async def remove_connection(self, connection_id: str):
        """
        Remove a connection from token monitoring
        
        Args:
            connection_id: WebSocket connection ID to remove
        """
        # Cancel scheduled task if exists
        if connection_id in self.refresh_tasks:
            self.refresh_tasks[connection_id].cancel()
            del self.refresh_tasks[connection_id]
        
        # Remove from monitored connections
        self.monitored_connections.discard(connection_id)
        
        logger.debug(f"Removed {connection_id} from token monitoring")
    
    async def _schedule_refresh_notification(self, connection_id: str, delay: float):
        """
        Schedule a refresh notification after delay
        
        Args:
            connection_id: Connection to notify
            delay: Seconds to wait before notification
        """
        try:
            await asyncio.sleep(delay)
            await self._send_refresh_notification(connection_id)
        except asyncio.CancelledError:
            logger.debug(f"Refresh notification cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error in scheduled refresh notification: {e}")
    
    async def _send_refresh_notification(self, connection_id: str):
        """
        Send token refresh notification to client
        
        Args:
            connection_id: Connection to notify
        """
        try:
            # Check if connection still exists
            if connection_id not in self.websocket_manager._connections:
                logger.debug(f"Connection {connection_id} no longer exists")
                return
            
            # Send refresh notification
            await self.websocket_manager._send_message(connection_id, {
                "type": "token_refresh_required",
                "message": "Your authentication token will expire soon. Please refresh it.",
                "action": "refresh_token",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Sent token refresh notification to {connection_id}")
            
            # Remove from monitoring (client should reconnect with new token)
            await self.remove_connection(connection_id)
            
        except Exception as e:
            logger.error(f"Error sending refresh notification: {e}")
    
    async def _monitor_tokens(self):
        """
        Background task to monitor all tokens periodically
        """
        while not self._shutdown:
            try:
                # Check all monitored connections
                connections_to_check = list(self.monitored_connections)
                current_time = datetime.utcnow()
                
                for connection_id in connections_to_check:
                    # Skip if connection no longer exists
                    if connection_id not in self.websocket_manager._connections:
                        await self.remove_connection(connection_id)
                        continue
                    
                    # Get connection info
                    connection = self.websocket_manager._connections[connection_id]
                    if hasattr(connection, 'token_exp'):
                        try:
                            exp_time = datetime.fromtimestamp(connection.token_exp)
                            time_until_expiry = (exp_time - current_time).total_seconds()
                            
                            # Check if token needs refresh
                            if time_until_expiry <= self.refresh_threshold:
                                await self._send_refresh_notification(connection_id)
                        except Exception as e:
                            logger.error(f"Error checking token expiry for {connection_id}: {e}")
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in token monitor: {e}")
                await asyncio.sleep(30)  # Wait before retry
    
    async def handle_token_refreshed(self, connection_id: str, new_token: str):
        """
        Handle when a client has refreshed their token
        
        Args:
            connection_id: Connection that refreshed token
            new_token: New JWT token
        """
        try:
            # Decode new token to get expiry
            payload = jwt.decode(
                new_token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                options={"verify_exp": False}
            )
            
            user_info = {
                "token_exp": payload.get("exp"),
                "user_id": payload.get("sub") or payload.get("user_id"),
                "username": payload.get("username") or payload.get("name")
            }
            
            # Add back to monitoring with new token
            await self.add_connection(connection_id, new_token, user_info)
            
            # Send confirmation
            await self.websocket_manager._send_message(connection_id, {
                "type": "token_refresh_acknowledged",
                "message": "Token refresh successful",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Token refreshed for {connection_id}")
            
        except Exception as e:
            logger.error(f"Error handling token refresh: {e}")
    
    async def shutdown(self):
        """Shutdown token refresh manager"""
        logger.info("Shutting down token refresh manager...")
        self._shutdown = True
        
        # Cancel monitor task
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all refresh tasks
        for task in self.refresh_tasks.values():
            task.cancel()
        
        self.refresh_tasks.clear()
        self.monitored_connections.clear()
        
        logger.info("Token refresh manager shutdown complete")
    
    def get_stats(self) -> Dict[str, any]:
        """Get token monitoring statistics"""
        return {
            "monitored_connections": len(self.monitored_connections),
            "scheduled_refreshes": len(self.refresh_tasks),
            "refresh_threshold": self.refresh_threshold,
            "check_interval": self.check_interval
        }