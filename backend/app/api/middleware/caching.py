"""
Caching Middleware for Performance Optimization
Agent 8: Performance & Optimization Specialist

Implements in-memory and Redis caching for API responses
"""

import json
import hashlib
import time
from typing import Any, Dict, Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class CachingMiddleware(BaseHTTPMiddleware):
    """Intelligent caching middleware for API responses"""
    
    def __init__(
        self, 
        app: ASGIApp,
        cache_ttl: int = 300,  # 5 minutes default
        max_cache_size: int = 1000,
        enabled_paths: list = None,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        self.cache_store: Dict[str, Dict[str, Any]] = {}
        
        # Default cacheable paths
        self.enabled_paths = enabled_paths or [
            '/api/v1/doctors',
            '/health',
            '/api/v1/cases',
            '/api/v1/rooms'
        ]
        
        # Paths to exclude from caching
        self.exclude_paths = exclude_paths or [
            '/api/v1/auth/login',
            '/api/v1/auth/register',
            '/api/v1/media/upload',
            '/ws/'
        ]
        
        logger.info(f"Caching middleware initialized with TTL: {cache_ttl}s")
    
    def _should_cache(self, request: Request) -> bool:
        """Determine if request should be cached"""
        path = str(request.url.path)
        method = request.method
        
        # Only cache GET requests
        if method != "GET":
            return False
        
        # Check exclusions
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        # Check if path is in enabled paths
        for enabled_path in self.enabled_paths:
            if path.startswith(enabled_path):
                return True
        
        return False
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate unique cache key for request"""
        # Include path, query params, and relevant headers
        cache_data = {
            'path': str(request.url.path),
            'query': str(request.query_params),
            'method': request.method,
            # Include auth header hash for user-specific caching
            'auth_hash': hashlib.md5(
                request.headers.get('authorization', '').encode()
            ).hexdigest()[:8]
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry['timestamp'] < self.cache_ttl
    
    def _cleanup_cache(self):
        """Remove expired entries and maintain size limit"""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self.cache_store.items()
            if current_time - entry['timestamp'] >= self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.cache_store[key]
        
        # If still over limit, remove oldest entries
        if len(self.cache_store) > self.max_cache_size:
            sorted_entries = sorted(
                self.cache_store.items(),
                key=lambda x: x[1]['timestamp']
            )
            
            # Remove oldest entries
            entries_to_remove = len(self.cache_store) - self.max_cache_size
            for i in range(entries_to_remove):
                key = sorted_entries[i][0]
                del self.cache_store[key]
    
    def _cache_response(self, cache_key: str, response_body: bytes, status_code: int, headers: dict):
        """Store response in cache"""
        self.cache_store[cache_key] = {
            'timestamp': time.time(),
            'body': response_body,
            'status_code': status_code,
            'headers': dict(headers),
            'content_type': headers.get('content-type', 'application/json')
        }
        
        # Cleanup if needed
        if len(self.cache_store) > self.max_cache_size:
            self._cleanup_cache()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if request should be cached
        if not self._should_cache(request):
            return await call_next(request)
        
        cache_key = self._generate_cache_key(request)
        
        # Check if we have a valid cached response
        if cache_key in self.cache_store:
            cache_entry = self.cache_store[cache_key]
            
            if self._is_cache_valid(cache_entry):
                logger.debug(f"Cache HIT for {request.url.path}")
                
                # Create response from cache
                response = Response(
                    content=cache_entry['body'],
                    status_code=cache_entry['status_code'],
                    headers=cache_entry['headers']
                )
                
                # Add cache headers
                response.headers["X-Cache"] = "HIT"
                response.headers["X-Cache-Age"] = str(
                    int(time.time() - cache_entry['timestamp'])
                )
                
                return response
        
        # Cache miss - execute request
        logger.debug(f"Cache MISS for {request.url.path}")
        response = await call_next(request)
        
        # Cache successful responses
        if 200 <= response.status_code < 300:
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Cache the response
            self._cache_response(
                cache_key, 
                response_body, 
                response.status_code, 
                response.headers
            )
            
            # Create new response with cached body
            cached_response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
            # Add cache headers
            cached_response.headers["X-Cache"] = "MISS"
            cached_response.headers["X-Cache-TTL"] = str(self.cache_ttl)
            
            return cached_response
        
        # Don't cache error responses
        response.headers["X-Cache"] = "SKIP"
        return response
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        valid_entries = sum(
            1 for entry in self.cache_store.values()
            if current_time - entry['timestamp'] < self.cache_ttl
        )
        
        return {
            "total_entries": len(self.cache_store),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache_store) - valid_entries,
            "cache_ttl": self.cache_ttl,
            "max_cache_size": self.max_cache_size,
            "enabled_paths": self.enabled_paths,
            "exclude_paths": self.exclude_paths
        }
    
    def clear_cache(self, pattern: str = None):
        """Clear cache entries, optionally by pattern"""
        if pattern:
            keys_to_remove = [
                key for key in self.cache_store.keys()
                if pattern in key
            ]
            for key in keys_to_remove:
                del self.cache_store[key]
            logger.info(f"Cleared {len(keys_to_remove)} cache entries matching '{pattern}'")
        else:
            self.cache_store.clear()
            logger.info("Cleared all cache entries")


# Redis-based caching middleware (for production)
class RedisCachingMiddleware(BaseHTTPMiddleware):
    """Redis-based caching middleware for production environments"""
    
    def __init__(
        self, 
        app: ASGIApp,
        redis_url: str = "redis://localhost:6379",
        cache_ttl: int = 300,
        key_prefix: str = "medical_api_cache:"
    ):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.key_prefix = key_prefix
        self.redis_client = None
        
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(redis_url)
            logger.info(f"Redis caching middleware initialized: {redis_url}")
        except ImportError:
            logger.warning("Redis not available, falling back to memory cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Fallback to regular response if Redis not available
        if not self.redis_client:
            return await call_next(request)
        
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        cache_key = f"{self.key_prefix}{request.url.path}:{hash(str(request.query_params))}"
        
        try:
            # Check Redis cache
            cached_response = await self.redis_client.get(cache_key)
            
            if cached_response:
                logger.debug(f"Redis cache HIT for {request.url.path}")
                cached_data = json.loads(cached_response)
                
                response = Response(
                    content=cached_data['body'],
                    status_code=cached_data['status_code'],
                    headers=cached_data['headers']
                )
                response.headers["X-Cache"] = "REDIS-HIT"
                return response
        
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
        
        # Execute request
        response = await call_next(request)
        
        # Cache successful responses
        if 200 <= response.status_code < 300:
            try:
                # Read response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Cache in Redis
                cache_data = {
                    'body': response_body.decode('utf-8'),
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                }
                
                await self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(cache_data)
                )
                
                # Return new response
                cached_response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                cached_response.headers["X-Cache"] = "REDIS-MISS"
                return cached_response
                
            except Exception as e:
                logger.warning(f"Failed to cache in Redis: {e}")
        
        return response