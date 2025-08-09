"""
Configuration module for the Collaboration Microservice.

This module handles all configuration settings including environment variables,
database connections, API keys, and service-specific settings.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Configuration settings for the Collaboration Microservice.
    """
    
    # Service Configuration
    SERVICE_NAME: str = "collaboration-microservice"
    HOST: str = os.getenv("COLLABORATION_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("COLLABORATION_PORT", "8002"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Neo4j Database Configuration
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # Neo4j connection pool settings
    NEO4J_MAX_CONNECTION_LIFETIME: int = int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "3600"))
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "50"))
    NEO4J_CONNECTION_ACQUISITION_TIMEOUT: int = int(os.getenv("NEO4J_CONNECTION_ACQUISITION_TIMEOUT", "60"))
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_MESSAGE_QUEUE_SIZE: int = 1000
    WS_MAX_CONNECTIONS_PER_ROOM: int = 50
    WS_MAX_MESSAGE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Room Configuration
    ROOM_DEFAULT_EXPIRY_HOURS: int = 24
    ROOM_MAX_PARTICIPANTS: int = 20
    ROOM_CLEANUP_INTERVAL: int = 3600  # 1 hour in seconds
    ROOM_IDLE_TIMEOUT_MINUTES: int = 60
    
    # Chat Configuration
    CHAT_MAX_MESSAGE_LENGTH: int = 5000
    CHAT_HISTORY_LIMIT: int = 100
    CHAT_FILE_UPLOAD_MAX_SIZE: int = 50 * 1024 * 1024  # 50MB
    CHAT_ALLOWED_FILE_TYPES: List[str] = [
        ".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", 
        ".gif", ".bmp", ".svg", ".csv", ".xlsx", ".xls"
    ]
    
    # Notification Configuration
    NOTIFICATION_BATCH_SIZE: int = 100
    NOTIFICATION_PROCESSING_INTERVAL: int = 10  # seconds
    NOTIFICATION_RETENTION_DAYS: int = 30
    EMAIL_NOTIFICATIONS_ENABLED: bool = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "False").lower() == "true"
    
    # AI Assistant Configuration
    AI_MODEL_NAME: str = os.getenv("AI_MODEL_NAME", "gemini-pro")
    AI_MAX_TOKENS: int = 2048
    AI_TEMPERATURE: float = 0.7
    AI_TIMEOUT_SECONDS: int = 30
    AI_RETRY_ATTEMPTS: int = 3
    AI_CONTEXT_WINDOW_SIZE: int = 10  # Number of previous messages to include
    
    # Service URLs (for integration with main app)
    MAIN_APP_URL: str = os.getenv("MAIN_APP_URL", "http://localhost:8000")
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", f"{MAIN_APP_URL}/auth")
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", f"{MAIN_APP_URL}/users")
    CASES_SERVICE_URL: str = os.getenv("CASES_SERVICE_URL", f"{MAIN_APP_URL}/cases")
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://localhost:8000"
    ).split(",")
    
    # File Storage Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    TEMP_FILE_EXPIRY_HOURS: int = 24
    
    # Video/Audio Configuration
    VIDEO_CODEC: str = "VP8"
    AUDIO_CODEC: str = "opus"
    MAX_VIDEO_BITRATE: int = 1000000  # 1 Mbps
    MAX_AUDIO_BITRATE: int = 64000    # 64 kbps
    
    # WebRTC ICE/TURN Configuration
    STUN_SERVERS: str = os.getenv("STUN_SERVERS", "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302")
    TURN_SERVER_URL: Optional[str] = os.getenv("TURN_SERVER_URL")  # e.g., "turn:turn.example.com:3478,turns:turn.example.com:5349"
    TURN_SECRET: Optional[str] = os.getenv("TURN_SECRET")  # Shared secret for TURN authentication
    TURN_TTL: int = int(os.getenv("TURN_TTL", "86400"))  # TURN credential TTL in seconds (default 24 hours)
    
    # Recording Configuration
    RECORDING_ENABLED: bool = os.getenv("RECORDING_ENABLED", "True").lower() == "true"
    RECORDING_FORMAT: str = os.getenv("RECORDING_FORMAT", "webm")
    RECORDING_VIDEO_CODEC: str = os.getenv("RECORDING_VIDEO_CODEC", "vp8")
    RECORDING_AUDIO_CODEC: str = os.getenv("RECORDING_AUDIO_CODEC", "opus")
    RECORDING_BITRATE: int = int(os.getenv("RECORDING_BITRATE", "1000000"))  # 1 Mbps
    RECORDING_STORAGE_PATH: str = os.getenv("RECORDING_STORAGE_PATH", "/recordings")
    RECORDING_BASE_URL: str = os.getenv("RECORDING_BASE_URL", "https://recordings.example.com")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    # Performance Configuration
    CACHE_TTL: int = 3600  # 1 hour
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    CONNECTION_POOL_SIZE: int = 20
    
    # Feature Flags
    ENABLE_VIDEO_RECORDING: bool = os.getenv("ENABLE_VIDEO_RECORDING", "False").lower() == "true"
    ENABLE_SCREEN_SHARING: bool = os.getenv("ENABLE_SCREEN_SHARING", "True").lower() == "true"
    ENABLE_AI_ASSISTANT: bool = os.getenv("ENABLE_AI_ASSISTANT", "True").lower() == "true"
    ENABLE_FILE_SHARING: bool = os.getenv("ENABLE_FILE_SHARING", "True").lower() == "true"
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("GEMINI_API_KEY")
    def validate_gemini_api_key(cls, v):
        """Validate that Gemini API key is provided if AI assistant is enabled."""
        if not v and cls.ENABLE_AI_ASSISTANT:
            raise ValueError("GEMINI_API_KEY is required when AI assistant is enabled")
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables from main app


# Create global settings instance
settings = Settings()

# Export commonly used settings
SECRET_KEY = settings.SECRET_KEY
DEBUG = settings.DEBUG
NEO4J_URI = settings.NEO4J_URI
NEO4J_USER = settings.NEO4J_USER
NEO4J_PASSWORD = settings.NEO4J_PASSWORD