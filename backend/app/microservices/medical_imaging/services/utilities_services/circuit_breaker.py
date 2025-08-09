"""
Circuit Breaker Pattern Implementation
Prevents cascade failures and provides automatic recovery
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for individual services"""
    
    def __init__(self, 
                 failure_threshold: int = 3,
                 timeout: int = 60,
                 recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # How long to stay open
        self.recovery_timeout = recovery_timeout  # Timeout for half-open test
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.last_success_time: Optional[datetime] = None
        
    def record_success(self):
        """Record successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_success_time = datetime.utcnow()
        logger.debug(f"Circuit breaker recorded success, state: {self.state.value}")
        
    def record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
            
    def can_attempt(self) -> bool:
        """Check if we can attempt a call"""
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).seconds
                if time_since_failure > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker moved to HALF_OPEN state")
                    return True
            return False
            
        # HALF_OPEN state - allow one test
        return True
    
    def get_state(self) -> str:
        """Get current state as string"""
        return self.state.value


class EnhancedReportGeneratorWithFallback:
    """Report generator with circuit breaker and caching"""
    
    def __init__(self, providers: Dict[str, Any]):
        self.providers = providers
        self.circuit_breakers = {
            name: CircuitBreaker() for name in providers
        }
        self.response_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps: Dict[str, datetime] = {}
        
    def _get_cache_key(self, kwargs: dict) -> str:
        """Generate cache key from arguments"""
        # Create a stable key from the arguments
        key_parts = []
        for k, v in sorted(kwargs.items()):
            if k in ['image_data', 'image_type', 'patient_info']:
                if isinstance(v, dict):
                    v_str = str(sorted(v.items()))
                else:
                    v_str = str(v)[:100]  # Limit length
                key_parts.append(f"{k}:{v_str}")
        return "|".join(key_parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid"""
        if cache_key not in self.cache_timestamps:
            return False
            
        age = (datetime.utcnow() - self.cache_timestamps[cache_key]).seconds
        return age < self.cache_ttl
        
    async def generate_with_fallback(self, **kwargs) -> str:
        """Generate with automatic fallback and circuit breaker"""
        # Check cache first
        cache_key = self._get_cache_key(kwargs)
        if cache_key in self.response_cache and self._is_cache_valid(cache_key):
            logger.info("Returning cached response")
            return self.response_cache[cache_key]
            
        errors = []
        
        # Try each provider in order
        for name, provider in self.providers.items():
            if not provider:
                continue
                
            cb = self.circuit_breakers[name]
            
            if not cb.can_attempt():
                logger.warning(f"Circuit breaker OPEN for {name}, skipping")
                errors.append(f"{name}: Circuit breaker open")
                continue
                
            try:
                logger.info(f"Attempting generation with {name}")
                
                # Add timeout to prevent hanging
                async with asyncio.timeout(30):
                    # Call the appropriate method based on provider type
                    if hasattr(provider, 'generate_comprehensive_analysis'):
                        result = await provider.generate_comprehensive_analysis(**kwargs)
                    elif hasattr(provider, 'generate_image_analysis'):
                        result = await provider.generate_image_analysis(**kwargs)
                    else:
                        raise AttributeError(f"Provider {name} has no suitable generation method")
                
                # Success - record it
                cb.record_success()
                
                # Cache the response
                self.response_cache[cache_key] = result
                self.cache_timestamps[cache_key] = datetime.utcnow()
                
                logger.info(f"Successfully generated with {name}")
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"{name} timed out after 30 seconds")
                cb.record_failure()
                errors.append(f"{name}: Timeout")
                
            except Exception as e:
                logger.error(f"{name} failed: {e}")
                cb.record_failure()
                errors.append(f"{name}: {str(e)}")
                
            # Exponential backoff before trying next provider
            if len(errors) < len(self.providers):
                backoff = min(2 ** len(errors), 10)
                logger.debug(f"Backing off for {backoff} seconds before next attempt")
                await asyncio.sleep(backoff)
        
        # All providers failed
        error_msg = f"All providers failed: {'; '.join(errors)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_circuit_states(self) -> Dict[str, str]:
        """Get current state of all circuit breakers"""
        return {
            name: cb.get_state() 
            for name, cb in self.circuit_breakers.items()
        }
    
    def clear_cache(self):
        """Clear the response cache"""
        self.response_cache.clear()
        self.cache_timestamps.clear()
        logger.info("Response cache cleared")