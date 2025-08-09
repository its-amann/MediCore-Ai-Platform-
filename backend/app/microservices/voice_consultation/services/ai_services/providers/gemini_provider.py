"""
Google Gemini AI Provider
Handles all Gemini models with vision capabilities
"""

import os
import logging
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from PIL import Image
import io
import base64

from .base_provider import BaseAIProvider, ModelConfig, ProviderCapabilities

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider with vision capabilities"""
    
    # Available Gemini models
    MODELS = [
        ModelConfig(
            model_id="gemini-1.5-pro",
            context_length=1048576,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value, 
                         ProviderCapabilities.MEDICAL.value, ProviderCapabilities.CITATIONS.value],
            rate_limit_daily=1500,
            rate_limit_per_minute=15,
            priority=1,
            cost_category="standard",
            supports_vision=True
        ),
        ModelConfig(
            model_id="gemini-1.5-flash",
            context_length=1048576,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value,
                         ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=1500,
            rate_limit_per_minute=60,
            priority=2,
            cost_category="lite",
            supports_vision=True
        ),
        ModelConfig(
            model_id="gemini-2.0-flash-exp",
            context_length=1048576,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value,
                         ProviderCapabilities.MEDICAL.value],
            rate_limit_daily=50,
            rate_limit_per_minute=20,
            priority=3,
            cost_category="free",
            supports_vision=True
        ),
        ModelConfig(
            model_id="gemini-1.5-pro-002",
            context_length=2097152,
            capabilities=[ProviderCapabilities.VISION.value, ProviderCapabilities.REASONING.value,
                         ProviderCapabilities.MEDICAL.value, ProviderCapabilities.CITATIONS.value],
            rate_limit_daily=1000,
            rate_limit_per_minute=10,
            priority=4,
            cost_category="premium",
            supports_vision=True
        )
    ]
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        """Initialize Gemini provider with multiple API keys"""
        super().__init__("Gemini")
        
        # Load API keys
        if api_keys:
            self.api_keys = api_keys
        else:
            # Try to load medical imaging specific API keys first
            self.api_keys = []
            
            # Load medical imaging specific keys
            med_key_1 = os.getenv("MEDICAL_IMAGING_GEMINI_1")
            med_key_2 = os.getenv("MEDICAL_IMAGING_GEMINI_2")
            
            if med_key_1:
                self.api_keys.append(med_key_1)
            if med_key_2:
                self.api_keys.append(med_key_2)
            
            # If no medical imaging keys, fallback to general keys
            if not self.api_keys:
                for i in range(1, 4):  # Try up to 3 keys
                    key = os.getenv(f"GEMINI_API_KEY_{i}") or os.getenv(f"GEMINI_API_KEY") if i == 1 else None
                    if key:
                        self.api_keys.append(key)
        
        if not self.api_keys:
            raise ValueError("No Gemini API keys found")
        
        self.current_key_index = 0
        
        # Configure Gemini
        genai.configure(api_key=self.api_keys[0])
        
        # Initialize models and keep track of configs
        self.models = {}
        self.model_configs = {}  # Keep track of model configs for rate limit tracking
        for model_config in self.MODELS:
            try:
                self.models[model_config.model_id] = genai.GenerativeModel(model_config.model_id)
                self.model_configs[model_config.model_id] = model_config
                logger.info(f"Initialized Gemini model: {model_config.model_id}")
            except Exception as e:
                logger.warning(f"Could not initialize {model_config.model_id}: {e}")
    
    def get_available_models(self, require_vision: bool = False) -> List[ModelConfig]:
        """Get available Gemini models"""
        available = []
        for model_id, model_config in self.model_configs.items():
            # Check if model requires vision and has it
            if require_vision and not model_config.supports_vision:
                continue
            
            # Check if model is initialized
            if model_id not in self.models:
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
        """Make API call to Gemini"""
        
        model_id = model or "gemini-1.5-flash"
        
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not available")
        
        try:
            gemini_model = self.models[model_id]
            
            # Prepare content
            content = []
            
            # Add image if provided
            if image_data:
                try:
                    # Decode base64 image
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))
                    content.append(image)
                except Exception as e:
                    logger.warning(f"Could not process image: {e}")
            
            # Add text prompt
            content.append(prompt)
            
            # Generate response
            response = gemini_model.generate_content(
                content,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get("temperature", 0.3),
                    max_output_tokens=kwargs.get("max_tokens", 4096),
                    top_p=kwargs.get("top_p", 0.95),
                    top_k=kwargs.get("top_k", 40)
                )
            )
            
            if response and response.text:
                # Update successful usage
                if model_id in self.model_configs:
                    self.model_configs[model_id].update_usage(success=True)
                return response.text
            else:
                logger.warning(f"Empty response from Gemini model {model_id}")
                return None
                
        except Exception as e:
            # Handle rate limit errors
            if "429" in str(e) or "quota" in str(e).lower() or "exceeded" in str(e).lower():
                logger.warning(f"Rate limit hit for Gemini {model_id}")
                
                # Mark model as rate limited
                if model_id in self.model_configs:
                    # Check if it's a daily or minute limit
                    if "daily" in str(e).lower() or "day" in str(e).lower():
                        self.model_configs[model_id].mark_rate_limited(24)  # 24 hour reset
                    else:
                        self.model_configs[model_id].mark_rate_limited(0.0167)  # 1 minute reset
                
                # Try next API key
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                if self.current_key_index != 0:  # If we haven't cycled through all keys
                    genai.configure(api_key=self.api_keys[self.current_key_index])
                    logger.info(f"Switching to API key {self.current_key_index + 1}")
                    # Retry with new key
                    return await self._call_api(prompt, image_data, model, **kwargs)
                else:
                    logger.error(f"All API keys exhausted for Gemini")
            
            logger.error(f"Gemini API error: {e}")
            raise