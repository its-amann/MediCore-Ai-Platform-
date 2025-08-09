"""
Simplified configuration for Medical History Service
Focuses only on Neo4j configuration since auth/server config comes from main app
"""

import os
from typing import Optional
from dataclasses import dataclass, field
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Neo4j database configuration."""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = ""
    database: str = "neo4j"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 100
    connection_acquisition_timeout: int = 60
    connection_timeout: int = 30
    encrypted: bool = False


@dataclass
class ServiceConfig:
    """Service-specific configuration."""
    max_cases_per_query: int = 100
    similarity_threshold: float = 0.7
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    enable_pattern_analysis: bool = True
    max_pattern_results: int = 50
    log_level: str = "INFO"


@dataclass
class MCPConfig:
    """Simplified configuration for Medical History Service."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)
    
    def __post_init__(self):
        """Initialize configuration after creation."""
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Database configuration
        if neo4j_uri := os.getenv("NEO4J_URI"):
            self.database.uri = neo4j_uri
        # Support both NEO4J_USER and NEO4J_USERNAME for compatibility
        if neo4j_user := os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME"):
            self.database.username = neo4j_user
        if neo4j_pass := os.getenv("NEO4J_PASSWORD"):
            self.database.password = neo4j_pass
        if neo4j_db := os.getenv("NEO4J_DATABASE"):
            self.database.database = neo4j_db
        
        # Service configuration
        if max_cases := os.getenv("MCP_MAX_CASES_PER_QUERY"):
            self.service.max_cases_per_query = int(max_cases)
        if threshold := os.getenv("MCP_SIMILARITY_THRESHOLD"):
            self.service.similarity_threshold = float(threshold)
        if enable_cache := os.getenv("MCP_ENABLE_CACHING"):
            self.service.enable_caching = enable_cache.lower() == "true"
        if cache_ttl := os.getenv("MCP_CACHE_TTL"):
            self.service.cache_ttl_seconds = int(cache_ttl)
        if log_level := os.getenv("MCP_LOG_LEVEL") or os.getenv("LOG_LEVEL"):
            self.service.log_level = log_level.upper()


# Global configuration instance
_config: Optional[MCPConfig] = None


def get_config() -> MCPConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = MCPConfig()
    return _config


def set_config(config: MCPConfig):
    """Set the global configuration instance."""
    global _config
    _config = config