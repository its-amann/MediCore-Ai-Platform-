"""
Application configuration settings for Unified Medical AI Platform
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Try to import BaseSettings from the correct location
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older versions
    from pydantic import BaseSettings

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    app_name: str = "Unified Medical AI Platform"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Server settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    
    # Database settings
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "medical123")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # Redis settings
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT settings
    secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Groq API settings
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model_general: str = os.getenv("GROQ_MODEL_GENERAL", "llama-3.3-70b-versatile")
    groq_model_cardiologist: str = os.getenv("GROQ_MODEL_CARDIOLOGIST", "llama-3.3-70b-versatile")
    groq_model_bp_specialist: str = os.getenv("GROQ_MODEL_BP_SPECIALIST", "llama-3.3-70b-versatile")
    vision_model: str = os.getenv("VISION_MODEL", "llama-3.2-11b-vision-preview")
    
    # Gemini API settings
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_embedding_api_key: str = os.getenv("GEMINI_EMBEDDING_API_KEY", "")
    gemini_report_api_key: str = os.getenv("GEMINI_REPORT_API_KEY", "")
    gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    gemini_report_model: str = os.getenv("GEMINI_REPORT_MODEL", "gemini-1.5-pro-latest")
    
    # CORS settings
    allowed_origins: list = ["http://localhost:3000", "http://localhost:3001", "*"]
    
    # File upload settings
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: set = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".mp3", ".wav", ".m4a"}
    
    # Media storage
    media_directory: str = os.getenv("MEDIA_DIRECTORY", "media")
    
    # Additional API keys (optional)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY", "")
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY", "")
    
    # MCP Server settings
    mcp_server_enabled: bool = os.getenv("MCP_SERVER_ENABLED", "True").lower() == "true"
    mcp_server_host: str = os.getenv("MCP_SERVER_HOST", "localhost")
    mcp_server_port: int = int(os.getenv("MCP_SERVER_PORT", "3030"))
    # Use MCP_JWT_SECRET if set, otherwise fallback to main JWT_SECRET_KEY
    mcp_jwt_secret: str = os.getenv("MCP_JWT_SECRET", os.getenv("JWT_SECRET_KEY", ""))
    mcp_require_auth: bool = os.getenv("MCP_REQUIRE_AUTH", "False").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from environment

def validate_configuration():
    """Validate critical configuration settings"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required but not set in environment")
    
    if not settings.secret_key or settings.secret_key == "your-secret-key-here":
        raise ValueError("SECRET_KEY must be set to a secure value")
    
    # Create media directory if it doesn't exist
    os.makedirs(settings.media_directory, exist_ok=True)

# Create settings instance
settings = Settings()

# Load CORS origins from environment if available
import json
cors_env = os.getenv("CORS_ORIGINS")
if cors_env:
    try:
        settings.allowed_origins = json.loads(cors_env)
    except:
        pass