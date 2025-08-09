"""
AI prompts for the Collaboration microservice
"""

from .ai_assistant_prompt import (
    get_ai_assistant_prompt,
    get_diagnostic_suggestion_prompt,
    get_treatment_suggestion_prompt,
    get_summary_generation_prompt,
    get_action_item_extraction_prompt
)

__all__ = [
    "get_ai_assistant_prompt",
    "get_diagnostic_suggestion_prompt",
    "get_treatment_suggestion_prompt",
    "get_summary_generation_prompt",
    "get_action_item_extraction_prompt"
]