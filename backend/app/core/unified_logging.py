"""
Unified Logging System for Medical AI Platform

This module provides a centralized logging infrastructure with:
- Structured JSON logging
- Context propagation
- Performance tracking
- Security audit trails
- Medical operation logging with HIPAA compliance
- Correlation IDs for request tracking
"""

import logging
import json
import sys
import os
import traceback
import time
import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import uuid
import inspect
from collections import defaultdict
import threading
import platform

# Context variables for request tracking
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

# Global configuration
LOG_DIR = Path(os.getenv('LOG_DIR', './logs'))
LOG_DIR.mkdir(exist_ok=True)

# Log levels per service
SERVICE_LOG_LEVELS = {
    'medical_mcp': os.getenv('MCP_LOG_LEVEL', 'INFO'),
    'groq_doctors': os.getenv('GROQ_LOG_LEVEL', 'INFO'),
    'database': os.getenv('DB_LOG_LEVEL', 'INFO'),
    'api': os.getenv('API_LOG_LEVEL', 'INFO'),
    'security': os.getenv('SECURITY_LOG_LEVEL', 'INFO'),
    'performance': os.getenv('PERF_LOG_LEVEL', 'INFO'),
}


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get context data
        ctx = request_context.get()
        corr_id = correlation_id.get()
        
        # Build structured log entry
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add correlation ID if present
        if corr_id:
            log_entry['correlation_id'] = corr_id
            
        # Add context data
        if ctx:
            log_entry['context'] = ctx
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
            
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'exc_info',
                          'exc_text', 'stack_info', 'pathname', 'processName',
                          'process', 'threadName', 'thread', 'taskName']:
                log_entry[key] = value
                
        return json.dumps(log_entry, default=str)


