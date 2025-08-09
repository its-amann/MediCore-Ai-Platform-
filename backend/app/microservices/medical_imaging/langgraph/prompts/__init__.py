"""
System prompts for all agents in the medical imaging workflow
"""

from .image_analysis_prompt import IMAGE_ANALYSIS_SYSTEM_PROMPT
from .literature_search_prompt import LITERATURE_SEARCH_SYSTEM_PROMPT
from .report_writer_prompt import REPORT_WRITER_SYSTEM_PROMPT
from .quality_checker_prompt import QUALITY_CHECKER_SYSTEM_PROMPT

__all__ = [
    'IMAGE_ANALYSIS_SYSTEM_PROMPT',
    'LITERATURE_SEARCH_SYSTEM_PROMPT',
    'REPORT_WRITER_SYSTEM_PROMPT',
    'QUALITY_CHECKER_SYSTEM_PROMPT'
]