"""
Google Gemini Web Search Provider
Specialized provider for Gemini models with web search capabilities
Used exclusively by the literature research agent
"""

import os
import logging
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from datetime import datetime

from .base_provider import BaseAIProvider, ModelConfig, ProviderCapabilities

logger = logging.getLogger(__name__)


class GeminiWebSearchProvider(BaseAIProvider):
    """Gemini provider specialized for web search operations"""
    
    # Gemini models that support web search (2.5 and 2.0 models)
    WEB_SEARCH_MODELS = [
        ModelConfig(
            model_id="gemini-2.5-pro-latest",
            context_length=2097152,
            capabilities=[
                ProviderCapabilities.WEB_SEARCH.value,
                ProviderCapabilities.REASONING.value,
                ProviderCapabilities.MEDICAL.value,
                ProviderCapabilities.CITATIONS.value
            ],
            rate_limit_daily=50,
            rate_limit_per_minute=10,
            priority=1,
            cost_category="premium",
            supports_vision=False  # Web search doesn't need vision
        ),
        ModelConfig(
            model_id="gemini-2.5-flash-latest",
            context_length=1048576,
            capabilities=[
                ProviderCapabilities.WEB_SEARCH.value,
                ProviderCapabilities.REASONING.value,
                ProviderCapabilities.MEDICAL.value
            ],
            rate_limit_daily=100,
            rate_limit_per_minute=20,
            priority=2,
            cost_category="standard",
            supports_vision=False
        ),
        ModelConfig(
            model_id="gemini-2.0-flash-latest",
            context_length=1048576,
            capabilities=[
                ProviderCapabilities.WEB_SEARCH.value,
                ProviderCapabilities.REASONING.value,
                ProviderCapabilities.MEDICAL.value
            ],
            rate_limit_daily=50,
            rate_limit_per_minute=15,
            priority=3,
            cost_category="lite",
            supports_vision=False
        ),
        ModelConfig(
            model_id="gemini-2.5-pro-002",
            context_length=2097152,
            capabilities=[
                ProviderCapabilities.WEB_SEARCH.value,
                ProviderCapabilities.REASONING.value,
                ProviderCapabilities.MEDICAL.value,
                ProviderCapabilities.CITATIONS.value
            ],
            rate_limit_daily=50,
            rate_limit_per_minute=10,
            priority=4,
            cost_category="premium",
            supports_vision=False
        ),
        ModelConfig(
            model_id="gemini-2.0-flash-002",
            context_length=1048576,
            capabilities=[
                ProviderCapabilities.WEB_SEARCH.value,
                ProviderCapabilities.REASONING.value,
                ProviderCapabilities.MEDICAL.value
            ],
            rate_limit_daily=100,
            rate_limit_per_minute=20,
            priority=5,
            cost_category="standard",
            supports_vision=False
        ),
        ModelConfig(
            model_id="gemini-2.5-flash-002",
            context_length=1048576,
            capabilities=[
                ProviderCapabilities.WEB_SEARCH.value,
                ProviderCapabilities.REASONING.value,
                ProviderCapabilities.MEDICAL.value
            ],
            rate_limit_daily=100,
            rate_limit_per_minute=20,
            priority=6,
            cost_category="standard",
            supports_vision=False
        )
    ]
    
    def __init__(self):
        """Initialize Gemini Web Search provider with dedicated API key"""
        super().__init__("GeminiWebSearch")
        
        # Load the dedicated web search API key
        self.api_key = os.getenv("MEDICAL_IMAGING_WEB_SEARCH")
        
        if not self.api_key:
            logger.error("MEDICAL_IMAGING_WEB_SEARCH API key not found")
            raise ValueError("MEDICAL_IMAGING_WEB_SEARCH API key not configured")
        
        # Configure Gemini with the web search API key
        genai.configure(api_key=self.api_key)
        
        # Initialize models
        self.models = {}
        self.model_configs = {}
        
        for model_config in self.WEB_SEARCH_MODELS:
            try:
                # Create model with web search tools enabled
                generation_config = {
                    "temperature": 0.3,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
                
                # Configure tools for web search
                tools = [
                    {
                        "google_search": {
                            "dynamic_retrieval_config": {
                                "mode": "ungrounded",  # Allows web search
                                "dynamic_threshold": 0.3  # Sensitivity for triggering search
                            }
                        }
                    }
                ]
                
                self.models[model_config.model_id] = genai.GenerativeModel(
                    model_config.model_id,
                    generation_config=generation_config,
                    tools=tools
                )
                self.model_configs[model_config.model_id] = model_config
                logger.info(f"Initialized Gemini Web Search model: {model_config.model_id}")
                
            except Exception as e:
                logger.warning(f"Could not initialize {model_config.model_id}: {e}")
    
    def get_available_models(self, require_vision: bool = False) -> List[ModelConfig]:
        """Get available Gemini web search models"""
        # Web search models don't support vision, so return empty if vision required
        if require_vision:
            return []
        
        available = []
        for model_id, model_config in self.model_configs.items():
            # Check if model is initialized and available
            if model_id in self.models and model_config.is_available():
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
        """Make API call to Gemini with web search enabled"""
        
        # Get the best available model
        if not model:
            available_models = self.get_available_models()
            if not available_models:
                raise ValueError("No Gemini web search models available")
            model = available_models[0].model_id
        
        if model not in self.models:
            raise ValueError(f"Model {model} not available for web search")
        
        try:
            gemini_model = self.models[model]
            
            # Create web search prompt
            web_search_prompt = f"""
{prompt}

IMPORTANT: Use web search to find REAL, verifiable medical information. 
Search for:
- Recent medical research papers and case studies
- Clinical guidelines from reputable sources
- PubMed articles with actual PMIDs
- Medical journals like NEJM, JAMA, Lancet
- Authoritative medical websites

Return ONLY real, verifiable information with actual URLs and citations.
Do NOT generate fake references.
"""
            
            # Generate response with web search
            response = gemini_model.generate_content(web_search_prompt)
            
            if response and response.text:
                # Update successful usage
                if model in self.model_configs:
                    self.model_configs[model].update_usage(success=True)
                
                logger.info(f"Successfully generated web search response with {model}")
                return response.text
            else:
                logger.warning(f"Empty response from Gemini web search model {model}")
                return None
                
        except Exception as e:
            # Handle rate limit errors
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning(f"Rate limit hit for Gemini web search {model}")
                
                # Mark model as rate limited
                if model in self.model_configs:
                    if "daily" in str(e).lower():
                        self.model_configs[model].mark_rate_limited(24)
                    else:
                        self.model_configs[model].mark_rate_limited(0.0167)
                
                # Try another model
                available_models = self.get_available_models()
                if available_models and available_models[0].model_id != model:
                    logger.info(f"Trying alternative model: {available_models[0].model_id}")
                    return await self._call_api(prompt, image_data, available_models[0].model_id, **kwargs)
            
            logger.error(f"Gemini web search API error: {e}")
            raise
    
    async def search_medical_literature(
        self,
        findings: List[Dict[str, Any]],
        patient_info: Dict[str, Any]
    ) -> str:
        """
        Search medical literature using Gemini's web search capability
        
        Args:
            findings: List of medical findings from image analysis
            patient_info: Patient demographic and clinical information
            
        Returns:
            String containing formatted literature references
        """
        
        # Build a comprehensive search prompt
        age = patient_info.get('age', 'Unknown')
        gender = patient_info.get('gender', 'Unknown')
        symptoms = ', '.join(patient_info.get('symptoms', ['Not specified']))
        
        prompt = f"""You are a medical research specialist. Use web search to find REAL medical literature.

Patient Information:
- Age: {age}
- Gender: {gender}
- Symptoms: {symptoms}

Medical Findings:
{json.dumps(findings, indent=2)}

SEARCH INSTRUCTIONS:
1. Search PubMed for recent case reports matching these findings
2. Find clinical guidelines from authoritative sources (2023-2024)
3. Look for differential diagnosis resources
4. Find treatment protocols and outcomes

For EACH real source found, provide:
- Title: [Exact title from the source]
- Authors: [Real author names]
- Journal/Source: [Actual journal name]
- Year: [Publication year]
- Type: [Research/Case Study/Guideline]
- Key Findings: [Relevant findings]
- URL: [Actual URL]
- PubMed ID: [If available]

Return AT LEAST 5-7 real, verifiable references. Do NOT create fake references."""

        return await self._call_api(prompt)
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status"""
        status = super().get_status()
        status["specialized"] = "web_search"
        status["api_key_configured"] = bool(self.api_key)
        status["available_models"] = len([m for m in self.model_configs.values() if m.is_available()])
        return status