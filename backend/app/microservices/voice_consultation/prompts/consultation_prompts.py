"""
Simple wrapper for consultation prompts to maintain backward compatibility
"""

# Import from core location
from ..core.prompts.consultation_prompts import get_doctor_prompt, get_specialist_instructions

# Re-export
__all__ = ['get_doctor_prompt', 'get_specialist_instructions']