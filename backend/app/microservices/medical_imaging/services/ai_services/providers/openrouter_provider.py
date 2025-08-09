"""
OpenRouter AI Provider
Access to 30+ free models with intelligent fallback
"""

import os
import logging
from typing import Dict, List, Optional, Any
import httpx
import asyncio

from .base_provider import BaseAIProvider, ModelConfig, ProviderCapabilities, ProviderStatus

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseAIProvider):
    """OpenRouter AI provider with extensive free model access"""
    
    # Comprehensive list of free models
    MODELS = [
        # Vision-capable models
        ModelConfig(
            model_id="google/gemini-2.0-flash-exp:free",
            context_length=1048576,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=1,
            cost_category="free",
            supports_vision=True
        ),
        ModelConfig(
            model_id="meta-llama/llama-3.2-11b-vision-instruct:free",
            context_length=131072,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=2,
            cost_category="free",
            supports_vision=True
        ),
        ModelConfig(
            model_id="moonshotai/kimi-vl-a3b-thinking:free",
            context_length=200000,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=3,
            cost_category="free",
            supports_vision=True
        ),
        
        # High-performance reasoning models
        ModelConfig(
            model_id="deepseek/deepseek-r1:free",
            context_length=64000,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value, ProviderCapabilities.ANALYSIS.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=4,
            cost_category="free"
        ),
        ModelConfig(
            model_id="deepseek/deepseek-r1-0528:free",
            context_length=64000,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=5,
            cost_category="free"
        ),
        ModelConfig(
            model_id="deepseek/deepseek-r1-0528-qwen3-8b:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=6,
            cost_category="free"
        ),
        ModelConfig(
            model_id="deepseek/deepseek-chat-v3-0324:free",
            context_length=64000,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=7,
            cost_category="free"
        ),
        ModelConfig(
            model_id="deepseek/deepseek-r1-distill-qwen-14b:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=8,
            cost_category="free"
        ),
        
        # Advanced models
        ModelConfig(
            model_id="nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            context_length=131072,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value, ProviderCapabilities.ANALYSIS.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=9,
            cost_category="free"
        ),
        ModelConfig(
            model_id="google/gemini-2.5-pro-exp-03-25",
            context_length=1048576,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value, ProviderCapabilities.CITATIONS.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=10,
            cost_category="free"
        ),
        
        # Kimi models
        ModelConfig(
            model_id="moonshotai/kimi-k2:free",
            context_length=200000,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value, ProviderCapabilities.ANALYSIS.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=11,
            cost_category="free"
        ),
        ModelConfig(
            model_id="moonshotai/kimi-dev-72b:free",
            context_length=200000,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=12,
            cost_category="free"
        ),
        
        # Qwen models
        ModelConfig(
            model_id="qwen/qwen3-coder:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.CODING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=13,
            cost_category="free"
        ),
        ModelConfig(
            model_id="qwen/qwen3-30b-a3b:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=14,
            cost_category="free"
        ),
        ModelConfig(
            model_id="qwen/qwen3-235b-a22b:free",
            context_length=131072,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=15,
            cost_category="free"
        ),
        ModelConfig(
            model_id="qwen/qwq-32b:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.ANALYSIS.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=16,
            cost_category="free"
        ),
        ModelConfig(
            model_id="qwen/qwen-2.5-72b-instruct:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=17,
            cost_category="free"
        ),
        
        # Mistral models
        ModelConfig(
            model_id="mistralai/mistral-small-3.2-24b-instruct:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=18,
            cost_category="free"
        ),
        ModelConfig(
            model_id="mistralai/mistral-small-3.1-24b-instruct:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=19,
            cost_category="free"
        ),
        ModelConfig(
            model_id="mistralai/devstral-small-2505:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.CODING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=20,
            cost_category="free"
        ),
        
        # Cognitive models
        ModelConfig(
            model_id="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=21,
            cost_category="free"
        ),
        ModelConfig(
            model_id="cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=22,
            cost_category="free"
        ),
        
        # Other specialized models
        ModelConfig(
            model_id="z-ai/glm-4.5-air:free",
            context_length=128000,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=23,
            cost_category="free"
        ),
        ModelConfig(
            model_id="openrouter/horizon-beta",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=24,
            cost_category="free"
        ),
        ModelConfig(
            model_id="openrouter/horizon-alpha",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=25,
            cost_category="free"
        ),
        ModelConfig(
            model_id="tencent/hunyuan-a13b-instruct:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=26,
            cost_category="free"
        ),
        ModelConfig(
            model_id="tngtech/deepseek-r1t2-chimera:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=27,
            cost_category="free"
        ),
        ModelConfig(
            model_id="tngtech/deepseek-r1t-chimera:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=28,
            cost_category="free"
        ),
        ModelConfig(
            model_id="microsoft/mai-ds-r1:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=29,
            cost_category="free"
        ),
        ModelConfig(
            model_id="shisa-ai/shisa-v2-llama3.3-70b:free",
            context_length=131072,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=30,
            cost_category="free"
        ),
        ModelConfig(
            model_id="agentica-org/deepcoder-14b-preview:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.CODING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=31,
            cost_category="free"
        ),
        ModelConfig(
            model_id="sarvamai/sarvam-m:free",
            context_length=32768,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=32,
            cost_category="free"
        ),
        ModelConfig(
            model_id="google/gemma-3-27b-it:free",
            context_length=8192,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=33,
            cost_category="free"
        ),
        ModelConfig(
            model_id="nousresearch/deephermes-3-llama-3-8b-preview:free",
            context_length=8192,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=34,
            cost_category="free"
        )
    ]
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        """Initialize OpenRouter provider with multiple API keys"""
        super().__init__("OpenRouter")
        
        # Load API keys
        if api_keys:
            self.api_keys = api_keys
        else:
            # Try to load medical imaging specific API keys first
            self.api_keys = []
            
            # Load medical imaging specific keys
            med_key_1 = os.getenv("MEDICAL_IMAGING_OPENROUTE_1")
            med_key_2 = os.getenv("MEDICAL_IMAGING_OPENROUTE_2")
            med_key_3 = os.getenv("MEDICAL_IMAGING_OPENROUTE_3")
            
            if med_key_1 and med_key_1 != "your-openrouter-api-key":
                self.api_keys.append(med_key_1)
            if med_key_2 and med_key_2 != "your-openrouter-api-key":
                self.api_keys.append(med_key_2)
            if med_key_3 and med_key_3 != "your-openrouter-api-key":
                self.api_keys.append(med_key_3)
            
            # If no medical imaging keys, fallback to general keys
            if not self.api_keys:
                for i in range(1, 4):  # Try up to 3 keys
                    key = os.getenv(f"OPENROUTER_API_KEY_{i}") or os.getenv(f"OPENROUTER_API_KEY") if i == 1 else None
                    if key and key != "your-openrouter-api-key":
                        self.api_keys.append(key)
        
        if not self.api_keys or all(key in ["test-key", "your-openrouter-api-key", ""] for key in self.api_keys):
            logger.warning("No valid OpenRouter API keys found - provider disabled")
            self.status = ProviderStatus.DISABLED
            return
        
        self.current_key_index = 0
        
        # Initialize model configs for rate limit tracking
        self.model_configs = {model.model_id: model for model in self.MODELS}
        
        logger.info(f"OpenRouter provider initialized with {len(self.api_keys)} API keys and {len(self.MODELS)} models")
    
    def get_available_models(self, require_vision: bool = False) -> List[ModelConfig]:
        """Get available OpenRouter models"""
        if not self.api_keys or self.status == ProviderStatus.DISABLED:
            return []
        
        available = []
        for model_id, model_config in self.model_configs.items():
            # Check if model requires vision and has it
            if require_vision and not model_config.supports_vision:
                continue
            
            # Check if model is available (not rate limited)
            if model_config.is_available():
                available.append(model_config)
        
        # Sort by priority
        available.sort(key=lambda x: x.priority)
        return available
    
    async def _call_api(
        self,
        prompt: str,
        image_data: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Make API call to OpenRouter"""
        
        if not self.api_keys:
            raise ValueError("No OpenRouter API keys configured")
        
        model_id = model or "google/gemini-2.0-flash-exp:free"
        api_key = self.api_keys[self.current_key_index]
        
        # Prepare messages
        messages = [{"role": "user", "content": prompt}]
        
        # Add image if provided and model supports it
        if image_data:
            # Check if model supports vision
            model_config = next((m for m in self.MODELS if m.model_id == model_id), None)
            if model_config and model_config.supports_vision:
                messages[0]["content"] = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
        
        timeout_config = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "Medical AI Assistant"
                    },
                    json={
                        "model": model_id,
                        "messages": messages,
                        "temperature": kwargs.get("temperature", 0.3),
                        "max_tokens": kwargs.get("max_tokens", 4000),
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Update successful usage
                    if model_id in self.model_configs:
                        self.model_configs[model_id].update_usage(success=True)
                    return result["choices"][0]["message"]["content"]
                
                elif response.status_code == 429:
                    # Rate limit - try next key
                    logger.warning(f"Rate limit hit for OpenRouter key {self.current_key_index} with model {model_id}")
                    
                    # Mark model as rate limited
                    if model_id in self.model_configs:
                        # Parse the response to check if it's a daily or minute limit
                        try:
                            error_data = response.json()
                            error_msg = str(error_data.get('error', {}).get('message', ''))
                            if "daily" in error_msg.lower() or "day" in error_msg.lower():
                                self.model_configs[model_id].mark_rate_limited(24)  # 24 hour reset
                            else:
                                self.model_configs[model_id].mark_rate_limited(0.0167)  # 1 minute reset
                        except:
                            # Default to 1 minute if we can't parse
                            self.model_configs[model_id].mark_rate_limited(0.0167)
                    
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    if self.current_key_index != 0:
                        logger.info(f"Switching to API key {self.current_key_index + 1}")
                        return await self._call_api(prompt, image_data, model, **kwargs)
                    else:
                        logger.error(f"All API keys exhausted for OpenRouter")
                    return None
                
                elif response.status_code == 401:
                    logger.error(f"OpenRouter authentication failed - invalid API key")
                    self.status = ProviderStatus.DISABLED
                    return None
                
                else:
                    logger.error(f"OpenRouter API error: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"OpenRouter API error: {e}")
                raise