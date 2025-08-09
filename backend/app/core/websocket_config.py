"""
WebSocket Configuration for enabling/disabling features
"""

from typing import Dict, Any
import os

class WebSocketConfig:
    """Configuration for WebSocket features that can be toggled"""
    
    def __init__(self):
        # Feature flags with defaults that maintain backward compatibility
        self.features = {
            # Heartbeat/ping-pong feature
            "heartbeat_enabled": os.getenv("WEBSOCKET_HEARTBEAT_ENABLED", "true").lower() == "true",
            "heartbeat_interval": int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30")),
            "heartbeat_timeout": int(os.getenv("WEBSOCKET_HEARTBEAT_TIMEOUT", "10")),
            
            # Connection pooling
            "connection_pooling_enabled": os.getenv("WEBSOCKET_CONNECTION_POOLING", "true").lower() == "true",
            "max_connections_per_user": int(os.getenv("WEBSOCKET_MAX_CONNECTIONS_PER_USER", "5")),
            "max_total_connections": int(os.getenv("WEBSOCKET_MAX_TOTAL_CONNECTIONS", "1000")),
            
            # Connection cleanup
            "cleanup_enabled": os.getenv("WEBSOCKET_CLEANUP_ENABLED", "true").lower() == "true",
            "cleanup_interval": int(os.getenv("WEBSOCKET_CLEANUP_INTERVAL", "300")),
            "stale_connection_timeout": int(os.getenv("WEBSOCKET_STALE_TIMEOUT", "3600")),
            
            # Enhanced error handling
            "enhanced_error_handling": os.getenv("WEBSOCKET_ENHANCED_ERRORS", "true").lower() == "true",
            
            # Connection state tracking
            "connection_state_tracking": os.getenv("WEBSOCKET_STATE_TRACKING", "true").lower() == "true",
            
            # Statistics collection
            "stats_enabled": os.getenv("WEBSOCKET_STATS_ENABLED", "true").lower() == "true",
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(f"{feature}_enabled", False)
    
    def get_feature_config(self, feature: str) -> Dict[str, Any]:
        """Get configuration for a specific feature"""
        config = {}
        for key, value in self.features.items():
            if key.startswith(feature):
                config[key.replace(f"{feature}_", "")] = value
        return config
    
    def disable_all_enhancements(self):
        """Disable all enhancements for maximum backward compatibility"""
        for key in self.features:
            if key.endswith("_enabled"):
                self.features[key] = False

# Global config instance
websocket_config = WebSocketConfig()

# For services that need pure backward compatibility
def use_legacy_websocket_mode():
    """Switch to legacy mode with no enhancements"""
    websocket_config.disable_all_enhancements()