class WindowsSafeRotatingFileHandler(RotatingFileHandler):
    """A rotating file handler that works better on Windows by handling file locking issues"""
    
    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        Handle Windows file locking issues gracefully.
        """
        if platform.system() == 'Windows':
            # On Windows, we need to close the file before renaming
            if self.stream:
                self.stream.close()
                self.stream = None
            
            # Try the rollover with retries
            for attempt in range(3):
                try:
                    if self.backupCount > 0:
                        for i in range(self.backupCount - 1, 0, -1):
                            sfn = self.rotation_filename("%s.%d" % (self.baseFilename, i))
                            dfn = self.rotation_filename("%s.%d" % (self.baseFilename, i + 1))
                            if os.path.exists(sfn):
                                if os.path.exists(dfn):
                                    os.remove(dfn)
                                os.rename(sfn, dfn)
                        dfn = self.rotation_filename(self.baseFilename + ".1")
                        if os.path.exists(dfn):
                            os.remove(dfn)
                        if os.path.exists(self.baseFilename):
                            os.rename(self.baseFilename, dfn)
                    break
                except (OSError, PermissionError) as e:
                    if attempt < 2:
                        time.sleep(0.1)  # Brief pause before retry
                    else:
                        # If all retries fail, just truncate the current file
                        try:
                            with open(self.baseFilename, 'w'):
                                pass
                        except:
                            pass  # Give up if we can't even truncate
            
            # Reopen the file
            self.stream = self._open()
        else:
            # On Unix-like systems, use the standard behavior
            super().doRollover()


class UnifiedLogger:
    """Enhanced logger with specialized methods for medical AI platform"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False
        self._setup_logger()
        
    def _setup_logger(self):
        """Configure logger if not already configured"""
        # Clear any existing handlers to prevent duplicates
        self.logger.handlers.clear()
        
        # Now add our handlers
        # Set log level based on service
        service_name = self.logger.name.split('.')[0]
        level = SERVICE_LOG_LEVELS.get(service_name, os.getenv('LOG_LEVEL', 'INFO'))
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
        
        # In development on Windows, use simpler file handling to avoid permission issues
        is_windows = platform.system() == 'Windows'
        is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
        
        if is_windows and is_development:
            # Use simple file handler without rotation in development
            app_log_path = LOG_DIR / 'medical_ai.log'
            file_handler = logging.FileHandler(app_log_path, mode='a')
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
            
            # Error log handler
            error_log_path = LOG_DIR / 'errors.log'
            error_handler = logging.FileHandler(error_log_path, mode='a')
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(error_handler)
        else:
            # File handler - main application log with rotation
            app_log_path = LOG_DIR / 'medical_ai.log'
            file_handler = WindowsSafeRotatingFileHandler(
                app_log_path,
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=10
            )
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
            
            # Error log handler
            error_log_path = LOG_DIR / 'errors.log'
            error_handler = WindowsSafeRotatingFileHandler(
                error_log_path,
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=5
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(error_handler)
    
    def with_context(self, **kwargs) -> 'UnifiedLogger':
        """Add context to logs"""
        ctx = request_context.get().copy()
        ctx.update(kwargs)
        request_context.set(ctx)
        return self
    
    def set_correlation_id(self, corr_id: str):
        """Set correlation ID for request tracking"""
        correlation_id.set(corr_id)
    
    # Standard logging methods
    def debug(self, message: str, exc_info: bool = False, **kwargs):
        self.logger.debug(message, exc_info=exc_info, extra=kwargs)
    
    def info(self, message: str, exc_info: bool = False, **kwargs):
        self.logger.info(message, exc_info=exc_info, extra=kwargs)
    
    def warning(self, message: str, exc_info: bool = False, **kwargs):
        self.logger.warning(message, exc_info=exc_info, extra=kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        self.logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        self.logger.critical(message, exc_info=exc_info, extra=kwargs)
    
    # Specialized logging methods
    def security(self, event_type: str, details: Dict[str, Any], severity: str = 'INFO'):
        """Log security-related events"""
        self.logger.log(
            getattr(logging, severity.upper()),
            f"Security Event: {event_type}",
            extra={
                'security_event': True,
                'event_type': event_type,
                'details': details,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
    
    def audit(self, action: str, entity: str, entity_id: str, changes: Optional[Dict] = None):
        """Log audit trail for compliance"""
        self.logger.info(
            f"Audit: {action} on {entity}",
            extra={
                'audit_trail': True,
                'action': action,
                'entity': entity,
                'entity_id': entity_id,
                'changes': changes,
                'user': request_context.get().get('user_id', 'system'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
    
    def api_call(self, service: str, endpoint: str, method: str, 
                 status_code: Optional[int] = None, duration_ms: Optional[float] = None):
        """Log external API calls"""
        self.logger.info(
            f"API Call: {method} {service} {endpoint}",
            extra={
                'api_call': True,
                'service': service,
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'duration_ms': duration_ms
            }
        )
    
    def performance(self, operation: str, duration_ms: float, metadata: Optional[Dict] = None):
        """Log performance metrics"""
        self.logger.info(
            f"Performance: {operation} took {duration_ms:.2f}ms",
            extra={
                'performance_metric': True,
                'operation': operation,
                'duration_ms': duration_ms,
                'metadata': metadata or {}
            }
        )
    
    def medical_operation(self, operation: str, patient_id: Optional[str] = None, 
                         details: Optional[Dict] = None, hipaa_compliant: bool = True):
        """Log medical operations with HIPAA considerations"""
        # Mask patient ID if HIPAA compliant logging is enabled
        if hipaa_compliant and patient_id:
            masked_id = f"***{patient_id[-4:]}" if len(patient_id) > 4 else "****"
        else:
            masked_id = patient_id
            
        self.logger.info(
            f"Medical Operation: {operation}",
            extra={
                'medical_operation': True,
                'operation': operation,
                'patient_id': masked_id,
                'details': details or {},
                'hipaa_compliant': hipaa_compliant
            }
        )
    
    def ai_model_interaction(self, model: str, operation: str, 
                            tokens_used: Optional[int] = None, 
                            response_time_ms: Optional[float] = None):
        """Log AI model interactions"""
        self.logger.info(
            f"AI Model: {model} - {operation}",
            extra={
                'ai_interaction': True,
                'model': model,
                'operation': operation,
                'tokens_used': tokens_used,
                'response_time_ms': response_time_ms
            }
        )


# Logger factory with thread-safe initialization
_logger_cache = {}
_logger_lock = threading.Lock()

def get_logger(name: str) -> UnifiedLogger:
    """
    Get or create a logger instance (thread-safe)
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        UnifiedLogger instance
    """
    if name not in _logger_cache:
        with _logger_lock:
            # Double-check pattern to prevent race conditions
            if name not in _logger_cache:
                _logger_cache[name] = UnifiedLogger(name)
    return _logger_cache[name]


# Decorators for automatic logging
def log_performance(operation_name: Optional[str] = None):
    """Decorator to automatically log function performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            op_name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.performance(op_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Performance: {op_name} failed after {duration_ms:.2f}ms",
                    exc_info=True,
                    extra={'operation': op_name, 'duration_ms': duration_ms}
                )
                raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            op_name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.performance(op_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Performance: {op_name} failed after {duration_ms:.2f}ms",
                    exc_info=True,
                    extra={'operation': op_name, 'duration_ms': duration_ms}
                )
                raise
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    return decorator


def log_medical_operation(operation_name: Optional[str] = None):
    """Decorator to automatically log medical operations"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            op_name = operation_name or func.__name__
            
            # Try to extract patient_id from arguments
            patient_id = kwargs.get('patient_id') or (args[1] if len(args) > 1 else None)
            
            try:
                result = await func(*args, **kwargs)
                logger.medical_operation(op_name, patient_id)
                return result
            except Exception as e:
                logger.error(
                    f"Medical operation failed: {op_name}",
                    exc_info=True,
                    extra={'operation': op_name, 'patient_id': patient_id}
                )
                raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            op_name = operation_name or func.__name__
            
            # Try to extract patient_id from arguments
            patient_id = kwargs.get('patient_id') or (args[1] if len(args) > 1 else None)
            
            try:
                result = func(*args, **kwargs)
                logger.medical_operation(op_name, patient_id)
                return result
            except Exception as e:
                logger.error(
                    f"Medical operation failed: {op_name}",
                    exc_info=True,
                    extra={'operation': op_name, 'patient_id': patient_id}
                )
                raise
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    return decorator


def with_context(**context_kwargs):
    """Decorator to add context to all logs within a function"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Save current context
            old_context = request_context.get()
            new_context = old_context.copy()
            new_context.update(context_kwargs)
            
            # Set new context
            request_context.set(new_context)
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                # Restore old context
                request_context.set(old_context)
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Save current context
            old_context = request_context.get()
            new_context = old_context.copy()
            new_context.update(context_kwargs)
            
            # Set new context
            request_context.set(new_context)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Restore old context
                request_context.set(old_context)
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Initialize root logger with unified configuration
def initialize_unified_logging():
    """Initialize the unified logging system"""
    # Set correlation ID for system startup
    correlation_id.set(f"system-{uuid.uuid4().hex[:8]}")
    
    # Configure root logger to prevent propagation
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Clear any default handlers
    root_logger.setLevel(logging.WARNING)  # Set high level to avoid noise
    
    # Disable problematic third-party loggers on Windows
    if platform.system() == 'Windows':
        # Disable httpx and httpcore file logging to avoid permission issues
        httpx_logger = logging.getLogger('httpx')
        httpx_logger.setLevel(logging.WARNING)
        httpx_logger.handlers = [h for h in httpx_logger.handlers if not isinstance(h, logging.FileHandler)]
        
        httpcore_logger = logging.getLogger('httpcore')
        httpcore_logger.setLevel(logging.WARNING)
        httpcore_logger.handlers = [h for h in httpcore_logger.handlers if not isinstance(h, logging.FileHandler)]
        
        # Also check for any 'ubicon' logger
        ubicon_logger = logging.getLogger('ubicon')
        ubicon_logger.setLevel(logging.WARNING)
        ubicon_logger.handlers = []
    
    # Get application logger
    logger = get_logger('medical_ai')
    logger.info(
        "Unified Logging System Initialized",
        extra={
            'log_dir': str(LOG_DIR),
            'service_levels': SERVICE_LOG_LEVELS,
            'json_format': True
        }
    )
    
    return logger