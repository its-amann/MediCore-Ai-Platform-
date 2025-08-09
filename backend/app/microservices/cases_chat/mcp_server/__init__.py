"""
Medical History Service - Simplified MCP Server
Provides case history retrieval and analysis for AI doctors
"""

from .medical_history_service import (
    MedicalHistoryService,
    get_medical_history_service,
    CaseContext,
    SimilarCase
)
from .mcp_config import MCPConfig, get_config
from .mcp_client import MCPClient, AsyncMCPClient, MCPConnection

__version__ = "2.0.0"
__all__ = [
    "MedicalHistoryService",
    "get_medical_history_service",
    "CaseContext",
    "SimilarCase",
    "MCPConfig",
    "get_config",
    "MCPClient",
    "AsyncMCPClient",
    "MCPConnection"
]