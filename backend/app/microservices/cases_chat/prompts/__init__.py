"""
Medical AI Doctor Prompts
Centralized prompt management for all AI doctors
"""

from .general_consultant_prompt import GENERAL_CONSULTANT_PROMPT, get_general_consultant_prompt
from .cardiologist_prompt import CARDIOLOGIST_PROMPT, get_cardiologist_prompt
from .bp_specialist_prompt import BP_SPECIALIST_PROMPT, get_bp_specialist_prompt
from .shared_prompts import (
    get_handover_prompt,
    get_case_summary_prompt,
    get_report_generation_prompt,
    get_image_analysis_prompt,
    get_audio_context_prompt,
    get_mcp_context_prompt,
    MEDICAL_GUIDELINES,
    COMMUNICATION_GUIDELINES
)

__all__ = [
    "GENERAL_CONSULTANT_PROMPT",
    "get_general_consultant_prompt",
    "CARDIOLOGIST_PROMPT", 
    "get_cardiologist_prompt",
    "BP_SPECIALIST_PROMPT",
    "get_bp_specialist_prompt",
    "get_handover_prompt",
    "get_case_summary_prompt",
    "get_report_generation_prompt",
    "get_image_analysis_prompt",
    "get_audio_context_prompt",
    "get_mcp_context_prompt",
    "MEDICAL_GUIDELINES",
    "COMMUNICATION_GUIDELINES"
]