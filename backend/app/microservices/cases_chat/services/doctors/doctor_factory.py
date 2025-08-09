"""
Factory for creating doctor service instances
"""
from typing import Dict, Type, Optional, List, Any
import logging
from ..base.doctor_service_base import BaseDoctorService
from .gemini_doctor import GeminiDoctorService
from .groq_doctor import GroqDoctorService
from ...core.config import settings
from ...core.exceptions import ConfigurationError, DoctorServiceError

logger = logging.getLogger(__name__)


class DoctorServiceFactory:
    """Factory for creating doctor service instances"""
    
    _services: Dict[str, Type[BaseDoctorService]] = {
        "gemini": GeminiDoctorService,
        "groq": GroqDoctorService,
    }
    
    _instances: Dict[str, BaseDoctorService] = {}
    _initialized = False
    
    @classmethod
    async def initialize(cls) -> None:
        """Initialize all configured doctor services"""
        if cls._initialized:
            return
        
        logger.info("Initializing doctor services...")
        
        available = cls.get_available_doctors()
        if not available:
            raise ConfigurationError("No doctor services configured. Please set API keys.")
        
        # Initialize all available services
        for service_type in available:
            try:
                doctor = await cls.create_doctor(service_type)
                if doctor:
                    await doctor.initialize()
                    logger.info(f"Initialized {service_type} doctor service")
            except Exception as e:
                logger.error(f"Failed to initialize {service_type} doctor service: {e}")
        
        cls._initialized = True
        logger.info(f"Doctor services initialized. Available: {available}")
    
    @classmethod
    async def create_doctor(cls, service_type: str, model_name: Optional[str] = None) -> Optional[BaseDoctorService]:
        """
        Create doctor service instance
        
        Args:
            service_type: Type of doctor service (gemini, groq, etc.)
            model_name: Optional specific model name
            
        Returns:
            Doctor service instance
            
        Raises:
            DoctorServiceError: If service type is unknown or not configured
        """
        if service_type not in cls._services:
            raise DoctorServiceError(f"Unknown doctor service type: {service_type}")
        
        # Check if already instantiated
        cache_key = f"{service_type}:{model_name or 'default'}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Get service class
        service_class = cls._services[service_type]
        
        # Get appropriate API key
        api_key = getattr(settings, f"{service_type}_api_key", None)
        if not api_key:
            raise DoctorServiceError(
                f"API key not configured for {service_type}",
                {"service": service_type, "config_key": f"{service_type}_api_key"}
            )
        
        try:
            # Create instance
            if model_name:
                instance = service_class(api_key, model_name)
            else:
                instance = service_class(api_key)
            
            # Cache the instance
            cls._instances[cache_key] = instance
            
            logger.info(f"Created {service_type} doctor service with model: {instance.model_name}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create {service_type} doctor service: {e}")
            raise DoctorServiceError(
                f"Failed to create {service_type} doctor service: {str(e)}",
                {"service": service_type, "error": str(e)}
            )
    
    @classmethod
    def get_available_doctors(cls) -> List[str]:
        """
        Get list of available doctor services
        
        Returns:
            List of configured doctor service types
        """
        available = []
        for service_type in cls._services.keys():
            api_key = getattr(settings, f"{service_type}_api_key", None)
            if api_key:
                available.append(service_type)
        return available
    
    @classmethod
    def get_available_models(cls, service_type: str) -> List[str]:
        """
        Get available models for a service type
        
        Args:
            service_type: The service type
            
        Returns:
            List of available model names
        """
        if service_type not in cls._services:
            return []
        
        # This could be enhanced to query the actual available models from each service
        # For now, return predefined lists
        models_map = {
            "gemini": ["gemini-pro", "gemini-pro-vision"],
            "groq": ["mixtral-8x7b-32768", "llama2-70b-4096"],
        }
        
        return models_map.get(service_type, [])
    
    @classmethod
    async def get_primary_doctor(cls) -> BaseDoctorService:
        """
        Get primary doctor service based on configuration
        
        Returns:
            Primary doctor service instance
            
        Raises:
            DoctorServiceError: If no services are configured
        """
        if not cls._initialized:
            await cls.initialize()
        
        available = cls.get_available_doctors()
        if not available:
            raise DoctorServiceError("No doctor services configured")
        
        # Use configured default or prefer Gemini if available
        primary_type = settings.default_ai_provider
        if primary_type not in available:
            primary_type = "gemini" if "gemini" in available else available[0]
        
        doctor = await cls.create_doctor(primary_type)
        if not doctor:
            raise DoctorServiceError(f"Failed to create primary doctor service: {primary_type}")
        
        return doctor
    
    @classmethod
    async def get_fallback_doctor(cls, exclude: List[str]) -> Optional[BaseDoctorService]:
        """
        Get a fallback doctor service
        
        Args:
            exclude: List of service types to exclude
            
        Returns:
            Fallback doctor service or None
        """
        available = cls.get_available_doctors()
        
        # Follow configured fallback order
        for service_type in settings.doctor_fallback_order:
            if service_type in available and service_type not in exclude:
                try:
                    doctor = await cls.create_doctor(service_type)
                    if doctor:
                        return doctor
                except Exception as e:
                    logger.error(f"Failed to create fallback doctor {service_type}: {e}")
        
        # Try any available service not in exclude list
        for service_type in available:
            if service_type not in exclude:
                try:
                    doctor = await cls.create_doctor(service_type)
                    if doctor:
                        return doctor
                except Exception as e:
                    logger.error(f"Failed to create fallback doctor {service_type}: {e}")
        
        return None
    
    @classmethod
    def register_service(cls, service_type: str, service_class: Type[BaseDoctorService]) -> None:
        """
        Register a new doctor service type
        
        Args:
            service_type: Service type identifier
            service_class: Service class
        """
        cls._services[service_type] = service_class
        logger.info(f"Registered doctor service type: {service_type}")
    
    @classmethod
    def unregister_service(cls, service_type: str) -> None:
        """
        Unregister a doctor service type
        
        Args:
            service_type: Service type identifier
        """
        if service_type in cls._services:
            del cls._services[service_type]
            
        # Remove any cached instances
        keys_to_remove = [k for k in cls._instances.keys() if k.startswith(f"{service_type}:")]
        for key in keys_to_remove:
            del cls._instances[key]
        
        logger.info(f"Unregistered doctor service type: {service_type}")
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached instances"""
        cls._instances.clear()
        cls._initialized = False
        logger.info("Cleared doctor service cache")
    
    @classmethod
    async def get_service_info(cls) -> Dict[str, Any]:
        """
        Get information about all available services
        
        Returns:
            Dictionary with service information
        """
        info = {
            "configured_services": cls.get_available_doctors(),
            "registered_types": list(cls._services.keys()),
            "primary_service": settings.default_ai_provider,
            "fallback_order": settings.doctor_fallback_order,
            "services": {}
        }
        
        for service_type in cls.get_available_doctors():
            try:
                doctor = await cls.create_doctor(service_type)
                if doctor:
                    info["services"][service_type] = await doctor.get_service_info()
            except Exception as e:
                info["services"][service_type] = {
                    "error": str(e),
                    "available": False
                }
        
        return info