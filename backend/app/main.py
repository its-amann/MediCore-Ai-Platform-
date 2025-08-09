"""
Unified Medical AI Platform - Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import os
import asyncio
from dotenv import load_dotenv
from pydantic import ValidationError

# Load environment variables first
load_dotenv()

# Initialize unified logging system
from app.core.logging_config import initialize_logging
from app.core.unified_logging import get_logger

# Initialize logging before any other imports that might use logging
logger = initialize_logging()

# Log WebSocket configuration at startup
ws_auth_required = os.getenv('WS_AUTH_REQUIRED', 'true').lower() == 'true'
ws_auth_bypass = os.getenv('WS_AUTH_BYPASS', 'false').lower() == 'true'
logger.info(f"WebSocket Configuration: auth_required={ws_auth_required}, auth_bypass={ws_auth_bypass}")
if not ws_auth_required or ws_auth_bypass:
    logger.warning("⚠️  WebSocket authentication is DISABLED - DO NOT USE IN PRODUCTION")

# Now import other modules
from app.core.database.neo4j_client import Neo4jClient
from app.core.services.database_manager import unified_db_manager
from app.core.services.microservice_initializer import MicroserviceInitializer
from app.core.services.mcp_server_manager import get_mcp_server_manager
from app.core.services.mcp_client_pool import get_mcp_client_pool

# Import organized routes
from app.api.routes import (
    auth_router,
    cases_router,
    medical_imaging_router,
    collaboration_router,
    voice_router,
    websocket_router,
    health_router,
    doctors_router,
    medical_context_router,
    logs_router,
    mcp_management_router
)

from app.api.unified_middleware import setup_unified_middleware
from app.core.config import settings, validate_configuration

# Import collaboration integration
from app.microservices.collaboration.integration import collaboration_integration

# Validate configuration on startup
validate_configuration()

# Global database client and status
neo4j_client = None
database_connected = False
mcp_server_manager = None
mcp_client_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global neo4j_client, database_connected, mcp_server_manager, mcp_client_pool
    
    # Startup
    logger.info("Starting Unified Medical AI Platform...")
    
    # Initialize UnifiedDatabaseManager first
    try:
        # Register main application with database manager
        unified_db_manager.register_service("main_application", {
            "type": "core",
            "version": settings.app_version
        })
        
        # Connect both sync and async drivers
        sync_driver = unified_db_manager.connect_sync()
        async_driver = await unified_db_manager.connect_async()
        
        # Initialize database constraints once for all services
        await unified_db_manager.initialize_constraints()
        
        # Create legacy Neo4jClient wrapper for backward compatibility
        neo4j_client = Neo4jClient()
        neo4j_client.driver = sync_driver  # Use the shared sync driver
        
        # Verify connection is working
        if not unified_db_manager.is_connected_sync():
            raise Exception("Neo4j connection verification failed")
        
        logger.info("Connected to Neo4j database using UnifiedDatabaseManager")
        logger.info("Database constraints initialized")
        
        database_connected = True
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        logger.warning("Application will continue but database-dependent features may not work")
        neo4j_client = None
        database_connected = False
    
    # Initialize MCP Server Manager and Client Pool
    if settings.mcp_server_enabled and database_connected:
        try:
            # Initialize MCP server manager
            mcp_server_manager = await get_mcp_server_manager()
            
            # Pass database configuration to MCP servers
            for server_name, server_info in mcp_server_manager.servers.items():
                server_info.config.env_vars.update({
                    "NEO4J_URI": settings.neo4j_uri,
                    "NEO4J_USER": settings.neo4j_user,
                    "NEO4J_PASSWORD": settings.neo4j_password,
                    "NEO4J_DATABASE": settings.neo4j_database,
                })
            
            # Start all MCP servers
            await mcp_server_manager.start_all()
            
            # Initialize MCP client pool
            mcp_client_pool = await get_mcp_client_pool()
            
            logger.info("MCP servers and client pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP infrastructure: {e}", exc_info=True)
            # Continue without MCP - application can still function
    else:
        if not settings.mcp_server_enabled:
            logger.info("MCP servers disabled by configuration")
        elif not database_connected:
            logger.warning("Skipping MCP server initialization - database not connected")
    
    # Initialize collaboration integration with shared database driver
    if database_connected and sync_driver:
        try:
            # Pass the shared sync driver to collaboration integration
            await collaboration_integration.initialize(neo4j_driver=sync_driver)
            # Register collaboration service with database manager
            unified_db_manager.register_service("collaboration_microservice", {
                "type": "microservice",
                "version": "1.0.0"
            })
            logger.info("Collaboration integration initialized successfully with shared database")
        except Exception as e:
            logger.error(f"Failed to initialize collaboration integration: {e}")
            # Log the full error for debugging
            import traceback
            logger.error(f"Full error trace: {traceback.format_exc()}")
            # Don't fail the entire app if collaboration fails to initialize
    else:
        logger.warning("Skipping collaboration integration initialization - database not connected")
    
    # Initialize all microservices with shared database connections
    microservice_initializer = None
    if database_connected and sync_driver and async_driver:
        try:
            microservice_initializer = MicroserviceInitializer(unified_db_manager)
            
            # Initialize all microservices
            init_results = await microservice_initializer.initialize_all_microservices(sync_driver, async_driver)
            logger.info(f"Microservice initialization results: {init_results}")
            
            # Run unified migrations
            migration_results = await microservice_initializer.run_unified_migrations()
            logger.info(f"Migration results: {migration_results}")
            
        except Exception as e:
            logger.error(f"Failed to initialize microservices: {e}")
            # Continue running but log the error
    
    # Session manager now integrated into cases microservice
    
    # Initialize cases chat WebSocket adapter
    try:
        from app.microservices.cases_chat.websocket_adapter import get_cases_chat_ws_adapter
        cases_chat_adapter = get_cases_chat_ws_adapter()
        logger.info("Cases chat WebSocket adapter initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize cases chat WebSocket adapter: {e}")
        # Don't fail the entire app if adapter fails to initialize
    
    # DISABLED: AI provider health monitoring to prevent excessive API consumption
    # The health monitoring was making actual API calls every 5 minutes to test providers
    # which was consuming API quotas unnecessarily. Health checks are now done on-demand
    # when providers are actually used, with built-in fallback mechanisms.
    logger.info("AI provider health monitoring disabled - using on-demand checks with fallback")
    
    # Initialize medical imaging workflow manager
    try:
        # Import the get_workflow_manager function from the API routes
        from app.api.routes.medical_imaging.medical_imaging import get_workflow_manager
        
        # Initialize the workflow manager
        workflow_manager = await get_workflow_manager()
        if workflow_manager:
            logger.info("Medical imaging workflow manager initialized successfully")
        else:
            logger.warning("Medical imaging workflow manager not available")
        
    except Exception as e:
        logger.warning(f"Failed to initialize medical imaging workflow manager: {e}")
        # Don't fail the entire app if workflow manager fails to initialize
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Cancel all background tasks gracefully
    try:
        tasks = [t for t in asyncio.all_tasks() if t != asyncio.current_task()]
        logger.info(f"Cancelling {len(tasks)} background tasks...")
        for task in tasks:
            task.cancel()
        # Wait for all tasks to complete cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All background tasks cancelled")
    except asyncio.CancelledError:
        # This is expected during shutdown
        pass
    except Exception as e:
        logger.warning(f"Error cancelling background tasks: {e}")
    
    # Shutdown WebSocket manager
    try:
        from app.core.websocket import cleanup_websocket_manager
        await cleanup_websocket_manager()
        logger.info("WebSocket manager shut down successfully")
    except Exception as e:
        logger.warning(f"Error shutting down WebSocket manager: {e}")
    
    # Shutdown medical imaging WebSocket adapter
    try:
        from app.microservices.medical_imaging.websocket_adapter import cleanup_medical_websocket
        await cleanup_medical_websocket()
        logger.info("Medical imaging WebSocket adapter shut down successfully")
    except Exception as e:
        logger.warning(f"Error shutting down medical imaging WebSocket adapter: {e}")
    
    # Shutdown cases chat WebSocket adapter
    try:
        # Cases chat adapter doesn't have a cleanup function, just log shutdown
        logger.info("Cases chat WebSocket adapter shut down successfully")
    except Exception as e:
        logger.warning(f"Error shutting down cases chat WebSocket adapter: {e}")
    
    # Shutdown all microservices through the initializer
    if microservice_initializer:
        try:
            await microservice_initializer.shutdown_all()
            logger.info("All microservices shut down successfully")
        except Exception as e:
            logger.warning(f"Error shutting down microservices: {e}")
    
    # Shutdown collaboration integration
    try:
        await collaboration_integration.shutdown()
        logger.info("Collaboration integration shut down successfully")
    except Exception as e:
        logger.warning(f"Error shutting down collaboration integration: {e}")
    
    # Session manager handled by cases microservice
    
    # Shutdown MCP infrastructure
    if mcp_client_pool:
        try:
            await mcp_client_pool.close_all()
            logger.info("MCP client pool shut down successfully")
        except Exception as e:
            logger.warning(f"Error shutting down MCP client pool: {e}")
    
    if mcp_server_manager:
        try:
            await mcp_server_manager.stop_all()
            logger.info("MCP servers shut down successfully")
        except Exception as e:
            logger.warning(f"Error shutting down MCP servers: {e}")
    
    # Shutdown UnifiedDatabaseManager
    try:
        await unified_db_manager.shutdown()
        logger.info("UnifiedDatabaseManager shut down successfully")
    except Exception as e:
        logger.warning(f"Error shutting down UnifiedDatabaseManager: {e}")
    
    # Legacy cleanup for neo4j_client
    if neo4j_client and hasattr(neo4j_client, 'disconnect'):
        try:
            neo4j_client.disconnect()
            logger.info("Legacy database connection closed")
        except Exception as e:
            logger.warning(f"Error closing legacy database connection: {e}")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Advanced medical AI platform with imaging, voice consultation, and collaboration features",
    version=settings.app_version,
    lifespan=lifespan,
    debug=settings.debug,
    redirect_slashes=False
)

# CORS middleware - Enhanced for file uploads and WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRF-Token",
        "X-Upload-Progress",
        # WebSocket-specific headers
        "Sec-WebSocket-Protocol",
        "Sec-WebSocket-Version",
        "Sec-WebSocket-Key",
        "Sec-WebSocket-Extensions"
    ],
    expose_headers=[
        "Content-Length",
        "X-Upload-Progress",
        "X-Report-ID",
        "X-Workflow-ID",
        "X-Total-Count",
        "X-Page-Count"
    ],
    max_age=3600  # Cache preflight for 1 hour
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Setup unified middleware stack
setup_unified_middleware(app)

# Exception handlers must be registered before routes
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors"""
    logger.info(f"Validation error handler triggered: {exc.errors()}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request path: {request.url.path}")
    errors = exc.errors()
    if len(errors) == 1:
        error = errors[0]
        # Extract field name, skipping 'body' if present
        field_loc = error['loc']
        field = field_loc[-1] if field_loc else 'field'
        if len(field_loc) > 1 and field_loc[0] == 'body':
            field = field_loc[-1]
        message = f"{str(field).title()}: {error['msg']}"
    else:
        # Multiple errors - return the first few
        messages = []
        for error in errors[:3]:  # Limit to first 3 errors
            field_loc = error['loc']
            field = field_loc[-1] if field_loc else 'field'
            if len(field_loc) > 1 and field_loc[0] == 'body':
                field = field_loc[-1]
            messages.append(f"{str(field)}: {error['msg']}")
        message = "; ".join(messages)
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": message,
            "status_code": 422,
            "path": str(request.url)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    # Log with full context using unified logger
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "request_method": request.method,
            "request_path": str(request.url.path),
            "request_url": str(request.url),
            "client_host": request.client.host if request.client else "unknown",
            "headers": dict(request.headers) if hasattr(request, 'headers') else {}
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": str(request.url)
        }
    )

