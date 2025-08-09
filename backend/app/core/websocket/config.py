"""
WebSocket Configuration Management

Centralized configuration for the unified WebSocket system.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import os


class ConnectionMode(str, Enum):
    """WebSocket connection modes"""
    SINGLE = "single"           # One connection per user
    MULTIPLE = "multiple"       # Multiple connections per user allowed
    MANAGED = "managed"         # System manages connection limits


class AuthMode(str, Enum):
    """Authentication modes for WebSocket connections"""
    TOKEN = "token"             # JWT token authentication
    SESSION = "session"         # Session-based authentication
    NONE = "none"              # No authentication (development only)


@dataclass
class ExtensionConfig:
    """Configuration for WebSocket extensions"""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 100  # Lower numbers = higher priority


@dataclass
class WebSocketConfig:
    """Unified WebSocket configuration"""
    
    # Connection Management
    max_connections_per_user: int = 5
    max_total_connections: int = 1000
    connection_mode: ConnectionMode = ConnectionMode.MANAGED
    connection_timeout: int = 30  # seconds
    
    # Heartbeat Configuration
    heartbeat_interval: int = 30  # seconds
    heartbeat_timeout: int = 10   # seconds
    enable_heartbeat: bool = True
    
    # Cleanup Configuration
    cleanup_interval: int = 300   # 5 minutes
    stale_connection_threshold: int = 3600  # 1 hour
    enable_auto_cleanup: bool = True
    
    # Authentication
    auth_mode: AuthMode = AuthMode.TOKEN
    auth_required: bool = True
    token_validation_endpoint: Optional[str] = None
    
    # Message Handling
    max_message_size: int = 1024 * 1024  # 1MB
    enable_message_compression: bool = True
    message_queue_size: int = 100
    
    # Extension System
    extensions: Dict[str, ExtensionConfig] = field(default_factory=dict)
    enable_extensions: bool = True
    extension_discovery_paths: List[str] = field(default_factory=list)
    
    # Logging and Monitoring
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_interval: int = 60  # seconds
    
    # Security
    enable_cors: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 100
    enable_rate_limiting: bool = True
    
    # Development
    debug_mode: bool = False
    enable_message_logging: bool = False
    
    @classmethod
    def from_env(cls) -> 'WebSocketConfig':
        """Create configuration from environment variables"""
        return cls(
            max_connections_per_user=int(os.getenv('WS_MAX_CONNECTIONS_PER_USER', '5')),
            max_total_connections=int(os.getenv('WS_MAX_TOTAL_CONNECTIONS', '1000')),
            connection_timeout=int(os.getenv('WS_CONNECTION_TIMEOUT', '30')),
            heartbeat_interval=int(os.getenv('WS_HEARTBEAT_INTERVAL', '30')),
            heartbeat_timeout=int(os.getenv('WS_HEARTBEAT_TIMEOUT', '10')),
            cleanup_interval=int(os.getenv('WS_CLEANUP_INTERVAL', '300')),
            stale_connection_threshold=int(os.getenv('WS_STALE_THRESHOLD', '3600')),
            auth_mode=AuthMode(os.getenv('WS_AUTH_MODE', 'token')),
            auth_required=os.getenv('WS_AUTH_REQUIRED', 'true').lower() == 'true',
            max_message_size=int(os.getenv('WS_MAX_MESSAGE_SIZE', str(1024 * 1024))),
            rate_limit_per_minute=int(os.getenv('WS_RATE_LIMIT', '100')),
            debug_mode=os.getenv('WS_DEBUG_MODE', 'false').lower() == 'true',
            log_level=os.getenv('WS_LOG_LEVEL', 'INFO'),
        )
    
    def register_extension(self, name: str, config: ExtensionConfig):
        """Register an extension configuration"""
        self.extensions[name] = config
    
    def get_extension_config(self, name: str) -> Optional[ExtensionConfig]:
        """Get configuration for a specific extension"""
        return self.extensions.get(name)
    
    def is_extension_enabled(self, name: str) -> bool:
        """Check if an extension is enabled"""
        ext_config = self.extensions.get(name)
        return ext_config is not None and ext_config.enabled and self.enable_extensions
    
    def get_sorted_extensions(self) -> List[ExtensionConfig]:
        """Get extensions sorted by priority (higher priority first)"""
        return sorted(
            [ext for ext in self.extensions.values() if ext.enabled],
            key=lambda x: x.priority
        )


# Default configuration instance
default_config = WebSocketConfig()

# Environment-based configuration
env_config = WebSocketConfig.from_env()

# For development/testing - override auth_required if WS_AUTH_REQUIRED is explicitly set to false
if os.getenv('WS_AUTH_REQUIRED', '').lower() == 'false':
    print("[WebSocket Config] Authentication disabled via WS_AUTH_REQUIRED=false")
    env_config.auth_required = False
    default_config.auth_required = False