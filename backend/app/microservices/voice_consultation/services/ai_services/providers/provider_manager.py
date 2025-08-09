"""
Unified Provider Manager
Orchestrates multiple AI providers with intelligent fallback and load balancing
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
from enum import Enum

from .base_provider import BaseAIProvider, ProviderStatus, ProviderCapabilities
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .openrouter_provider import OpenRouterProvider

from app.microservices.medical_imaging.models.imaging_models import (
    ImagingReport, ImageAnalysis, ImageType
)

logger = logging.getLogger(__name__)


class ProviderPriority(Enum):
    """Provider priority levels"""
    PRIMARY = 1
    SECONDARY = 2
    TERTIARY = 3
    FALLBACK = 4


class UnifiedProviderManager:
    """
    Manages multiple AI providers with intelligent routing and fallback
    Eliminates redundancy by centralizing all provider logic
    """
    
    def __init__(self):
        """Initialize the unified provider manager"""
        self.providers: Dict[str, BaseAIProvider] = {}
        self.provider_priority: Dict[str, ProviderPriority] = {}
        self.failed_providers: List[str] = []
        self.last_successful_provider = None
        
        # Initialize providers
        self._initialize_providers()
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.provider_usage = {name: 0 for name in self.providers.keys()}
        
        logger.info(f"Unified Provider Manager initialized with {len(self.providers)} providers")
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        
        # Try to initialize Gemini (Primary)
        try:
            gemini = GeminiProvider()
            self.providers["gemini"] = gemini
            self.provider_priority["gemini"] = ProviderPriority.PRIMARY
            logger.info("Gemini provider initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini provider: {e}")
        
        # Try to initialize Groq (Secondary - fast fallback)
        try:
            groq = GroqProvider()
            self.providers["groq"] = groq
            self.provider_priority["groq"] = ProviderPriority.SECONDARY
            logger.info("Groq provider initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Groq provider: {e}")
        
        # Try to initialize OpenRouter (Tertiary - extensive models)
        try:
            openrouter = OpenRouterProvider()
            if openrouter.status != ProviderStatus.DISABLED:
                self.providers["openrouter"] = openrouter
                self.provider_priority["openrouter"] = ProviderPriority.TERTIARY
                logger.info("OpenRouter provider initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize OpenRouter provider: {e}")
        
        if not self.providers:
            raise ValueError("No AI providers could be initialized!")
    
    def get_available_providers(self) -> List[Tuple[str, BaseAIProvider]]:
        """Get list of available providers sorted by priority"""
        available = []
        
        for name, provider in self.providers.items():
            # Skip failed providers
            if name in self.failed_providers:
                continue
            
            # Check provider status
            if provider.check_rate_limits():
                available.append((name, provider))
        
        # Sort by priority
        available.sort(key=lambda x: self.provider_priority[x[0]].value)
        
        # If last successful provider is available, prioritize it
        if self.last_successful_provider:
            available = sorted(available, key=lambda x: 0 if x[0] == self.last_successful_provider else 1)
        
        return available
    
    def get_next_available_provider(self) -> Optional[Dict[str, Any]]:
        """Get the next available provider with model and API key information"""
        available_providers = self.get_available_providers()
        
        if not available_providers:
            return None
        
        # Get the first available provider
        provider_name, provider = available_providers[0]
        
        # Get an available model for this provider
        model_id = self.get_available_model(provider_name, provider, require_vision=True)
        
        if not model_id:
            # Try next provider if current one has no available models
            for name, prov in available_providers[1:]:
                model_id = self.get_available_model(name, prov, require_vision=True)
                if model_id:
                    provider_name = name
                    provider = prov
                    break
        
        if not model_id:
            return None
        
        # Get API key
        api_key = provider.api_keys[0] if hasattr(provider, 'api_keys') else provider.api_key
        
        return {
            'type': provider_name,
            'model_id': model_id,
            'api_key': api_key,
            'provider': provider
        }
    
    def get_available_model(self, provider_name: str, provider: BaseAIProvider, require_vision: bool = False) -> Optional[str]:
        """Get an available model from a provider that is not rate limited"""
        models = provider.get_available_models(require_vision)
        
        # Check each model for rate limit status
        for model in models:
            if model.is_available():
                logger.info(f"Selected model {model.model_id} from {provider_name} (daily: {model.usage_count_daily}/{model.rate_limit_daily})")
                return model.model_id
            else:
                # Log why model is not available
                if model.rate_limit_reset_time:
                    time_until_reset = (model.rate_limit_reset_time - datetime.now()).total_seconds() / 3600
                    logger.debug(f"Model {model.model_id} is rate limited for {time_until_reset:.1f} more hours")
        
        logger.warning(f"No available models found for {provider_name}")
        return None
    
    async def analyze_image(
        self,
        image_data: str,
        image_type: str,
        patient_info: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Analyze medical image using available providers
        Returns: (analysis_result, provider_used)
        """
        self.total_requests += 1
        
        # Get available providers
        available_providers = self.get_available_providers()
        
        if not available_providers:
            raise Exception("No AI providers available - all are rate limited or in cooldown")
        
        # If preferred provider specified and available, try it first
        if preferred_provider and preferred_provider in [name for name, _ in available_providers]:
            provider = self.providers[preferred_provider]
            try:
                logger.info(f"Trying preferred provider: {preferred_provider}")
                result = await provider.generate_image_analysis(
                    image_data, image_type, patient_info, custom_prompt
                )
                if result:
                    self.successful_requests += 1
                    self.provider_usage[preferred_provider] += 1
                    self.last_successful_provider = preferred_provider
                    logger.info(f"Successfully analyzed image with {preferred_provider}")
                    return result, preferred_provider
            except Exception as e:
                logger.warning(f"Preferred provider {preferred_provider} failed: {e}")
        
        # Try each available provider
        for provider_name, provider in available_providers:
            if provider_name == preferred_provider:
                continue  # Already tried
            
            try:
                logger.info(f"Trying provider: {provider_name}")
                result = await provider.generate_image_analysis(
                    image_data, image_type, patient_info, custom_prompt
                )
                
                if result:
                    self.successful_requests += 1
                    self.provider_usage[provider_name] += 1
                    self.last_successful_provider = provider_name
                    logger.info(f"Successfully analyzed image with {provider_name}")
                    return result, provider_name
                    
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                
                # Check if it's a vision capability issue
                if "vision" in str(e).lower() or "image" in str(e).lower():
                    logger.info(f"Provider {provider_name} does not support image analysis, trying next...")
                
                continue
        
        # All providers failed
        raise Exception(f"All {len(available_providers)} providers failed to analyze image")
    
    async def generate_report(
        self,
        analyses: List[ImageAnalysis],
        patient_info: Optional[Dict[str, Any]] = None,
        case_info: Optional[Dict[str, Any]] = None,
        preferred_provider: Optional[str] = None
    ) -> Tuple[ImagingReport, str]:
        """
        Generate medical report using available providers
        Returns: (report, provider_used)
        """
        self.total_requests += 1
        
        # Get available providers
        available_providers = self.get_available_providers()
        
        if not available_providers:
            raise Exception("No AI providers available - all are rate limited or in cooldown")
        
        # If preferred provider specified and available, try it first
        if preferred_provider and preferred_provider in [name for name, _ in available_providers]:
            provider = self.providers[preferred_provider]
            try:
                logger.info(f"Trying preferred provider for report: {preferred_provider}")
                result = await provider.generate_report(analyses, patient_info, case_info)
                if result:
                    self.successful_requests += 1
                    self.provider_usage[preferred_provider] += 1
                    self.last_successful_provider = preferred_provider
                    logger.info(f"Successfully generated report with {preferred_provider}")
                    return result, preferred_provider
            except Exception as e:
                logger.warning(f"Preferred provider {preferred_provider} failed: {e}")
        
        # Try each available provider
        for provider_name, provider in available_providers:
            if provider_name == preferred_provider:
                continue  # Already tried
            
            try:
                logger.info(f"Trying provider for report: {provider_name}")
                result = await provider.generate_report(analyses, patient_info, case_info)
                
                if result:
                    self.successful_requests += 1
                    self.provider_usage[provider_name] += 1
                    self.last_successful_provider = provider_name
                    logger.info(f"Successfully generated report with {provider_name}")
                    return result, provider_name
                    
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        # All providers failed
        raise Exception(f"All {len(available_providers)} providers failed to generate report")
    
    async def process_medical_images(
        self,
        images: List[Dict[str, Any]],
        patient_info: Dict[str, Any],
        case_id: str
    ) -> ImagingReport:
        """
        Complete medical image processing pipeline
        Analyzes images and generates comprehensive report
        """
        logger.info(f"Processing {len(images)} images for case {case_id}")
        
        # Analyze each image
        analyses = []
        for idx, image in enumerate(images):
            logger.info(f"Analyzing image {idx + 1}/{len(images)}")
            
            # Extract image data
            image_data = image.get("base64_data", "")
            image_type = image.get("type", "unknown")
            
            try:
                # Analyze image with fallback
                analysis_text, provider_used = await self.analyze_image(
                    image_data=image_data,
                    image_type=image_type,
                    patient_info=patient_info
                )
                
                # Create ImageAnalysis object
                analysis = ImageAnalysis(
                    image_id=image.get("id", f"img_{idx}"),
                    filename=image.get("filename", f"image_{idx}.jpg"),
                    image_type=ImageType(image_type.lower()) if image_type.lower() in [e.value for e in ImageType] else ImageType.OTHER,
                    analysis_text=analysis_text,
                    findings=[],  # Will be populated in report generation
                    keywords=[]
                )
                analyses.append(analysis)
                
                logger.info(f"Image {idx + 1} analyzed successfully with {provider_used}")
                
            except Exception as e:
                logger.error(f"Failed to analyze image {idx + 1}: {e}")
                # Create placeholder analysis
                analysis = ImageAnalysis(
                    image_id=image.get("id", f"img_{idx}"),
                    filename=image.get("filename", f"image_{idx}.jpg"),
                    image_type=ImageType.OTHER,
                    analysis_text=f"Analysis failed: {str(e)}",
                    findings=[],
                    keywords=[]
                )
                analyses.append(analysis)
        
        # Generate comprehensive report
        logger.info("Generating comprehensive medical report...")
        try:
            report, provider_used = await self.generate_report(
                analyses=analyses,
                patient_info=patient_info,
                case_info={"case_id": case_id}
            )
            
            logger.info(f"Report generated successfully with {provider_used}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            # Return basic report with analyses
            from app.microservices.medical_imaging.models.imaging_models import ReportStatus
            return ImagingReport(
                report_id=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                case_id=case_id,
                user_id=patient_info.get("user_id", "system"),
                images=analyses,
                overall_analysis="Report generation failed due to provider errors",
                clinical_impression="Unable to generate clinical impression",
                recommendations=["Please retry report generation"],
                status=ReportStatus.FAILED,
                completed_at=datetime.now()
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics"""
        stats = {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "provider_usage": self.provider_usage,
            "last_successful_provider": self.last_successful_provider,
            "providers": {}
        }
        
        # Add individual provider stats
        for name, provider in self.providers.items():
            stats["providers"][name] = provider.get_status()
        
        return stats
    
    def reset_failed_providers(self):
        """Reset failed providers list to retry them"""
        self.failed_providers = []
        logger.info("Failed providers list reset")
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.total_requests = 0
        self.successful_requests = 0
        self.provider_usage = {name: 0 for name in self.providers.keys()}
        for provider in self.providers.values():
            provider.reset_stats()
        logger.info("Statistics reset")


# Singleton instance
_provider_manager_instance = None


def get_provider_manager() -> UnifiedProviderManager:
    """Get or create the unified provider manager instance"""
    global _provider_manager_instance
    if _provider_manager_instance is None:
        _provider_manager_instance = UnifiedProviderManager()
    return _provider_manager_instance