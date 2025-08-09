"""
Cases Chat Service Configuration
Environment-specific settings and configuration management
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Service configuration settings"""
    
    # Service Information
    SERVICE_NAME: str = "cases_chat"
    SERVICE_VERSION: str = "1.0.0"
    
    # API Configuration
    API_PREFIX: str = "/api/v1/cases-chat"
    
    # Database Configuration
    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        env="NEO4J_URI"
    )
    NEO4J_USER: str = Field(
        default="neo4j",
        env="NEO4J_USER"
    )
    NEO4J_PASSWORD: str = Field(
        default="password",
        env="NEO4J_PASSWORD"
    )
    NEO4J_DATABASE: str = Field(
        default="neo4j",
        env="NEO4J_DATABASE"
    )
    
    # AI Service Configuration
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        env="GROQ_API_KEY"
    )
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        env="GEMINI_API_KEY"
    )
    
    # Model Configuration
    DEFAULT_AI_MODEL: str = "mixtral-8x7b-32768"
    DEFAULT_TEMPERATURE: float = 0.3
    DEFAULT_MAX_TOKENS: int = 500
    
    # MCP Server Configuration
    MCP_SERVER_URL: Optional[str] = Field(
        default=None,
        env="MCP_SERVER_URL"
    )
    MCP_SERVER_TIMEOUT: int = Field(
        default=30,
        env="MCP_SERVER_TIMEOUT"
    )
    ENABLE_MCP: bool = Field(
        default=True,
        env="ENABLE_MCP"
    )
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_CONNECTION_TIMEOUT: int = 60
    
    # Security Configuration
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-here",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL"
    )
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File Storage
    MEDIA_UPLOAD_PATH: str = Field(
        default="/tmp/cases_chat/media",
        env="MEDIA_UPLOAD_PATH"
    )
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB
    
    # Cache Configuration
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 3600  # 1 hour
    
    # Feature Flags
    ENABLE_AUDIO_SUPPORT: bool = True
    ENABLE_IMAGE_SUPPORT: bool = True
    ENABLE_MULTI_DOCTOR_CHAT: bool = True
    ENABLE_CASE_REPORTS: bool = True
    
    # Performance Settings
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT: int = 120  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from environment


# Create settings instance
settings = Settings()

# Ensure required directories exist
os.makedirs(settings.MEDIA_UPLOAD_PATH, exist_ok=True)