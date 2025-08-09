"""
Unified Middleware for Medical AI Platform

This module provides middleware components that integrate with the unified logging system:
- Request/response logging
- Performance monitoring
- Security audit trails
- Medical operation tracking
- Error handling with structured logging
"""

import time
import uuid
import json
import traceback
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI, status

from app.core.unified_logging import get_logger, correlation_id, request_context


class UnifiedLoggingMiddleware(BaseHTTPMiddleware):
    """Comprehensive request/response logging middleware"""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.logger = get_logger('api.middleware.logging')
        self.exclude_paths = exclude_paths or ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths and WebSocket endpoints
        if request.url.path in self.exclude_paths or request.url.path.startswith('/api/v1/ws'):
            return await call_next(request)
        
        # Generate correlation ID for request tracking
        corr_id = request.headers.get('X-Correlation-ID', f"req-{uuid.uuid4().hex[:12]}")
        correlation_id.set(corr_id)
        
        # Extract request context
        context = {
            'method': request.method,
            'path': request.url.path,
            'client_host': request.client.host if request.client else 'unknown',
            'user_agent': request.headers.get('user-agent', 'unknown'),
        }
        
        # Add authenticated user info if available
        if hasattr(request.state, 'user'):
            context['user_id'] = getattr(request.state.user, 'id', 'unknown')
            context['user_email'] = getattr(request.state.user, 'email', 'unknown')
        
        request_context.set(context)
        
        # Log request
        start_time = time.time()
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'request_id': corr_id,
                'query_params': dict(request.query_params),
                'headers': self._sanitize_headers(dict(request.headers))
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            self.logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    'request_id': corr_id,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                    'response_size': response.headers.get('content-length', 0)
                }
            )
            
            # Add correlation ID to response headers
            response.headers['X-Correlation-ID'] = corr_id
            
            # Log performance metrics for slow requests
            if duration_ms > 1000:  # Log slow requests (>1s)
                self.logger.performance(
                    f"{request.method} {request.url.path}",
                    duration_ms,
                    metadata={'status_code': response.status_code, 'slow_request': True}
                )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    'request_id': corr_id,
                    'duration_ms': duration_ms,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    'error': 'Internal server error',
                    'correlation_id': corr_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                headers={'X-Correlation-ID': corr_id}
            )
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive information from headers"""
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        sanitized = headers.copy()
        
        for header in sensitive_headers:
            if header in sanitized:
                sanitized[header] = '***REDACTED***'
                
        return sanitized


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security logging and monitoring middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger('security.middleware')
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip WebSocket endpoints
        if request.url.path.startswith('/api/v1/ws'):
            return await call_next(request)
            
        # Log security headers
        security_headers = {
            'x-forwarded-for': request.headers.get('x-forwarded-for'),
            'x-real-ip': request.headers.get('x-real-ip'),
            'referer': request.headers.get('referer'),
            'origin': request.headers.get('origin'),
        }
        
        # Check for suspicious patterns
        suspicious = False
        details = {}
        
        # Check for SQL injection patterns
        if request.url.query:
            query_string = str(request.url.query).lower()
            sql_patterns = ['union', 'select', 'drop', 'insert', 'update', 'delete', '--', '/*', '*/']
            if any(pattern in query_string for pattern in sql_patterns):
                suspicious = True
                details['sql_injection_attempt'] = True
                details['query'] = str(request.url.query)
        
        # Check for path traversal
        if '../' in request.url.path or '..\\' in request.url.path:
            suspicious = True
            details['path_traversal_attempt'] = True
            details['path'] = request.url.path
        
        # Log security event if suspicious
        if suspicious:
            self.logger.security(
                'suspicious_request',
                details={
                    **details,
                    **security_headers,
                    'client_host': request.client.host if request.client else 'unknown'
                },
                severity='WARNING'
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers to response
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Log authentication failures
        if response.status_code == 401:
            self.logger.security(
                'authentication_failure',
                details={
                    'path': request.url.path,
                    'method': request.method,
                    'client_host': request.client.host if request.client else 'unknown'
                },
                severity='WARNING'
            )
        
        # Log authorization failures
        elif response.status_code == 403:
            self.logger.security(
                'authorization_failure',
                details={
                    'path': request.url.path,
                    'method': request.method,
                    'user_id': request_context.get().get('user_id', 'unknown')
                },
                severity='WARNING'
            )
        
        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Advanced performance monitoring middleware"""
    
    def __init__(self, app, slow_request_threshold_ms: float = 1000):
        super().__init__(app)
        self.logger = get_logger('performance.middleware')
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.request_metrics = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip WebSocket endpoints
        if request.url.path.startswith('/api/v1/ws'):
            return await call_next(request)
            
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        # Track concurrent requests
        path = request.url.path
        if path not in self.request_metrics:
            self.request_metrics[path] = {
                'count': 0,
                'total_time': 0,
                'errors': 0,
                'slow_requests': 0
            }
        
        self.request_metrics[path]['count'] += 1
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate metrics
            duration_ms = (time.time() - start_time) * 1000
            end_memory = self._get_memory_usage()
            memory_delta = end_memory - start_memory
            
            # Update metrics
            self.request_metrics[path]['total_time'] += duration_ms
            
            # Log slow requests
            if duration_ms > self.slow_request_threshold_ms:
                self.request_metrics[path]['slow_requests'] += 1
                self.logger.performance(
                    f"Slow request: {request.method} {path}",
                    duration_ms,
                    metadata={
                        'memory_delta_mb': memory_delta,
                        'status_code': response.status_code,
                        'threshold_ms': self.slow_request_threshold_ms
                    }
                )
            
            # Log endpoint statistics periodically (every 100 requests)
            if self.request_metrics[path]['count'] % 100 == 0:
                avg_time = self.request_metrics[path]['total_time'] / self.request_metrics[path]['count']
                self.logger.info(
                    f"Endpoint statistics: {path}",
                    extra={
                        'endpoint_stats': True,
                        'path': path,
                        'total_requests': self.request_metrics[path]['count'],
                        'average_time_ms': avg_time,
                        'error_rate': self.request_metrics[path]['errors'] / self.request_metrics[path]['count'],
                        'slow_request_rate': self.request_metrics[path]['slow_requests'] / self.request_metrics[path]['count']
                    }
                )
            
            return response
            
        except Exception as e:
            self.request_metrics[path]['errors'] += 1
            raise
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0


class MedicalOperationMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking medical operations and HIPAA compliance"""
    
    def __init__(self, app, medical_endpoints: Optional[list] = None):
        super().__init__(app)
        self.logger = get_logger('medical.middleware')
        self.medical_endpoints = medical_endpoints or [
            '/api/cases',
            '/api/consultations',
            '/api/patients',
            '/api/medical-history',
            '/api/prescriptions'
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is a medical endpoint
        is_medical = any(request.url.path.startswith(endpoint) for endpoint in self.medical_endpoints)
        
        if not is_medical:
            return await call_next(request)
        
        # Extract patient ID if available
        patient_id = None
        if 'patient_id' in request.path_params:
            patient_id = request.path_params['patient_id']
        elif request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                request._body = body  # Cache body for downstream use
                data = json.loads(body)
                patient_id = data.get('patient_id')
            except:
                pass
        
        # Log medical operation start
        operation = f"{request.method} {request.url.path}"
        self.logger.medical_operation(
            operation,
            patient_id=patient_id,
            details={'endpoint': request.url.path, 'method': request.method}
        )
        
        # Process request
        response = await call_next(request)
        
        # Log audit trail for modifications
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            entity = request.url.path.split('/')[2] if len(request.url.path.split('/')) > 2 else 'unknown'
            self.logger.audit(
                action=request.method,
                entity=entity,
                entity_id=patient_id or 'unknown',
                changes={'status_code': response.status_code}
            )
        
        return response


class AIModelMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking AI model interactions"""
    
    def __init__(self, app, ai_endpoints: Optional[list] = None):
        super().__init__(app)
        self.logger = get_logger('ai.middleware')
        self.ai_endpoints = ai_endpoints or [
            '/api/groq',
            '/api/ai-consultation',
            '/api/diagnosis',
            '/api/recommendations'
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is an AI endpoint
        is_ai = any(request.url.path.startswith(endpoint) for endpoint in self.ai_endpoints)
        
        if not is_ai:
            return await call_next(request)
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Extract model info from response headers if available
        model = response.headers.get('X-AI-Model', 'unknown')
        tokens = response.headers.get('X-Tokens-Used')
        
        # Log AI interaction
        self.logger.ai_model_interaction(
            model=model,
            operation=f"{request.method} {request.url.path}",
            tokens_used=int(tokens) if tokens else None,
            response_time_ms=duration_ms
        )
        
        return response


def setup_unified_middleware(app: FastAPI):
    """Setup all unified middleware components"""
    
    # Note: CORS middleware is already added in main.py, so we skip it here
    # to avoid duplicate middleware
    
    # Security middleware
    app.add_middleware(SecurityMiddleware)
    
    # Medical operation tracking
    app.add_middleware(MedicalOperationMiddleware)
    
    # AI model tracking
    app.add_middleware(AIModelMiddleware)
    
    # Performance monitoring
    app.add_middleware(PerformanceMonitoringMiddleware)
    
    # Unified logging (should be last to catch all)
    app.add_middleware(UnifiedLoggingMiddleware)
    
    # Log middleware setup
    logger = get_logger('api.middleware')
    logger.info("Unified middleware stack configured", extra={
        'middleware_order': [
            'CORS',
            'Security',
            'MedicalOperation',
            'AIModel',
            'PerformanceMonitoring',
            'UnifiedLogging'
        ]
    })