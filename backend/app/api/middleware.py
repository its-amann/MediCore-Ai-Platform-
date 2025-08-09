"""
Custom middleware for the Unified Medical AI Platform
"""

import time
import logging
import json
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Import our unified logging system
try:
    from app.core.unified_logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback to standard logging
    logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for comprehensive request/response logging"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]  # Shorter ID for readability
        request.state.request_id = request_id
        
        # Get client info
        client_host = request.client.host if request.client else "unknown"
        
        # Start timing
        start_time = time.time()
        
        # Request logging with context
        request_data = {
            'request_id': request_id,
            'method': request.method,
            'path': str(request.url.path),
            'url': str(request.url),
            'client_ip': client_host,
            'query_params': dict(request.query_params) if request.query_params else {}
        }
        logger.info("Incoming request", extra=request_data)
        
        # Log headers (excluding sensitive ones)
        safe_headers = {k: v for k, v in request.headers.items() 
                       if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
        logger.debug(f"[{request_id}] Headers: {safe_headers}")
        
        # Skip body logging for now to avoid request body consumption issues
        # This was causing login failures because the body was being consumed
        # before the actual endpoint could read it
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Exception during request processing",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': str(request.url.path),
                    'duration': duration,
                    'client_ip': client_host,
                    'error': str(e)
                },
                exc_info=True
            )
            raise
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Response logging
        response_data = {
            'request_id': request_id,
            'status_code': response.status_code,
            'duration': process_time,
            'method': request.method,
            'path': str(request.url.path),
            'client_ip': client_host
        }
        logger.info("Request completed", extra=response_data)
        
        # Log slow requests
        if process_time > 1.0:  # More than 1 second
            logger.warning(f"[{request_id}] Slow request: {request.method} {request.url.path} took {process_time:.3f}s")
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for comprehensive error handling and logging"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
        
        try:
            response = await call_next(request)
            
            # Log 4xx and 5xx errors
            if response.status_code >= 400:
                logger.warning(f"[{request_id}] Error response: {response.status_code}")
            
            return response
        except Exception as e:
            # Log full exception with traceback
            logger.error(
                "Unhandled exception in middleware",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "client": request.client.host if request.client else "unknown",
                    "url": str(request.url),
                    "middleware": "ErrorHandlingMiddleware",
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Log to security logger if it looks like an attack
            if any(pattern in str(request.url).lower() for pattern in ['../..', 'script', 'eval(', 'exec(']):
                logger.warning(
                    "Suspicious activity detected",
                    extra={
                        'request_id': request_id,
                        'url': str(request.url),
                        'method': request.method,
                        'client': request.client.host if request.client else "unknown",
                        'patterns_detected': [p for p in ['../..', 'script', 'eval(', 'exec('] if p in str(request.url).lower()],
                        'security_event': 'suspicious_activity'
                    }
                )
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "path": str(request.url.path),
                    "method": request.method,
                    "timestamp": time.time()
                },
                headers={"X-Request-ID": request_id}
            )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Log security-related requests
        if any(pattern in str(request.url).lower() for pattern in ['admin', 'config', 'debug']):
            logger.warning(
                "Security sensitive access",
                extra={
                    'method': request.method,
                    'path': str(request.url.path),
                    'url': str(request.url),
                    'client': request.client.host if request.client else 'unknown',
                    'patterns_detected': [p for p in ['admin', 'config', 'debug'] if p in str(request.url).lower()],
                    'security_event': 'security_sensitive_access'
                }
            )
        
        return response

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring performance metrics"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        try:
            self.logger = get_logger("app.performance")
        except:
            self.logger = logging.getLogger("app.performance")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Track various metrics
        metrics = {
            "path": str(request.url.path),
            "method": request.method,
            "start_time": time.time()
        }
        
        # Memory usage before request (optional - requires psutil)
        try:
            import psutil
            process = psutil.Process()
            metrics["memory_before"] = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            metrics["memory_before"] = 0
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        metrics["duration"] = time.time() - metrics["start_time"]
        
        # Memory usage after request
        try:
            import psutil
            process = psutil.Process()
            metrics["memory_after"] = process.memory_info().rss / 1024 / 1024  # MB
            metrics["memory_delta"] = metrics["memory_after"] - metrics["memory_before"]
        except ImportError:
            metrics["memory_after"] = 0
            metrics["memory_delta"] = 0
        
        metrics["status_code"] = response.status_code
        
        # Log performance metrics
        self.logger.info(
            "Performance metrics",
            extra={
                'duration': metrics['duration'],
                'memory_delta': metrics['memory_delta'],
                'status_code': metrics['status_code'],
                'method': metrics['method'],
                'path': metrics['path'],
                'memory_before': metrics['memory_before'],
                'memory_after': metrics['memory_after']
            }
        )
        
        # Warn on high memory usage
        if metrics["memory_delta"] > 50:  # More than 50MB increase
            self.logger.warning(
                "High memory usage detected",
                extra={
                    **metrics,
                    'memory_threshold': 50,
                    'alert_type': 'high_memory_usage'
                }
            )
        
        return response