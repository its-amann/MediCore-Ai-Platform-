"""
State definition for LangGraph Medical Imaging Workflow
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph


class MedicalImagingState(TypedDict):
    """State for medical imaging workflow"""
    
    # Input data
    image_data: str  # Base64 encoded image
    patient_info: Dict[str, Any]  # Patient demographics and clinical info
    case_id: str
    user_id: str
    
    # Agent outputs
    image_analysis: Dict[str, Any]  # Raw analysis from image analysis agent
    findings: List[Dict[str, Any]]  # Structured findings with locations
    literature_references: List[Dict[str, Any]]  # PubMed search results
    heatmap_data: Dict[str, Any]  # Heatmap overlay data
    
    # Report generation
    detailed_report: Dict[str, Any]  # Final detailed report
    key_findings: List[str]  # Extracted key findings
    recommendations: List[str]  # Medical recommendations
    
    # Quality and metadata
    quality_score: float
    quality_feedback: str
    processing_time: float
    error: Optional[str]
    
    # Workflow control
    current_step: str
    completed_steps: List[str]
    
    # Additional data
    web_search_results: Optional[str]  # Additional web search results
    clinical_impression: str
    severity: str