# Include organized API routes

# Common routes
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(doctors_router, prefix="/api/v1/doctors", tags=["AI Doctors"])
app.include_router(medical_context_router, prefix="/api/v1/medical-context", tags=["Medical Context"])
app.include_router(logs_router, prefix="/api/v1/logs", tags=["Logs"])
app.include_router(mcp_management_router, prefix="/api/v1", tags=["MCP Management"])

# Authentication
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

# Cases microservice
app.include_router(cases_router, prefix="/api/v1", tags=["Cases"])

# Medical Imaging microservice
app.include_router(medical_imaging_router, prefix="/api/v1/medical-imaging", tags=["Medical Imaging"])

# Voice consultation microservice
app.include_router(voice_router, prefix="/api/v1/voice", tags=["Voice"])

# Collaboration microservice
app.include_router(collaboration_router, prefix="/api/v1/collaboration", tags=["Collaboration"])

# Unified WebSocket endpoint
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])

# Add rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import jwt

# Create limiter with user-based key
def get_user_id(request: Request):
    """Extract user ID from JWT token for rate limiting"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            token = auth.split(" ")[1]
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            return payload.get("sub", get_remote_address(request))
        except:
            pass
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_id)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Note: Collaboration router already included above

# app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])  # Temporarily disabled

# WebSocket endpoints for collaboration
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/api/v1/collaboration/ws/chat/{room_id}")
async def websocket_collaboration_chat(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for collaboration chat.
    Routes to the unified WebSocket manager.
    """
    if not hasattr(collaboration_integration, 'websocket_manager') or collaboration_integration.websocket_manager is None:
        await websocket.close(code=4003, reason="Collaboration service unavailable")
        return
    
    user_id = None
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Wait for authentication message
        auth_data = await websocket.receive_json()
        if auth_data.get("type") != "auth":
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        user_id = auth_data.get("user_id")
        token = auth_data.get("token")
        
        if not user_id and not token:
            await websocket.close(code=4001, reason="User ID or token required")
            return
        
        # Handle connection through unified WebSocket manager
        if token:
            await collaboration_integration.websocket_manager.handle_connection(websocket, token, room_id)
        else:
            # Fallback for direct user_id authentication (testing/development)
            success = await collaboration_integration.websocket_manager.connection_manager.connect(
                room_id, user_id, websocket, user_id
            )
            if not success:
                await websocket.close(code=1011, reason="Connection failed")
                return
            
            # Handle messages manually for fallback mode
            try:
                while True:
                    data = await websocket.receive_json()
                    await collaboration_integration.websocket_manager.handle_message(user_id, data)
            except Exception as e:
                logger.error(f"Error in fallback message handling: {e}")
                raise
        
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from collaboration chat room {room_id}")
    except Exception as e:
        logger.error(f"WebSocket collaboration chat error: {e}", exc_info=True)
    finally:
        if user_id and collaboration_integration.websocket_manager:
            await collaboration_integration.websocket_manager.connection_manager.disconnect(room_id, user_id)

