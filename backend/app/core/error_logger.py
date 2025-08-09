"""
Enhanced Error Logger for Unified Medical AI Platform
Captures detailed error information for debugging API and service issues
"""

import logging
import traceback
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import sys
from functools import wraps

# Error log file path
ERROR_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
ERROR_LOG_DIR.mkdir(exist_ok=True)
ERROR_LOG_FILE = ERROR_LOG_DIR / "api_errors.log"
DETAILED_ERROR_LOG = ERROR_LOG_DIR / "detailed_errors.json"

class ErrorLogger:
    """Enhanced error logger with detailed debugging information"""
    
    def __init__(self):
        # Configure file handler for error logs
        self.error_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
        self.error_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            'File: %(pathname)s:%(lineno)d\n'
            'Function: %(funcName)s\n'
            '---'
        )
        self.error_handler.setFormatter(formatter)
        
        # JSON error log for detailed analysis
        self.detailed_errors = []
        
    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Log error with full context and traceback"""
        error_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "python_version": sys.version,
            "stack_trace": []
        }
        
        # Extract detailed stack trace
        tb = traceback.extract_tb(error.__traceback__)
        for frame in tb:
            error_info["stack_trace"].append({
                "file": frame.filename,
                "line": frame.lineno,
                "function": frame.name,
                "code": frame.line
            })
        
        # Save to detailed log
        self._save_detailed_error(error_info)
        
        # Log to standard error log
        logger = logging.getLogger(context.get("logger_name", __name__))
        # Don't add handlers here - let the unified logging system manage handlers
        # This prevents duplicate log entries
        
        logger.error(
            f"{error_info['error_type']}: {error_info['error_message']}\n"
            f"Context: {json.dumps(context, indent=2)}\n"
            f"Traceback:\n{error_info['traceback']}"
        )
        
        return error_info
    
    def _save_detailed_error(self, error_info: Dict[str, Any]):
        """Save detailed error information to JSON file"""
        try:
            # Load existing errors
            if DETAILED_ERROR_LOG.exists():
                with open(DETAILED_ERROR_LOG, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
            else:
                errors = []
            
            # Add new error
            errors.append(error_info)
            
            # Keep only last 1000 errors
            if len(errors) > 1000:
                errors = errors[-1000:]
            
            # Save back
            with open(DETAILED_ERROR_LOG, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Failed to save detailed error log: {e}")
    
    def get_recent_errors(self, count: int = 10) -> list:
        """Get recent errors from the detailed log"""
        try:
            if DETAILED_ERROR_LOG.exists():
                with open(DETAILED_ERROR_LOG, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
                return errors[-count:]
            return []
        except Exception:
            return []

# Global error logger instance
error_logger = ErrorLogger()

def log_api_error(func):
    """Decorator to log API endpoint errors"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Extract request context if available
            context = {
                "function": func.__name__,
                "module": func.__module__,
                "args": str(args)[:500],  # Limit size
                "kwargs": str(kwargs)[:500],
                "logger_name": func.__module__
            }
            
            # Try to extract request information
            for arg in args:
                if hasattr(arg, 'url'):  # FastAPI Request object
                    context["request_url"] = str(arg.url)
                    context["request_method"] = arg.method
                    if hasattr(arg, 'headers'):
                        context["request_headers"] = dict(arg.headers)
                    break
            
            # Log the error
            error_info = error_logger.log_error(e, context)
            
            # Re-raise the error
            raise
    
    return wrapper

def log_service_error(service_name: str):
    """Decorator to log service/microservice errors"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    "service": service_name,
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args)[:500],
                    "kwargs": str(kwargs)[:500],
                    "logger_name": f"service.{service_name}"
                }
                
                # Log the error
                error_info = error_logger.log_error(e, context)
                
                # Re-raise the error
                raise
        
        return wrapper
    return decorator

# Utility function for manual error logging
def log_error(error: Exception, **context):
    """Manually log an error with context"""
    return error_logger.log_error(error, context)