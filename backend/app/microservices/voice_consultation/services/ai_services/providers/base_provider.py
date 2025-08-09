"""
Base AI Provider Class - Common functionality for all AI providers
Reduces redundancy by providing shared methods and interfaces
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import asyncio
import json

from app.microservices.medical_imaging.models.imaging_models import (
    ImagingReport, ImageAnalysis, ImageType, ReportStatus
)

logger = logging.getLogger(__name__)


class ProviderCapabilities(Enum):
    """Capabilities that providers can have"""
    VISION = "vision"  # Can analyze images directly
    REASONING = "reasoning"  # Advanced reasoning capabilities
    MEDICAL = "medical"  # Medical domain expertise
    CODING = "coding"  # Code generation
    ANALYSIS = "analysis"  # Deep analysis
    CITATIONS = "citations"  # Can generate citations
    WEB_SEARCH = "web_search"  # Can search the web


class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    ERROR = "error"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


class ModelConfig:
    """Configuration for a single model with rate limit tracking"""
    def __init__(
        self,
        model_id: str,
        context_length: int,
        capabilities: List[str],
        rate_limit_daily: int,
        rate_limit_per_minute: int,
        priority: int = 100,
        cost_category: str = "free",
        supports_vision: bool = False
    ):
        self.model_id = model_id
        self.context_length = context_length
        self.capabilities = capabilities
        self.rate_limit_daily = rate_limit_daily
        self.rate_limit_per_minute = rate_limit_per_minute
        self.priority = priority
        self.cost_category = cost_category
        self.supports_vision = supports_vision or ProviderCapabilities.VISION.value in capabilities
        
        # Rate limit tracking
        self.is_rate_limited = False
        self.rate_limited_at = None  # Timestamp when rate limited
        self.rate_limit_reset_time = None  # When the rate limit will reset
        self.usage_count_daily = 0
        self.usage_count_minute = 0
        self.last_used_at = None
        self.last_reset_daily = datetime.now()
        self.last_reset_minute = datetime.now()
    
    def is_available(self) -> bool:
        """Check if model is available (not rate limited)"""
        if not self.is_rate_limited:
            return True
            
        # Check if rate limit has expired
        now = datetime.now()
        if self.rate_limit_reset_time and now >= self.rate_limit_reset_time:
            # Reset rate limit
            self.is_rate_limited = False
            self.rate_limited_at = None
            self.rate_limit_reset_time = None
            self.usage_count_daily = 0
            self.usage_count_minute = 0
            return True
            
        return False
    
    def mark_rate_limited(self, reset_after_hours: int = 24):
        """Mark model as rate limited"""
        now = datetime.now()
        self.is_rate_limited = True
        self.rate_limited_at = now
        self.rate_limit_reset_time = now + timedelta(hours=reset_after_hours)
        logger.warning(f"Model {self.model_id} rate limited until {self.rate_limit_reset_time}")
    
    def update_usage(self, success: bool = True):
        """Update usage counters"""
        now = datetime.now()
        
        # Reset minute counter if needed
        if (now - self.last_reset_minute).seconds >= 60:
            self.usage_count_minute = 0
            self.last_reset_minute = now
            
        # Reset daily counter if needed
        if (now - self.last_reset_daily).days >= 1:
            self.usage_count_daily = 0
            self.last_reset_daily = now
            
        if success:
            self.usage_count_daily += 1
            self.usage_count_minute += 1
            self.last_used_at = now
            
            # Check if we've hit rate limits
            if self.usage_count_daily >= self.rate_limit_daily:
                self.mark_rate_limited(24)  # 24 hour reset for daily limit
            elif self.usage_count_minute >= self.rate_limit_per_minute:
                self.mark_rate_limited(0.0167)  # 1 minute reset (1/60 hour)


class BaseAIProvider(ABC):
    """
    Base class for all AI providers
    Implements common functionality to reduce code duplication
    """
    
    def __init__(self, provider_name: str):
        """Initialize base provider"""
        self.provider_name = provider_name
        self.status = ProviderStatus.AVAILABLE
        self.last_error = None
        self.last_success = None
        
        # Rate limiting
        self.request_count = defaultdict(lambda: {"daily": 0, "minute": 0, "last_reset": datetime.now()})
        self.cooldown_until = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info(f"{provider_name} provider initialized")
    
    @abstractmethod
    async def _call_api(
        self,
        prompt: str,
        image_data: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Make API call to the provider
        Must be implemented by each provider
        """
        pass
    
    @abstractmethod
    def get_available_models(self, require_vision: bool = False) -> List[ModelConfig]:
        """
        Get list of available models from this provider
        Must be implemented by each provider
        """
        pass
    
    def check_rate_limits(self, model: Optional[str] = None) -> bool:
        """Check if within rate limits"""
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            self.status = ProviderStatus.COOLDOWN
            return False
        
        # Reset counters if needed
        now = datetime.now()
        for model_id, usage in self.request_count.items():
            # Reset minute counter
            if (now - usage["last_reset"]).seconds >= 60:
                usage["minute"] = 0
            # Reset daily counter  
            if (now - usage["last_reset"]).days >= 1:
                usage["daily"] = 0
                usage["last_reset"] = now
        
        self.status = ProviderStatus.AVAILABLE
        return True
    
    def update_usage(self, model: Optional[str] = None, success: bool = True):
        """Update usage statistics"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            self.consecutive_failures = 0
            self.last_success = datetime.now()
            self.status = ProviderStatus.AVAILABLE
        else:
            self.failed_requests += 1
            self.consecutive_failures += 1
            
            # Apply cooldown if too many failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                cooldown_minutes = min(60 * (2 ** (self.consecutive_failures - 3)), 1440)  # Max 24 hours
                self.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
                self.status = ProviderStatus.COOLDOWN
                logger.warning(f"{self.provider_name} entering cooldown for {cooldown_minutes} minutes")
        
        # Update model-specific counters
        if model:
            usage = self.request_count[model]
            usage["daily"] += 1
            usage["minute"] += 1
    
    async def generate_image_analysis(
        self,
        image_data: str,
        image_type: str,
        patient_info: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Generate analysis for a single image"""
        
        # Check if provider is available
        if not self.check_rate_limits():
            raise Exception(f"{self.provider_name} is in cooldown or rate limited")
        
        # Build prompt
        prompt = custom_prompt or self._build_analysis_prompt(image_type, patient_info)
        
        try:
            # Get models that support vision if image data provided
            require_vision = bool(image_data)
            models = self.get_available_models(require_vision=require_vision)
            
            if not models:
                raise Exception(f"No available models for {self.provider_name}")
            
            # Try each model
            for model_config in models:
                try:
                    result = await self._call_api(
                        prompt=prompt,
                        image_data=image_data if require_vision else None,
                        model=model_config.model_id
                    )
                    
                    if result:
                        self.update_usage(model_config.model_id, success=True)
                        return result
                        
                except Exception as e:
                    logger.warning(f"{self.provider_name} model {model_config.model_id} failed: {e}")
                    self.update_usage(model_config.model_id, success=False)
                    continue
            
            raise Exception(f"All models failed for {self.provider_name}")
            
        except Exception as e:
            self.last_error = str(e)
            self.update_usage(success=False)
            raise
    
    async def generate_report(
        self,
        analyses: List[ImageAnalysis],
        patient_info: Optional[Dict[str, Any]] = None,
        case_info: Optional[Dict[str, Any]] = None
    ) -> ImagingReport:
        """Generate complete medical report"""
        
        # Check availability
        if not self.check_rate_limits():
            raise Exception(f"{self.provider_name} is in cooldown or rate limited")
        
        # Build comprehensive prompt
        prompt = self._build_report_prompt(analyses, patient_info, case_info)
        
        try:
            # Get available models (vision not required for report generation)
            models = self.get_available_models(require_vision=False)
            
            if not models:
                raise Exception(f"No available models for {self.provider_name}")
            
            # Try each model
            for model_config in models:
                try:
                    result = await self._call_api(
                        prompt=prompt,
                        model=model_config.model_id
                    )
                    
                    if result:
                        self.update_usage(model_config.model_id, success=True)
                        return self._parse_report_response(result, analyses, patient_info, case_info)
                        
                except Exception as e:
                    logger.warning(f"{self.provider_name} model {model_config.model_id} failed: {e}")
                    self.update_usage(model_config.model_id, success=False)
                    continue
            
            raise Exception(f"All models failed for {self.provider_name}")
            
        except Exception as e:
            self.last_error = str(e)
            self.update_usage(success=False)
            raise
    
    def _build_analysis_prompt(self, image_type: str, patient_info: Optional[Dict] = None) -> str:
        """Build prompt for image analysis"""
        prompt = f"""You are an expert radiologist analyzing a medical {image_type} image.
        
Patient Information:
{json.dumps(patient_info, indent=2) if patient_info else 'Not provided'}

Please provide:
1. Initial observations about the image
2. Any abnormalities or notable findings  
3. Clinical significance of findings
4. Recommendations for follow-up if needed

Be thorough but concise in your analysis."""
        return prompt
    
    def _build_report_prompt(
        self,
        analyses: List[ImageAnalysis],
        patient_info: Optional[Dict] = None,
        case_info: Optional[Dict] = None
    ) -> str:
        """Build prompt for comprehensive report"""
        prompt = f"""You are an expert radiologist creating a comprehensive medical imaging report.

Patient Information:
{json.dumps(patient_info, indent=2) if patient_info else 'Not provided'}

Case Information:
{json.dumps(case_info, indent=2) if case_info else 'Not provided'}

Individual Image Analyses:
"""
        for idx, analysis in enumerate(analyses):
            prompt += f"\n\nImage {idx + 1} ({analysis.image_type.value}):\n{analysis.analysis_text}"
        
        prompt += """

Please provide a comprehensive medical report with:
1. Overall Clinical Impression: Synthesize findings across all images
2. Key Findings: List the most significant findings
3. Differential Diagnosis: If applicable
4. Recommendations: Next steps for patient care
5. Summary: Brief summary suitable for referring physician

Format as a professional medical report."""
        return prompt
    
    def _parse_report_response(
        self,
        response: str,
        analyses: List[ImageAnalysis],
        patient_info: Optional[Dict],
        case_info: Optional[Dict]
    ) -> ImagingReport:
        """Parse AI response into ImagingReport format"""
        
        # Extract sections from response
        sections = self._extract_sections(response)
        
        # Ensure we have content for overall_analysis
        overall_analysis = sections.get("impression", "")
        if not overall_analysis:
            # Use the full response if no specific impression section found
            overall_analysis = response.strip()
        
        # Extract clinical impression
        clinical_impression = sections.get("clinical_impression", "")
        if not clinical_impression and overall_analysis:
            # Use first part of overall analysis as clinical impression
            clinical_impression = overall_analysis[:500] + "..." if len(overall_analysis) > 500 else overall_analysis
        
        # Create report
        report = ImagingReport(
            report_id=f"{self.provider_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            case_id=case_info.get("case_id", "") if case_info else "",
            user_id=patient_info.get("user_id", "system") if patient_info else "system",
            images=analyses,
            overall_analysis=overall_analysis,
            clinical_impression=clinical_impression,
            recommendations=sections.get("recommendations", []),
            status=ReportStatus.COMPLETED,
            completed_at=datetime.now()
        )
        
        return report
    
    def _extract_sections(self, response: str) -> Dict[str, Any]:
        """Extract sections from AI response"""
        sections = {
            "impression": "",
            "clinical_impression": "",
            "findings": [],
            "recommendations": []
        }
        
        # Simple extraction logic - can be overridden by specific providers
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if any(keyword in line.lower() for keyword in ["impression", "assessment"]):
                current_section = "impression"
            elif "clinical" in line.lower() and "impression" in line.lower():
                current_section = "clinical_impression"
            elif any(keyword in line.lower() for keyword in ["finding", "observation"]):
                current_section = "findings"
            elif "recommendation" in line.lower():
                current_section = "recommendations"
            elif current_section:
                # Add content to current section
                if current_section == "findings" or current_section == "recommendations":
                    if line.startswith(('-', '•', '*', '1', '2', '3')):
                        sections[current_section].append(line.lstrip('-•*123456789. '))
                else:
                    sections[current_section] += line + " "
        
        # Clean up sections
        for key in ["impression", "clinical_impression"]:
            sections[key] = sections[key].strip()
        
        return sections
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status and statistics"""
        return {
            "provider": self.provider_name,
            "status": self.status.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "consecutive_failures": self.consecutive_failures,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.consecutive_failures = 0
        self.status = ProviderStatus.AVAILABLE
        self.cooldown_until = None