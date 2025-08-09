"""
Comprehensive API Error Handler for Medical AI System
Provides intelligent error handling, classification, and recovery strategies
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of API errors"""
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    PAYMENT_REQUIRED = "payment_required"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"           # Temporary, retry immediately
    MEDIUM = "medium"     # Temporary, retry with backoff
    HIGH = "high"         # Requires intervention, longer backoff
    CRITICAL = "critical" # Permanent or semi-permanent failure


class APIErrorHandler:
    """
    Comprehensive API error handler with intelligent classification and recovery
    """
    
    # Error pattern definitions
    ERROR_PATTERNS = {
        ErrorType.RATE_LIMIT: [
            r"429",
            r"rate.?limit",
            r"too.?many.?requests",
            r"requests.?per.?minute",
            r"requests.?per.?second",
            r"throttle",
            r"rate.?exceeded"
        ],
        ErrorType.QUOTA_EXCEEDED: [
            r"quota.?exceeded",
            r"quota.?exhausted",
            r"usage.?limit",
            r"daily.?limit",
            r"monthly.?limit",
            r"resource.?exhausted",
            r"limit.?reached",
            r"credits.?exhausted"
        ],
        ErrorType.AUTHENTICATION: [
            r"401",
            r"unauthorized",
            r"invalid.?api.?key",
            r"authentication.?failed",
            r"api.?key.?not.?found",
            r"invalid.?credentials"
        ],
        ErrorType.AUTHORIZATION: [
            r"403",
            r"forbidden",
            r"access.?denied",
            r"insufficient.?permissions",
            r"not.?authorized"
        ],
        ErrorType.NOT_FOUND: [
            r"404",
            r"not.?found",
            r"model.?not.?found",
            r"endpoint.?not.?found",
            r"resource.?not.?found"
        ],
        ErrorType.SERVER_ERROR: [
            r"500",
            r"502",
            r"503",
            r"504",
            r"internal.?server.?error",
            r"bad.?gateway",
            r"service.?unavailable",
            r"gateway.?timeout",
            r"server.?error"
        ],
        ErrorType.NETWORK_ERROR: [
            r"connection.?error",
            r"network.?error",
            r"dns.?error",
            r"connection.?refused",
            r"connection.?timeout",
            r"network.?unreachable"
        ],
        ErrorType.TIMEOUT: [
            r"timeout",
            r"timed.?out",
            r"request.?timeout",
            r"read.?timeout",
            r"connect.?timeout"
        ],
        ErrorType.PAYMENT_REQUIRED: [
            r"402",
            r"payment.?required",
            r"insufficient.?funds",
            r"billing.?error",
            r"subscription.?expired",
            r"payment.?method"
        ],
        ErrorType.INVALID_REQUEST: [
            r"400",
            r"bad.?request",
            r"invalid.?request",
            r"malformed.?request",
            r"invalid.?parameter",
            r"missing.?parameter"
        ]
    }
    
    # Recovery strategies for each error type
    RECOVERY_STRATEGIES = {
        ErrorType.RATE_LIMIT: {
            'retry': True,
            'backoff_base': 1,
            'backoff_max': 60,
            'severity': ErrorSeverity.MEDIUM,
            'switch_provider': True,
            'switch_api_key': True
        },
        ErrorType.QUOTA_EXCEEDED: {
            'retry': True,
            'backoff_base': 60,
            'backoff_max': 3600,
            'severity': ErrorSeverity.HIGH,
            'switch_provider': True,
            'switch_api_key': True
        },
        ErrorType.AUTHENTICATION: {
            'retry': False,
            'backoff_base': 0,
            'backoff_max': 0,
            'severity': ErrorSeverity.CRITICAL,
            'switch_provider': False,
            'switch_api_key': True
        },
        ErrorType.AUTHORIZATION: {
            'retry': False,
            'backoff_base': 0,
            'backoff_max': 0,
            'severity': ErrorSeverity.CRITICAL,
            'switch_provider': True,
            'switch_api_key': False
        },
        ErrorType.NOT_FOUND: {
            'retry': False,
            'backoff_base': 0,
            'backoff_max': 0,
            'severity': ErrorSeverity.HIGH,
            'switch_provider': True,
            'switch_api_key': False
        },
        ErrorType.SERVER_ERROR: {
            'retry': True,
            'backoff_base': 5,
            'backoff_max': 300,
            'severity': ErrorSeverity.MEDIUM,
            'switch_provider': True,
            'switch_api_key': False
        },
        ErrorType.NETWORK_ERROR: {
            'retry': True,
            'backoff_base': 2,
            'backoff_max': 60,
            'severity': ErrorSeverity.MEDIUM,
            'switch_provider': False,
            'switch_api_key': False
        },
        ErrorType.TIMEOUT: {
            'retry': True,
            'backoff_base': 5,
            'backoff_max': 120,
            'severity': ErrorSeverity.MEDIUM,
            'switch_provider': False,
            'switch_api_key': False
        },
        ErrorType.PAYMENT_REQUIRED: {
            'retry': False,
            'backoff_base': 0,
            'backoff_max': 0,
            'severity': ErrorSeverity.CRITICAL,
            'switch_provider': True,
            'switch_api_key': True
        },
        ErrorType.INVALID_REQUEST: {
            'retry': False,
            'backoff_base': 0,
            'backoff_max': 0,
            'severity': ErrorSeverity.LOW,
            'switch_provider': False,
            'switch_api_key': False
        },
        ErrorType.UNKNOWN: {
            'retry': True,
            'backoff_base': 10,
            'backoff_max': 300,
            'severity': ErrorSeverity.MEDIUM,
            'switch_provider': True,
            'switch_api_key': False
        }
    }
    
    def __init__(self):
        """Initialize error handler"""
        self.error_history = []
        self.provider_error_counts = {}
        self.api_key_error_counts = {}
    
    def classify_error(self, error: Exception, provider: str = "", api_key_index: int = 0) -> Tuple[ErrorType, ErrorSeverity, Dict[str, Any]]:
        """
        Classify an error and determine recovery strategy
        
        Returns:
            Tuple of (error_type, severity, recovery_info)
        """
        error_str = str(error).lower()
        error_type = ErrorType.UNKNOWN
        
        # Try to classify the error
        for err_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_str, re.IGNORECASE):
                    error_type = err_type
                    break
            if error_type != ErrorType.UNKNOWN:
                break
        
        # Get recovery strategy
        strategy = self.RECOVERY_STRATEGIES.get(error_type, self.RECOVERY_STRATEGIES[ErrorType.UNKNOWN])
        severity = strategy['severity']
        
        # Extract additional information
        retry_after = self._extract_retry_after(str(error))
        
        recovery_info = {
            'should_retry': strategy['retry'],
            'backoff_base': strategy['backoff_base'],
            'backoff_max': strategy['backoff_max'],
            'switch_provider': strategy['switch_provider'],
            'switch_api_key': strategy['switch_api_key'],
            'retry_after': retry_after,
            'provider': provider,
            'api_key_index': api_key_index
        }
        
        # Log error for tracking
        self._log_error(error_type, severity, provider, api_key_index, str(error))
        
        return error_type, severity, recovery_info
    
    def _extract_retry_after(self, error_str: str) -> Optional[int]:
        """Extract retry-after time from error message"""
        # Look for retry-after patterns
        patterns = [
            r"retry.?after.?(\d+)",
            r"wait.?(\d+).?seconds",
            r"try.?again.?in.?(\d+)",
            r"back.?off.?(\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_str, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _log_error(self, error_type: ErrorType, severity: ErrorSeverity, provider: str, api_key_index: int, error_message: str):
        """Log error for tracking and analysis"""
        error_record = {
            'timestamp': datetime.now(),
            'error_type': error_type.value,
            'severity': severity.value,
            'provider': provider,
            'api_key_index': api_key_index,
            'message': error_message
        }
        
        self.error_history.append(error_record)
        
        # Keep only last 1000 errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Update provider error counts
        if provider:
            if provider not in self.provider_error_counts:
                self.provider_error_counts[provider] = {}
            
            if error_type.value not in self.provider_error_counts[provider]:
                self.provider_error_counts[provider][error_type.value] = 0
            
            self.provider_error_counts[provider][error_type.value] += 1
        
        # Update API key error counts  
        key_id = f"{provider}_{api_key_index}"
        if key_id not in self.api_key_error_counts:
            self.api_key_error_counts[key_id] = {}
        
        if error_type.value not in self.api_key_error_counts[key_id]:
            self.api_key_error_counts[key_id][error_type.value] = 0
        
        self.api_key_error_counts[key_id][error_type.value] += 1
        
        # Log with appropriate level
        if severity == ErrorSeverity.CRITICAL:
            logger.error(f"CRITICAL {error_type.value} error in {provider}: {error_message}")
        elif severity == ErrorSeverity.HIGH:
            logger.warning(f"HIGH {error_type.value} error in {provider}: {error_message}")
        else:
            logger.info(f"{severity.value.upper()} {error_type.value} error in {provider}: {error_message}")
    
    def should_switch_provider(self, provider: str, error_type: ErrorType) -> bool:
        """Determine if we should switch providers based on error history"""
        if provider not in self.provider_error_counts:
            return False
        
        provider_errors = self.provider_error_counts[provider]
        
        # Switch if too many critical errors
        critical_errors = (
            provider_errors.get(ErrorType.AUTHENTICATION.value, 0) +
            provider_errors.get(ErrorType.PAYMENT_REQUIRED.value, 0)
        )
        
        if critical_errors >= 2:
            return True
        
        # Switch if too many quota/rate limit errors
        quota_errors = (
            provider_errors.get(ErrorType.RATE_LIMIT.value, 0) +
            provider_errors.get(ErrorType.QUOTA_EXCEEDED.value, 0)
        )
        
        if quota_errors >= 5:
            return True
        
        return False
    
    def should_switch_api_key(self, provider: str, api_key_index: int, error_type: ErrorType) -> bool:
        """Determine if we should switch API keys"""
        key_id = f"{provider}_{api_key_index}"
        
        if key_id not in self.api_key_error_counts:
            return False
        
        key_errors = self.api_key_error_counts[key_id]
        
        # Switch if authentication errors
        if key_errors.get(ErrorType.AUTHENTICATION.value, 0) >= 1:
            return True
        
        # Switch if multiple quota errors
        if key_errors.get(ErrorType.QUOTA_EXCEEDED.value, 0) >= 3:
            return True
        
        return False
    
    def get_recommended_backoff(self, error_type: ErrorType, attempt: int, retry_after: Optional[int] = None) -> int:
        """Calculate recommended backoff time"""
        if retry_after:
            return retry_after
        
        strategy = self.RECOVERY_STRATEGIES.get(error_type, self.RECOVERY_STRATEGIES[ErrorType.UNKNOWN])
        
        base = strategy['backoff_base']
        max_backoff = strategy['backoff_max']
        
        # Exponential backoff with jitter
        backoff = min(base * (2 ** attempt), max_backoff)
        
        # Add jitter (±25%)
        import random
        jitter = backoff * 0.25 * (2 * random.random() - 1)
        
        return max(1, int(backoff + jitter))
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        stats = {
            'total_errors': len(self.error_history),
            'errors_by_type': {},
            'errors_by_severity': {},
            'errors_by_provider': {},
            'recent_errors': [],
            'provider_health': {}
        }
        
        # Analyze error history
        for error in self.error_history:
            error_type = error['error_type']
            severity = error['severity']
            provider = error['provider']
            
            # Count by type
            stats['errors_by_type'][error_type] = stats['errors_by_type'].get(error_type, 0) + 1
            
            # Count by severity
            stats['errors_by_severity'][severity] = stats['errors_by_severity'].get(severity, 0) + 1
            
            # Count by provider
            if provider:
                stats['errors_by_provider'][provider] = stats['errors_by_provider'].get(provider, 0) + 1
        
        # Recent errors (last 10)
        stats['recent_errors'] = self.error_history[-10:] if self.error_history else []
        
        # Provider health assessment
        for provider, error_counts in self.provider_error_counts.items():
            total_errors = sum(error_counts.values())
            critical_errors = (
                error_counts.get(ErrorType.AUTHENTICATION.value, 0) +
                error_counts.get(ErrorType.PAYMENT_REQUIRED.value, 0)
            )
            
            if critical_errors > 0:
                health = "critical"
            elif total_errors > 10:
                health = "poor"
            elif total_errors > 5:
                health = "fair"
            else:
                health = "good"
            
            stats['provider_health'][provider] = {
                'health': health,
                'total_errors': total_errors,
                'critical_errors': critical_errors,
                'error_breakdown': error_counts
            }
        
        return stats
    
    def clear_error_history(self, provider: Optional[str] = None):
        """Clear error history for a specific provider or all providers"""
        if provider:
            # Clear history for specific provider
            self.error_history = [e for e in self.error_history if e['provider'] != provider]
            
            # Clear provider error counts
            if provider in self.provider_error_counts:
                del self.provider_error_counts[provider]
            
            # Clear API key error counts for this provider
            keys_to_remove = [k for k in self.api_key_error_counts.keys() if k.startswith(f"{provider}_")]
            for key in keys_to_remove:
                del self.api_key_error_counts[key]
            
            logger.info(f"Cleared error history for provider: {provider}")
        else:
            # Clear all history
            self.error_history.clear()
            self.provider_error_counts.clear()
            self.api_key_error_counts.clear()
            logger.info("Cleared all error history")
    
    def get_provider_recommendations(self) -> Dict[str, str]:
        """Get recommendations for each provider based on error patterns"""
        recommendations = {}
        
        for provider, error_counts in self.provider_error_counts.items():
            total_errors = sum(error_counts.values())
            
            if total_errors == 0:
                recommendations[provider] = "Healthy - no errors recorded"
                continue
            
            # Analyze error patterns
            auth_errors = error_counts.get(ErrorType.AUTHENTICATION.value, 0)
            quota_errors = error_counts.get(ErrorType.QUOTA_EXCEEDED.value, 0)
            rate_limit_errors = error_counts.get(ErrorType.RATE_LIMIT.value, 0)
            payment_errors = error_counts.get(ErrorType.PAYMENT_REQUIRED.value, 0)
            
            if auth_errors > 0:
                recommendations[provider] = "Check API key configuration - authentication failures detected"
            elif payment_errors > 0:
                recommendations[provider] = "Check billing/subscription - payment required errors detected"
            elif quota_errors > 5:
                recommendations[provider] = "Consider upgrading plan - frequent quota exceeded errors"
            elif rate_limit_errors > 10:
                recommendations[provider] = "Implement rate limiting - frequent rate limit errors"
            elif total_errors > 15:
                recommendations[provider] = "Monitor closely - high error rate detected"
            else:
                recommendations[provider] = "Stable with minor issues - continue monitoring"
        
        return recommendations


# Global error handler instance
api_error_handler = APIErrorHandler()