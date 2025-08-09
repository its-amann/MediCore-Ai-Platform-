"""
Groq AI Provider
Fast inference with Llama and Mixtral models
"""

import os
import logging
from typing import Dict, List, Optional, Any
from groq import Groq

from .base_provider import BaseAIProvider, ModelConfig, ProviderCapabilities

logger = logging.getLogger(__name__)


class GroqProvider(BaseAIProvider):
    """Groq AI provider for fast inference"""
    
    # Available Groq models
    MODELS = [
        # Vision-capable models
        ModelConfig(
            model_id="meta-llama/llama-4-scout-17b-16e-instruct",
            context_length=16384,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value,
                         ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=1,
            cost_category="free",
            supports_vision=True
        ),
        ModelConfig(
            model_id="meta-llama/llama-4-maverick-17b-128e-instruct",
            context_length=131072,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value,
                         ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=2,
            cost_category="free",
            supports_vision=True
        ),
        ModelConfig(
            model_id="llama-3.2-90b-vision-preview",
            context_length=131072,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value, 
                         ProviderCapabilities.MEDICAL.value, ProviderCapabilities.ANALYSIS.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=3,
            cost_category="free",
            supports_vision=True  # Updated to support vision
        ),
        ModelConfig(
            model_id="deepseek-r1-distill-llama-70b",
            context_length=32768,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value,
                         ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=4,
            cost_category="free",
            supports_vision=True
        ),
        ModelConfig(
            model_id="meta-llama/llama-prompt-guard-2-86m",
            context_length=4096,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=5,
            cost_category="free",
            supports_vision=True
        ),
        ModelConfig(
            model_id="llama-3.2-90b-text-preview",
            context_length=131072,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=6,  # Lower priority for non-vision models
            cost_category="free",
            supports_vision=False
        ),
        # Note: mixtral-8x7b-32768 has been decommissioned
        # Removed deprecated model
        ModelConfig(
            model_id="llama3-70b-8192",
            context_length=8192,
            capabilities=[ProviderCapabilities.REASONING.value, ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=8,
            cost_category="free",
            supports_vision=False
        ),
        ModelConfig(
            model_id="llama3-8b-8192",
            context_length=8192,
            capabilities=[ProviderCapabilities.REASONING.value],
            rate_limit_daily=14400,
            rate_limit_per_minute=30,
            priority=9,
            cost_category="free",
            supports_vision=False
        )
    ]
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        """Initialize Groq provider with multiple API keys"""
        super().__init__("Groq")
        
        # Load API keys
        if api_keys:
            self.api_keys = api_keys
        else:
            # Try to load medical imaging specific API keys first
            self.api_keys = []
            
            # Load medical imaging specific keys
            med_key_1 = os.getenv("MEDICAL_IMAGING_GROQ_1")
            med_key_2 = os.getenv("MEDICAL_IMAGING_GROQ_2")
            
            if med_key_1:
                self.api_keys.append(med_key_1)
            if med_key_2:
                self.api_keys.append(med_key_2)
            
            # If no medical imaging keys, fallback to general keys
            if not self.api_keys:
                for i in range(1, 4):  # Try up to 3 keys
                    key = os.getenv(f"GROQ_API_KEY_{i}") or os.getenv(f"GROQ_API_KEY") if i == 1 else None
                    if key:
                        self.api_keys.append(key)
        
        if not self.api_keys:
            raise ValueError("No Groq API keys found")
        
        self.current_key_index = 0
        
        # Initialize Groq clients for each key
        self.clients = [Groq(api_key=key) for key in self.api_keys]
        self.current_client = self.clients[0]
        
        # Initialize model configs for rate limit tracking
        self.model_configs = {model.model_id: model for model in self.MODELS}
    
    def get_available_models(self, require_vision: bool = False) -> List[ModelConfig]:
        """Get available Groq models"""
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
        """Make API call to Groq"""
        
        model_id = model or "llama-3.2-90b-vision-preview"
        
        try:
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert radiologist analyzing medical images and creating detailed reports."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Add image if provided and model supports it
            if image_data and model_id == "llama-3.2-90b-vision-preview":
                # For vision models, add image to the user message
                messages[-1]["content"] = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            
            # Make API call
            response = self.current_client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=kwargs.get("temperature", 0.3),
                max_tokens=kwargs.get("max_tokens", 4096),
                top_p=kwargs.get("top_p", 0.95),
                stream=False
            )
            
            if response and response.choices and response.choices[0].message:
                # Update successful usage
                if model_id in self.model_configs:
                    self.model_configs[model_id].update_usage(success=True)
                return response.choices[0].message.content
            else:
                logger.warning(f"Empty response from Groq model {model_id}")
                return None
                
        except Exception as e:
            # Handle rate limit errors
            if "429" in str(e) or "rate" in str(e).lower():
                logger.warning(f"Rate limit hit for Groq {model_id}")
                
                # Mark model as rate limited
                if model_id in self.model_configs:
                    # Check if it's a daily or minute limit
                    if "daily" in str(e).lower() or "day" in str(e).lower():
                        self.model_configs[model_id].mark_rate_limited(24)  # 24 hour reset
                    else:
                        self.model_configs[model_id].mark_rate_limited(0.0167)  # 1 minute reset
                
                # Try next API key
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                self.current_client = self.clients[self.current_key_index]
                
                if self.current_key_index != 0:  # If we haven't cycled through all keys
                    logger.info(f"Switching to API key {self.current_key_index + 1}")
                    # Retry with new client
                    return await self._call_api(prompt, image_data, model, **kwargs)
                else:
                    logger.error(f"All API keys exhausted for Groq")
            
            logger.error(f"Groq API error: {e}")
            raise