@app.websocket("/api/v1/collaboration/ws/video/{room_id}")
async def websocket_collaboration_video(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for collaboration video/audio.
    Routes to the unified WebSocket manager.
    """
    if not hasattr(collaboration_integration, 'websocket_manager') or collaboration_integration.websocket_manager is None:
        await websocket.close(code=4003, reason="Collaboration service unavailable")
        return
    
    user_id = None
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Wait for authentication message
        auth_data = await websocket.receive_json()
        if auth_data.get("type") != "auth":
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        user_id = auth_data.get("user_id")
        token = auth_data.get("token")
        
        if not user_id and not token:
            await websocket.close(code=4001, reason="User ID or token required")
            return
        
        # Handle connection through unified WebSocket manager
        if token:
            await collaboration_integration.websocket_manager.handle_connection(websocket, token, room_id)
        else:
            # Fallback for direct user_id authentication (testing/development)
            success = await collaboration_integration.websocket_manager.connection_manager.connect(
                room_id, user_id, websocket, user_id
            )
            if not success:
                await websocket.close(code=1011, reason="Connection failed")
                return
            
            # Handle messages manually for fallback mode
            try:
                while True:
                    data = await websocket.receive_json()
                    await collaboration_integration.websocket_manager.handle_message(user_id, data)
            except Exception as e:
                logger.error(f"Error in fallback message handling: {e}")
                raise
        
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from collaboration video room {room_id}")
    except Exception as e:
        logger.error(f"WebSocket collaboration video error: {e}", exc_info=True)
    finally:
        if user_id and collaboration_integration.websocket_manager:
            await collaboration_integration.websocket_manager.connection_manager.disconnect(room_id, user_id)

# Dependency to get database client
def get_neo4j_client():
    """Get Neo4j database client"""
    if neo4j_client is None:
        logger.warning("Database client requested but not available")
        # Return None instead of raising exception for graceful degradation
        return None
    return neo4j_client

# Optional dependency for database client
def get_neo4j_client_optional():
    """Get Neo4j database client (returns None if not available)"""
    return neo4j_client

# Dependency to check database status
def get_database_status():
    """Get database connection status"""
    return {
        "connected": database_connected,
        "client_available": neo4j_client is not None
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    health_status = {
        "status": "healthy",
        "service": "Unified Medical AI Platform",
        "version": "1.0.0",
        "database": "disconnected"
    }
    
    # Check unified database manager
    try:
        db_health = await unified_db_manager.health_check()
        health_status["database"] = "connected" if db_health["status"] == "healthy" else "error"
        health_status["database_details"] = db_health
    except Exception as e:
        logger.warning(f"Unified database health check failed: {e}")
        health_status["database"] = "error"
        health_status["database_error"] = str(e)
    
    # Check legacy database connection if available
    if database_connected and neo4j_client is not None:
        try:
            # Test database connection with a simple query
            with neo4j_client.get_session() as session:
                session.run("RETURN 1")
            health_status["legacy_database"] = "connected"
        except Exception as e:
            logger.warning(
                f"Legacy database health check failed: {e}",
                exc_info=True,
                extra={"operation": "health_check", "service": "database_connectivity"}
            )
            health_status["legacy_database"] = "error"
            health_status["legacy_database_error"] = str(e)
    
    # Check collaboration integration status
    try:
        if hasattr(collaboration_integration, 'db_client') and collaboration_integration.db_client:
            health_status["collaboration"] = "connected"
        else:
            health_status["collaboration"] = "disconnected"
    except Exception as e:
        health_status["collaboration"] = "error"
        health_status["collaboration_error"] = str(e)
    
    # Check MCP infrastructure status
    if mcp_server_manager:
        try:
            mcp_status = await mcp_server_manager.get_all_server_status()
            health_status["mcp_servers"] = {
                "total": mcp_status["total"],
                "running": mcp_status["running"],
                "stopped": mcp_status["stopped"],
                "unhealthy": mcp_status["unhealthy"],
                "servers": {
                    name: {
                        "state": server["state"],
                        "uptime": server.get("uptime"),
                        "health_check_failures": server.get("health_check_failures", 0)
                    }
                    for name, server in mcp_status["servers"].items()
                }
            }
        except Exception as e:
            health_status["mcp_servers"] = "error"
            health_status["mcp_servers_error"] = str(e)
    else:
        health_status["mcp_servers"] = "disabled"
    
    if mcp_client_pool:
        try:
            client_health = await mcp_client_pool.health_check_all()
            health_status["mcp_clients"] = {
                name: {
                    "healthy": info["healthy"],
                    "success_rate": info["stats"]["success_rate"],
                    "average_request_time": info["stats"]["average_request_time"]
                }
                for name, info in client_health.items()
            }
        except Exception as e:
            health_status["mcp_clients"] = "error"
            health_status["mcp_clients_error"] = str(e)
    else:
        health_status["mcp_clients"] = "disabled"
    
    # Application is healthy even without database for testing
    return health_status

# Database status endpoint
@app.get("/database/status")
async def database_status():
    """Get detailed database connection status"""
    status = get_database_status()
    
    if status["connected"] and neo4j_client is not None:
        try:
            # Test database connection with a simple query
            with neo4j_client.get_session() as session:
                result = session.run("RETURN 1 as test").single()
            status["test_query"] = "passed"
            status["test_result"] = result["test"]
        except Exception as e:
            status["test_query"] = "failed"
            status["test_error"] = str(e)
    
    return status

# Test endpoint for debugging database
@app.get("/test-db")
async def test_db():
    """Test database connection"""
    try:
        logger.info(f"neo4j_client type: {type(neo4j_client)}")
        logger.info(f"neo4j_client value: {neo4j_client}")
        logger.info(f"database_connected: {database_connected}")
        
        if neo4j_client is None:
            return {
                "success": False,
                "error": "neo4j_client is None - database connection failed during startup",
                "database_connected": database_connected,
                "message": "Application is running in testing mode without database"
            }
        
        # Test get_neo4j_client function (this will raise exception if no database)
        try:
            client_from_func = get_neo4j_client()
            logger.info(f"client_from_func: {client_from_func}")
        except HTTPException as e:
            return {
                "success": False,
                "error": f"get_neo4j_client() raised HTTPException: {e.detail}",
                "status_code": e.status_code,
                "database_connected": database_connected
            }
            
        # Test the specific method that's failing
        try:
            # Test simple connection
            with client_from_func.get_session() as session:
                result = session.run("RETURN 1 as test").single()
            return {
                "success": True, 
                "db_connection_works": True, 
                "result": result["test"],
                "database_connected": database_connected
            }
        except Exception as e:
            return {
                "success": False, 
                "connection_error": str(e), 
                "client_type": str(type(client_from_func)),
                "database_connected": database_connected
            }
        
    except Exception as e:
        logger.error(f"Test DB error: {e}")
        return {
            "error": str(e),
            "database_connected": database_connected,
            "success": False
        }

# Test registration endpoint
@app.post("/test-register")
async def test_register():
    """Minimal test of registration logic"""
    try:
        # Direct test without any dependencies
        client = get_neo4j_client()
        if client is None:
            return {"error": "Database client is None"}
        
        # Test the database connection
        with client.get_session() as session:
            result = session.run("RETURN 1 as test").single()
        return {"success": True, "db_works": True, "result": result["test"]}
        
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

# Test endpoint for validation
@app.post("/test-validation")
async def test_validation(data: dict):
    """Test endpoint to debug validation"""
    from pydantic import ValidationError
    from app.core.database.models import UserCreate
    try:
        # This should trigger validation error
        user = UserCreate(**data)
        return {"success": True}
    except ValidationError as e:
        logger.info(f"Caught validation error manually: {e.errors()}")
        raise HTTPException(status_code=422, detail=str(e))

# Test collaboration integration endpoint
@app.get("/test-collaboration")
async def test_collaboration():
    """Test collaboration integration"""
    try:
        status = {
            "integration_initialized": hasattr(collaboration_integration, 'db_client'),
            "websocket_manager_available": hasattr(collaboration_integration, 'websocket_manager') and collaboration_integration.websocket_manager is not None,
            "services_available": {
                "room_service": hasattr(collaboration_integration, 'room_service') and collaboration_integration.room_service is not None,
                "chat_service": hasattr(collaboration_integration, 'chat_service') and collaboration_integration.chat_service is not None,
                "notification_service": hasattr(collaboration_integration, 'notification_service') and collaboration_integration.notification_service is not None,
                "user_service": hasattr(collaboration_integration, 'user_service') and collaboration_integration.user_service is not None
            }
        }
        
        # Test database connection if available
        if hasattr(collaboration_integration, 'db_client') and collaboration_integration.db_client:
            try:
                is_connected = await collaboration_integration.db_client.is_connected()
                status["database_connected"] = is_connected
            except Exception as e:
                status["database_connected"] = False
                status["database_error"] = str(e)
        else:
            status["database_connected"] = False
            
        return status
    except Exception as e:
        return {
            "error": str(e),
            "integration_available": False
        }

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Unified Medical AI Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "collaboration": {
            "api": "/api/v1/collaboration",
            "websocket_chat": "/api/v1/collaboration/ws/chat/{room_id}",
            "websocket_video": "/api/v1/collaboration/ws/video/{room_id}"
        }
    }

# Configure Uvicorn logging
def configure_uvicorn_logging():
    """Configure Uvicorn to log to logs/uvicorn.log"""
    import logging.config
    from pathlib import Path
    import platform
    import os
    
    # Ensure logs directory exists
    backend_dir = Path(__file__).parent.parent
    logs_dir = backend_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create log file path - use uvicorn.log as requested by user
    log_file_path = logs_dir / "uvicorn.log"
    
    # Check if we're on Windows in development
    is_windows = platform.system() == 'Windows'
    is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
    
    # Base handlers - always include console
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    }
    
    # Always add file handlers as requested by user
    # Remove the Windows development check to ensure logs are always written to file
    if True:  # Always enable file logging
        handlers.update({
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": str(log_file_path),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "access_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "access",
                "filename": str(log_file_path),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
        })
    
    # Uvicorn logging configuration
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "access": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
        },
        "handlers": handlers,
        "loggers": {
            "uvicorn": {
                "handlers": ["console", "file"],  # Always log to both console and file
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console", "file"],  # Always log to both console and file
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console", "access_file"],  # Always log to both console and file
                "level": "INFO",
                "propagate": False
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"]  # Always log to both console and file
        }
    }
    
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info(f"Uvicorn logging configured. Logs will be written to: {log_file_path}")
    return str(log_file_path)

# Configure Uvicorn logging on module load
uvicorn_log_path = configure_uvicorn_logging()

if __name__ == "__main__":
    import uvicorn
    import sys
    from pathlib import Path
    from datetime import datetime
    
    # Log startup message
    logger.info(f"Starting server directly via main.py. Logs will be written to: {uvicorn_log_path}")
    
    # Run uvicorn with our logging configuration
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True,  # Keep colors for terminal
        # Use our logging config
        log_config=None  # This ensures our dictConfig is used
    )


