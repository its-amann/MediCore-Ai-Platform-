"""
Nodes for LangGraph Medical Imaging Workflow
"""

import logging
import asyncio
from typing import Dict, Any

from .state import MedicalImagingState
from .agents import (
    ImageAnalysisAgent,
    LiteratureSearchAgent,
    DetailedReportWriterAgent,
    QualityCheckerAgent
)
from .tools import HeatmapGenerationTool

logger = logging.getLogger(__name__)


async def image_analysis_node(state: MedicalImagingState, provider_manager) -> MedicalImagingState:
    """Node for image analysis"""
    logger.info("Executing image analysis node")
    
    agent = ImageAnalysisAgent(provider_manager)
    return await agent.analyze(state)


async def parallel_processing_node(state: MedicalImagingState) -> MedicalImagingState:
    """Node for parallel execution of heatmap generation and literature search"""
    logger.info("Executing parallel processing node")
    
    async def generate_heatmap():
        """Generate heatmap in parallel"""
        try:
            tool = HeatmapGenerationTool()
            heatmap_data = await tool.generate_heatmap(
                image_data=state.get('image_data', ''),
                findings=state.get('findings', [])
            )
            return heatmap_data
        except Exception as e:
            logger.error(f"Heatmap generation error: {e}")
            return {'error': str(e)}
    
    async def search_literature():
        """Search literature in parallel"""
        try:
            agent = LiteratureSearchAgent()
            temp_state = state.copy()
            result_state = await agent.search(temp_state)
            return result_state.get('literature_references', [])
        except Exception as e:
            logger.error(f"Literature search error: {e}")
            return []
    
    # Execute both tasks in parallel
    heatmap_task = asyncio.create_task(generate_heatmap())
    literature_task = asyncio.create_task(search_literature())
    
    # Wait for both to complete
    heatmap_data, literature_refs = await asyncio.gather(heatmap_task, literature_task)
    
    # Update state with results
    state['heatmap_data'] = heatmap_data
    state['literature_references'] = literature_refs
    state['completed_steps'].extend(['heatmap_generation', 'literature_search'])
    
    logger.info("Parallel processing completed")
    return state


async def report_generation_node(state: MedicalImagingState, provider_manager) -> MedicalImagingState:
    """Node for detailed report generation"""
    logger.info("Executing report generation node")
    
    agent = DetailedReportWriterAgent(provider_manager)
    return await agent.write_report(state)


async def quality_check_node(state: MedicalImagingState, provider_manager) -> MedicalImagingState:
    """Node for quality checking"""
    logger.info("Executing quality check node")
    
    agent = QualityCheckerAgent(provider_manager)
    return await agent.check_quality(state)


async def final_processing_node(state: MedicalImagingState) -> MedicalImagingState:
    """Node for final processing and cleanup"""
    logger.info("Executing final processing node")
    
    # Extract clinical impression from report
    report_content = state.get('detailed_report', {}).get('content', '')
    
    # Simple extraction of clinical impression
    if "CLINICAL SUMMARY" in report_content:
        start = report_content.find("CLINICAL SUMMARY")
        end = report_content.find("\n\n", start)
        if end == -1:
            end = len(report_content)
        clinical_impression = report_content[start:end].replace("CLINICAL SUMMARY", "").strip()
        state['clinical_impression'] = clinical_impression[:500]  # Limit length
    else:
        state['clinical_impression'] = "See detailed report for clinical impression"
    
    # Determine severity based on findings
    findings = state.get('findings', [])
    severity_counts = {'mild': 0, 'moderate': 0, 'severe': 0}
    
    for finding in findings:
        severity = finding.get('severity', 'moderate')
        severity_counts[severity] += 1
    
    if severity_counts['severe'] > 0:
        state['severity'] = 'high'
    elif severity_counts['moderate'] > 2:
        state['severity'] = 'medium'
    else:
        state['severity'] = 'low'
    
    state['current_step'] = 'completed'
    state['completed_steps'].append('final_processing')
    
    logger.info("Workflow completed successfully")
    return state