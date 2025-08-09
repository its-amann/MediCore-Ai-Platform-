"""
Advanced Rate Limit Manager for Medical AI System
Handles exponential backoff, quota tracking, and intelligent fallback across all providers
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from enum import Enum
import json
import hashlib

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Status of API providers"""
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited" 
    QUOTA_EXCEEDED = "quota_exceeded"
    ERROR = "error"
    TEMPORARILY_DISABLED = "temporarily_disabled"


class RateLimitError(Exception):
    """Raised when rate limits are exceeded"""
    def __init__(self, message: str, provider: str, retry_after: Optional[int] = None):
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(message)


class ExponentialBackoff:
    """Implements exponential backoff with jitter"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 300.0, multiplier: float = 2.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.attempt = 0
    
    def get_delay(self) -> float:
        """Calculate next delay with exponential backoff and jitter"""
        import random
        delay = min(self.base_delay * (self.multiplier ** self.attempt), self.max_delay)
        # Add jitter (±25% of delay)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        self.attempt += 1
        return max(0.1, delay + jitter)
    
    def reset(self):
        """Reset backoff counter"""
        self.attempt = 0


class ProviderConfig:
    """Configuration for each provider"""
    
    def __init__(
        self,
        name: str,
        requests_per_minute: int = 60,
        requests_per_day: int = 1000,
        burst_limit: int = 10,
        cooldown_minutes: int = 5,
        priority: int = 1  # Lower number = higher priority
    ):
        self.name = name
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        self.burst_limit = burst_limit
        self.cooldown_minutes = cooldown_minutes
        self.priority = priority


class RequestCache:
    """Simple in-memory cache for API responses"""
    
    def __init__(self, max_size: int = 1000, ttl_minutes: int = 60):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.ttl_minutes = ttl_minutes
    
    def _generate_key(self, provider: str, method: str, **kwargs) -> str:
        """Generate cache key from request parameters"""
        # Create a deterministic hash of the request parameters
        content = f"{provider}:{method}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, provider: str, method: str, **kwargs) -> Optional[Any]:
        """Get cached response if available and not expired"""
        key = self._generate_key(provider, method, **kwargs)
        
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry['expires']:
                logger.info(f"Cache hit for {provider}:{method}")
                return entry['data']
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, provider: str, method: str, data: Any, **kwargs):
        """Cache a response"""
        key = self._generate_key(provider, method, **kwargs)
        
        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            # Remove 10% of oldest entries
            to_remove = sorted(self.cache.items(), key=lambda x: x[1]['created'])[:self.max_size // 10]
            for old_key, _ in to_remove:
                del self.cache[old_key]
        
        self.cache[key] = {
            'data': data,
            'created': datetime.now(),
            'expires': datetime.now() + timedelta(minutes=self.ttl_minutes)
        }
        logger.debug(f"Cached response for {provider}:{method}")


class AdvancedRateLimitManager:
    """
    Advanced rate limit manager with:
    - Exponential backoff with jitter
    - Request queuing and throttling
    - Response caching
    - Provider health monitoring
    - Intelligent fallback routing
    """
    
    # Default provider configurations
    DEFAULT_CONFIGS = {
        'gemini': ProviderConfig('gemini', requests_per_minute=15, requests_per_day=1500, priority=1),
        'openrouter': ProviderConfig('openrouter', requests_per_minute=20, requests_per_day=1000, priority=2),
        'groq': ProviderConfig('groq', requests_per_minute=30, requests_per_day=2000, priority=3),
        'together': ProviderConfig('together', requests_per_minute=10, requests_per_day=500, priority=4)
    }
    
    def __init__(self, cache_enabled: bool = True, cache_ttl_minutes: int = 30):
        # Provider tracking
        self.providers: Dict[str, ProviderConfig] = self.DEFAULT_CONFIGS.copy()
        self.provider_status: Dict[str, ProviderStatus] = {}
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=2000))
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.cooldown_until: Dict[str, datetime] = {}
        self.backoff_managers: Dict[str, ExponentialBackoff] = {}
        
        # Request queuing
        self.request_queues: Dict[str, asyncio.Queue] = {}
        self.processing_locks: Dict[str, asyncio.Lock] = {}
        
        # Response caching
        self.cache_enabled = cache_enabled
        self.cache = RequestCache(ttl_minutes=cache_ttl_minutes) if cache_enabled else None
        
        # Initialize provider states
        for provider_name in self.providers:
            self.provider_status[provider_name] = ProviderStatus.ACTIVE
            self.backoff_managers[provider_name] = ExponentialBackoff()
            self.request_queues[provider_name] = asyncio.Queue()
            self.processing_locks[provider_name] = asyncio.Lock()
        
        logger.info(f"Advanced Rate Limit Manager initialized with {len(self.providers)} providers")
    
    def add_provider(self, name: str, config: ProviderConfig):
        """Add a new provider configuration"""
        self.providers[name] = config
        self.provider_status[name] = ProviderStatus.ACTIVE
        self.backoff_managers[name] = ExponentialBackoff()
        self.request_queues[name] = asyncio.Queue()
        self.processing_locks[name] = asyncio.Lock()
        logger.info(f"Added provider: {name}")
    
    def _clean_old_requests(self, provider: str):
        """Remove request timestamps older than 24 hours"""
        now = time.time()
        history = self.request_history[provider]
        
        # Remove requests older than 24 hours
        while history and (now - history[0]) > 86400:  # 24 hours in seconds
            history.popleft()
    
    def _can_make_request(self, provider: str) -> bool:
        """Check if provider can handle a new request"""
        if provider not in self.providers:
            return False
        
        # Check if provider is in cooldown
        if provider in self.cooldown_until:
            if datetime.now() < self.cooldown_until[provider]:
                return False
            else:
                del self.cooldown_until[provider]
                self.provider_status[provider] = ProviderStatus.ACTIVE
        
        # Check provider status
        if self.provider_status[provider] not in [ProviderStatus.ACTIVE, ProviderStatus.RATE_LIMITED]:
            return False
        
        config = self.providers[provider]
        history = self.request_history[provider]
        now = time.time()
        
        # Clean old requests
        self._clean_old_requests(provider)
        
        # Check requests per minute
        recent_requests = sum(1 for timestamp in history if (now - timestamp) < 60)
        if recent_requests >= config.requests_per_minute:
            self.provider_status[provider] = ProviderStatus.RATE_LIMITED
            return False
        
        # Check requests per day
        if len(history) >= config.requests_per_day:
            self.provider_status[provider] = ProviderStatus.QUOTA_EXCEEDED
            return False
        
        return True
    
    def _record_request(self, provider: str, success: bool = True):
        """Record a request attempt"""
        now = time.time()
        self.request_history[provider].append(now)
        
        if success:
            # Reset error count and backoff on success
            self.error_counts[provider] = 0
            self.backoff_managers[provider].reset()
            if self.provider_status[provider] == ProviderStatus.RATE_LIMITED:
                self.provider_status[provider] = ProviderStatus.ACTIVE
        else:
            # Increment error count
            self.error_counts[provider] += 1
    
    def _handle_rate_limit_error(self, provider: str, error: Exception, retry_after: Optional[int] = None):
        """Handle rate limit errors with appropriate cooldown"""
        error_str = str(error).lower()
        
        # Determine cooldown time
        if retry_after:
            cooldown_seconds = retry_after
        elif "429" in error_str or "rate limit" in error_str:
            cooldown_seconds = 60 * self.providers[provider].cooldown_minutes
        elif "quota" in error_str or "exceeded" in error_str:
            cooldown_seconds = 60 * 15  # 15 minutes for quota errors
        else:
            cooldown_seconds = 60 * 5   # 5 minutes for other errors
        
        # Set cooldown
        self.cooldown_until[provider] = datetime.now() + timedelta(seconds=cooldown_seconds)
        self.provider_status[provider] = ProviderStatus.RATE_LIMITED
        
        logger.warning(f"Provider {provider} rate limited. Cooldown until {self.cooldown_until[provider]}")
    
    def get_available_providers(self, require_vision: bool = False) -> List[str]:
        """Get list of available providers sorted by priority"""
        available = []
        
        for provider_name, config in self.providers.items():
            if self._can_make_request(provider_name):
                # For now, assume all providers support the requested features
                # In a real implementation, you'd check provider capabilities
                available.append(provider_name)
        
        # Sort by priority (lower number = higher priority)
        available.sort(key=lambda p: self.providers[p].priority)
        return available
    
    async def execute_with_fallback(
        self,
        method_name: str,
        providers: List[str],
        request_func: Callable,
        cache_key_params: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        """
        Execute a request with automatic fallback across providers
        
        Args:
            method_name: Name of the method for caching
            providers: List of providers to try in order
            request_func: Async function that takes (provider_name, **kwargs) and returns result
            cache_key_params: Parameters to use for cache key generation
            **kwargs: Arguments to pass to request_func
        """
        cache_params = cache_key_params or {}
        
        # Try to get from cache first
        if self.cache_enabled and cache_params:
            for provider in providers:
                cached_result = self.cache.get(provider, method_name, **cache_params)
                if cached_result is not None:
                    return cached_result
        
        last_error = None
        
        for provider in providers:
            if not self._can_make_request(provider):
                logger.debug(f"Provider {provider} not available, skipping")
                continue
            
            try:
                logger.info(f"Attempting request with provider: {provider}")
                
                # Apply backoff delay if needed
                backoff = self.backoff_managers[provider]
                if backoff.attempt > 0:
                    delay = backoff.get_delay()
                    logger.info(f"Applying backoff delay: {delay:.2f}s for {provider}")
                    await asyncio.sleep(delay)
                
                # Execute the request
                result = await request_func(provider, **kwargs)
                
                # Record successful request
                self._record_request(provider, success=True)
                
                # Cache the result
                if self.cache_enabled and cache_params:
                    self.cache.set(provider, method_name, result, **cache_params)
                
                logger.info(f"Request successful with provider: {provider}")
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Record failed request
                self._record_request(provider, success=False)
                
                # Check if it's a rate limit error
                rate_limit_indicators = ["429", "quota", "rate limit", "exceeded", "too many requests"]
                if any(indicator in error_str for indicator in rate_limit_indicators):
                    # Extract retry-after if available
                    retry_after = None
                    if hasattr(e, 'retry_after'):
                        retry_after = e.retry_after
                    
                    self._handle_rate_limit_error(provider, e, retry_after)
                    logger.warning(f"Rate limit error with {provider}: {e}")
                    continue
                else:
                    # Other errors - still try next provider
                    logger.error(f"Error with {provider}: {e}")
                    continue
        
        # All providers failed
        if last_error:
            raise RateLimitError(
                f"All providers failed. Last error: {last_error}",
                provider="all",
                retry_after=300  # 5 minutes
            )
        else:
            raise RateLimitError(
                "No available providers (all rate limited or in cooldown)",
                provider="all",
                retry_after=60  # 1 minute
            )
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get detailed statistics for all providers"""
        stats = {}
        
        for provider_name, config in self.providers.items():
            history = self.request_history[provider_name]
            now = time.time()
            
            # Calculate request counts
            requests_last_minute = sum(1 for timestamp in history if (now - timestamp) < 60)
            requests_last_hour = sum(1 for timestamp in history if (now - timestamp) < 3600)
            requests_today = len(history)
            
            # Get cooldown info
            cooldown_until = None
            if provider_name in self.cooldown_until:
                cooldown_until = self.cooldown_until[provider_name].isoformat()
            
            stats[provider_name] = {
                'status': self.provider_status[provider_name].value,
                'priority': config.priority,
                'requests_per_minute_limit': config.requests_per_minute,
                'requests_per_day_limit': config.requests_per_day,
                'requests_last_minute': requests_last_minute,
                'requests_last_hour': requests_last_hour,
                'requests_today': requests_today,
                'error_count': self.error_counts[provider_name],
                'backoff_attempt': self.backoff_managers[provider_name].attempt,
                'cooldown_until': cooldown_until,
                'can_make_request': self._can_make_request(provider_name)
            }
        
        return stats
    
    def reset_provider(self, provider: str):
        """Reset a provider's state (for testing or manual recovery)"""
        if provider in self.providers:
            self.provider_status[provider] = ProviderStatus.ACTIVE
            self.error_counts[provider] = 0
            self.backoff_managers[provider].reset()
            if provider in self.cooldown_until:
                del self.cooldown_until[provider]
            logger.info(f"Reset provider: {provider}")
    
    def reset_all_providers(self):
        """Reset all providers' states"""
        for provider in self.providers:
            self.reset_provider(provider)
        logger.info("Reset all providers")