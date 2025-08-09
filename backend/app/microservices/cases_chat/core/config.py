"""
Cases Chat Service Configuration
Centralized configuration management with enhanced settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Enhanced service configuration settings"""
    
    # Service Information
    service_name: str = "cases_chat"
    service_version: str = "1.0.0"
    environment: str = Field("development", env="ENVIRONMENT")
    
    # API Configuration
    api_prefix: str = "/api/v1/cases-chat"
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8001, env="API_PORT")
    
    # Database Configuration
    neo4j_uri: str = Field("bolt://localhost:7687", env="NEO4J_URI")
    neo4j_username: str = Field("neo4j", env="NEO4J_USER")  # Use NEO4J_USER to match main app
    neo4j_password: str = Field("medical123", env="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", env="NEO4J_DATABASE")
    neo4j_connection_timeout: int = Field(30, env="NEO4J_CONNECTION_TIMEOUT")
    neo4j_max_connection_pool_size: int = Field(50, env="NEO4J_MAX_CONNECTION_POOL_SIZE")
    
    # AI Service Configuration
    gemini_api_key: str = Field("", env="GEMINI_API_KEY")  # Will get from env
    groq_api_key: str = Field("", env="GROQ_API_KEY")  # Will get from env
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    # Model Configuration
    default_ai_provider: str = Field("gemini", env="DEFAULT_AI_PROVIDER")
    default_ai_model: str = Field("gemini-pro", env="DEFAULT_AI_MODEL")
    default_temperature: float = Field(0.3, env="DEFAULT_TEMPERATURE")
    default_max_tokens: int = Field(1000, env="DEFAULT_MAX_TOKENS")
    ai_request_timeout: int = Field(60, env="AI_REQUEST_TIMEOUT")
    
    # MCP Server Configuration
    mcp_server_enabled: bool = Field(False, env="MCP_SERVER_ENABLED")
    mcp_server_host: str = Field("localhost", env="MCP_SERVER_HOST")
    mcp_server_port: int = Field(8000, env="MCP_SERVER_PORT")
    mcp_server_timeout: int = Field(30, env="MCP_SERVER_TIMEOUT")
    mcp_retry_attempts: int = Field(3, env="MCP_RETRY_ATTEMPTS")
    mcp_retry_delay: int = Field(5, env="MCP_RETRY_DELAY")
    
    # Media Configuration
    max_file_size: int = Field(50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_file_types: List[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx", ".txt", ".md"],
        env="ALLOWED_FILE_TYPES"
    )
    media_storage_backend: str = Field("local", env="MEDIA_STORAGE_BACKEND")
    media_upload_path: str = Field("/tmp/cases_chat/media", env="MEDIA_UPLOAD_PATH")
    media_url_prefix: str = Field("/media", env="MEDIA_URL_PREFIX")
    enable_media_analysis: bool = Field(True, env="ENABLE_MEDIA_ANALYSIS")
    
    # Performance Configuration
    max_context_messages: int = Field(50, env="MAX_CONTEXT_MESSAGES")
    context_window_tokens: int = Field(4000, env="CONTEXT_WINDOW_TOKENS")
    message_batch_size: int = Field(100, env="MESSAGE_BATCH_SIZE")
    max_concurrent_requests: int = Field(100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(120, env="REQUEST_TIMEOUT")
    
    # WebSocket Configuration
    ws_heartbeat_interval: int = Field(30, env="WS_HEARTBEAT_INTERVAL")
    ws_connection_timeout: int = Field(60, env="WS_CONNECTION_TIMEOUT")
    ws_max_connections_per_case: int = Field(10, env="WS_MAX_CONNECTIONS_PER_CASE")
    ws_message_queue_size: int = Field(1000, env="WS_MESSAGE_QUEUE_SIZE")
    
    # Security Configuration
    enable_message_encryption: bool = Field(False, env="ENABLE_MESSAGE_ENCRYPTION")
    session_timeout_minutes: int = Field(60, env="SESSION_TIMEOUT_MINUTES")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS")
    enable_rate_limiting: bool = Field(True, env="ENABLE_RATE_LIMITING")
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(60, env="RATE_LIMIT_WINDOW")
    
    # Cache Configuration
    enable_cache: bool = Field(True, env="ENABLE_CACHE")
    cache_ttl: int = Field(3600, env="CACHE_TTL")
    cache_backend: str = Field("memory", env="CACHE_BACKEND")
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    # Feature Flags
    enable_audio_support: bool = Field(True, env="ENABLE_AUDIO_SUPPORT")
    enable_image_support: bool = Field(True, env="ENABLE_IMAGE_SUPPORT")
    enable_multi_doctor_chat: bool = Field(True, env="ENABLE_MULTI_DOCTOR_CHAT")
    enable_case_reports: bool = Field(True, env="ENABLE_CASE_REPORTS")
    enable_real_time_notifications: bool = Field(True, env="ENABLE_REAL_TIME_NOTIFICATIONS")
    enable_case_similarity_search: bool = Field(True, env="ENABLE_CASE_SIMILARITY_SEARCH")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    enable_structured_logging: bool = Field(True, env="ENABLE_STRUCTURED_LOGGING")
    log_to_file: bool = Field(False, env="LOG_TO_FILE")
    log_file_path: str = Field("/var/log/cases_chat/app.log", env="LOG_FILE_PATH")
    
    # Monitoring and Metrics
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    enable_tracing: bool = Field(False, env="ENABLE_TRACING")
    jaeger_agent_host: Optional[str] = Field(None, env="JAEGER_AGENT_HOST")
    jaeger_agent_port: Optional[int] = Field(None, env="JAEGER_AGENT_PORT")
    
    # Health Check Configuration
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(5, env="HEALTH_CHECK_TIMEOUT")
    
    # Case Management Configuration
    case_number_prefix: str = Field("CASE", env="CASE_NUMBER_PREFIX")
    case_number_padding: int = Field(6, env="CASE_NUMBER_PADDING")
    enable_case_auto_archival: bool = Field(True, env="ENABLE_CASE_AUTO_ARCHIVAL")
    case_archive_days: int = Field(90, env="CASE_ARCHIVE_DAYS")
    
    # Doctor Service Configuration
    doctor_response_timeout: int = Field(30, env="DOCTOR_RESPONSE_TIMEOUT")
    enable_doctor_fallback: bool = Field(True, env="ENABLE_DOCTOR_FALLBACK")
    doctor_fallback_order: List[str] = Field(
        default_factory=lambda: ["gemini", "groq", "openai"],
        env="DOCTOR_FALLBACK_ORDER"
    )
    
    @validator("allowed_file_types")
    def validate_file_types(cls, v):
        """Ensure all file types start with a dot"""
        return [ft if ft.startswith(".") else f".{ft}" for ft in v]
    
    @validator("neo4j_uri")
    def validate_neo4j_uri(cls, v):
        """Validate Neo4j URI format"""
        if not v.startswith(("bolt://", "neo4j://", "bolt+s://", "neo4j+s://")):
            raise ValueError("Invalid Neo4j URI format")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Allow extra fields for backward compatibility
        extra = "allow"


# Create settings instance
settings = Settings()

# Ensure required directories exist
os.makedirs(settings.media_upload_path, exist_ok=True)
if settings.log_to_file:
    os.makedirs(os.path.dirname(settings.log_file_path), exist_ok=True)