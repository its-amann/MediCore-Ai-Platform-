"""
Cases Chat Service Main Application
Initializes and configures the Cases Chat microservice
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
from typing import Any

from .config import settings
from .routes import case_router, chat_router, websocket_router, health_router
from .core.dependencies import cleanup_services
from .utils.error_handlers import ServiceUnavailableError, create_error_response

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    
    # Initialize core services
    try:
        from .core.dependencies import get_storage_service, get_doctor_service
        
        # Test storage connection
        storage = get_storage_service()
        if await storage.health_check():
            logger.info("Storage service connected successfully")
        else:
            logger.warning("Storage service health check failed")
        
        # Test AI service
        doctor_service = get_doctor_service()
        ai_health = await doctor_service.health_check()
        if ai_health["healthy"]:
            logger.info("AI services initialized successfully")
        else:
            logger.warning(f"AI services partially available: {ai_health['message']}")
            
    except ServiceUnavailableError as e:
        logger.error(f"Critical service unavailable: {e}")
        # Continue startup but log the issue
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    
    # Initialize optional services
    try:
        from .core.dependencies import get_mcp_client
        mcp_client = get_mcp_client()
        if mcp_client and mcp_client.is_available():
            logger.info("MCP server connected successfully")
        else:
            logger.info("MCP server not available - running without medical history integration")
    except Exception as e:
        logger.warning(f"MCP initialization error: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cases Chat service")
    await cleanup_services()


# Create FastAPI application
app = FastAPI(
    title=f"{settings.SERVICE_NAME} API",
    description="AI-powered medical consultation service with case management",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError):
    """
    Handle service unavailability errors
    """
    return JSONResponse(
        status_code=503,
        content=create_error_response(
            error_type="service_unavailable",
            message=exc.message,
            status_code=503,
            details={"service": exc.service_name}
        )
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected errors
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            error_type="internal_error",
            message="An unexpected error occurred",
            status_code=500
        )
    )


# Include routers
app.include_router(case_router, prefix=settings.API_PREFIX)
app.include_router(chat_router, prefix=settings.API_PREFIX)
app.include_router(websocket_router, prefix=settings.API_PREFIX)
app.include_router(health_router, prefix=settings.API_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running",
        "api_docs": f"{settings.API_PREFIX}/docs"
    }


# Service information endpoint
@app.get(f"{settings.API_PREFIX}/info")
async def service_info():
    """
    Get service information and capabilities
    """
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "capabilities": {
            "case_management": True,
            "ai_consultation": True,
            "multi_doctor_support": settings.ENABLE_MULTI_DOCTOR_CHAT,
            "image_support": settings.ENABLE_IMAGE_SUPPORT,
            "audio_support": settings.ENABLE_AUDIO_SUPPORT,
            "case_reports": settings.ENABLE_CASE_REPORTS,
            "websocket_support": True,
            "mcp_integration": settings.ENABLE_MCP
        },
        "available_doctors": [
            "general_consultant",
            "cardiologist",
            "bp_specialist"
        ],
        "api_endpoints": {
            "cases": f"{settings.API_PREFIX}/cases",
            "chat": f"{settings.API_PREFIX}/chat",
            "websocket": f"{settings.API_PREFIX}/ws",
            "health": f"{settings.API_PREFIX}/health"
        }
    }


# Export the app instance for use with uvicorn
def create_app() -> FastAPI:
    """
    Application factory
    
    Returns:
        Configured FastAPI application
    """
    return app


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.microservices.cases_chat.service:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )