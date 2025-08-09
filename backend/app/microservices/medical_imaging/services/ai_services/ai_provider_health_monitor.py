"""
AI Provider Health Monitoring System
Monitors health of AI providers and manages failover
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class AIProviderHealthMonitor:
    """Monitor health of AI providers and manage failover"""
    
    def __init__(self):
        self.providers: Dict[str, Any] = {}
        self.health_status: Dict[str, str] = {}
        self.last_check: Dict[str, Optional[datetime]] = {}
        self.check_interval = 300  # 5 minutes
        self.failure_counts: Dict[str, int] = {}
        self.max_failures = 3
        
    async def register_provider(self, name: str, provider: Any):
        """Register a provider for health monitoring"""
        self.providers[name] = provider
        self.health_status[name] = "unknown"
        self.last_check[name] = None
        self.failure_counts[name] = 0
        logger.info(f"Registered provider: {name}")
        
    async def check_provider_health(self, name: str) -> bool:
        """Check if provider is healthy"""
        provider = self.providers.get(name)
        if not provider:
            logger.warning(f"Provider {name} not found")
            return False
            
        try:
            # Provider-specific health check
            if hasattr(provider, 'health_check'):
                result = await provider.health_check()
            else:
                # Generic test - try to generate something small
                logger.debug(f"Running generic health check for {name}")
                
                # Create minimal test request with a valid 1x1 white pixel PNG
                # This is a base64 encoded 1x1 white pixel PNG image
                test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                # Create proper test data structure
                test_data = {
                    "image_data": test_image_base64,
                    "image_type": "test_health_check",
                    "patient_info": {"test": True, "name": "Health Check"}
                }
                
                # Try to call the provider's main method with timeout
                async with asyncio.timeout(10):  # 10 second timeout
                    if hasattr(provider, 'generate_image_analysis'):
                        # For providers expecting different argument format
                        result = await provider.generate_image_analysis(
                            image_data=test_image_base64,  # Pass base64 string directly
                            image_type=test_data["image_type"],
                            patient_info=test_data["patient_info"]
                        )
                    elif hasattr(provider, '_call_api'):
                        # For unified providers, test with simple prompt
                        result = await provider._call_api(
                            prompt="Health check test",
                            image_data=test_image_base64,
                            model=None  # Will use default model
                        )
                    elif hasattr(provider, 'generate'):
                        result = await provider.generate(**test_data)
                    else:
                        logger.warning(f"Provider {name} has no testable method")
                        return False
            
            # Success
            self.health_status[name] = "healthy"
            self.last_check[name] = datetime.utcnow()
            self.failure_counts[name] = 0
            logger.info(f"Health check passed for {name}")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Health check timeout for {name}")
            self._record_failure(name)
            return False
            
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            self._record_failure(name)
            return False
    
    def _record_failure(self, name: str):
        """Record a failure for a provider"""
        self.failure_counts[name] = self.failure_counts.get(name, 0) + 1
        
        if self.failure_counts[name] >= self.max_failures:
            self.health_status[name] = "unhealthy"
            logger.warning(f"Provider {name} marked unhealthy after {self.max_failures} failures")
        else:
            self.health_status[name] = "degraded"
            
        self.last_check[name] = datetime.utcnow()
    
    def _is_check_stale(self, name: str) -> bool:
        """Check if health check is stale and needs refresh"""
        last = self.last_check.get(name)
        if not last:
            return True
            
        age = (datetime.utcnow() - last).seconds
        return age > self.check_interval
        
    async def get_healthy_provider(self, preferred_order: List[str]) -> Optional[Any]:
        """Get first healthy provider from preference list"""
        for name in preferred_order:
            # Skip if provider not registered
            if name not in self.providers:
                continue
                
            # Check if health check is stale
            if self._is_check_stale(name):
                await self.check_provider_health(name)
                
            if self.health_status.get(name) == "healthy":
                logger.info(f"Selected healthy provider: {name}")
                return self.providers[name]
            elif self.health_status.get(name) == "degraded":
                # Try degraded providers if no healthy ones
                logger.warning(f"Using degraded provider: {name}")
                return self.providers[name]
                
        logger.error("No healthy providers available")
        return None
    
    async def start_background_monitoring(self):
        """Start background health monitoring task"""
        while True:
            try:
                # Check all providers
                for name in self.providers:
                    if self._is_check_stale(name):
                        await self.check_provider_health(name)
                        
                # Wait before next round
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(60)
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get current status of all providers"""
        report = {}
        for name in self.providers:
            report[name] = {
                "status": self.health_status.get(name, "unknown"),
                "last_check": self.last_check.get(name).isoformat() if self.last_check.get(name) else None,
                "failure_count": self.failure_counts.get(name, 0),
                "available": self.health_status.get(name) in ["healthy", "degraded"]
            }
        return report