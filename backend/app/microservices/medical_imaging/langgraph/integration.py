"""
Integration module to use LangGraph workflow with existing system
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .workflow import MedicalImagingWorkflow
from app.microservices.medical_imaging.workflows.websocket_adapter import send_medical_progress

logger = logging.getLogger(__name__)


class LangGraphIntegration:
    """Integration layer for LangGraph workflow"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
        self.workflow = MedicalImagingWorkflow(provider_manager)
    
    async def process_medical_image(
        self,
        image_data: str,
        patient_info: Dict[str, Any],
        case_id: str,
        user_id: str,
        websocket_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process medical image using LangGraph workflow
        
        This method adapts the LangGraph workflow output to match
        the existing workflow manager's expected format
        """
        
        # Progress callback that sends updates via WebSocket
        async def progress_callback(progress_info: dict):
            if websocket_state:
                # Map LangGraph progress to existing WebSocket format
                step_mapping = {
                    'image_analysis': 'Image Analysis',
                    'parallel_processing': 'Literature Search & Heatmap Generation',
                    'report_generation': 'Report Generation',
                    'quality_check': 'Quality Check',
                    'final_processing': 'Finalizing'
                }
                
                current_step = progress_info.get('step', '')
                message = step_mapping.get(current_step, current_step)
                
                # Calculate progress percentage
                total_steps = 5
                completed = len(progress_info.get('completed_steps', []))
                progress = int((completed / total_steps) * 100)
                
                await send_medical_progress(
                    user_id=user_id,
                    username=websocket_state.get('username', 'User'),
                    message=message,
                    progress=progress,
                    data={
                        'findings_count': progress_info.get('findings_count', 0),
                        'literature_count': progress_info.get('literature_count', 0),
                        'has_heatmap': progress_info.get('has_heatmap', False)
                    }
                )
        
        try:
            # Run LangGraph workflow
            result = await self.workflow.run(
                image_data=image_data,
                patient_info=patient_info,
                case_id=case_id,
                user_id=user_id,
                progress_callback=progress_callback if websocket_state else None
            )
            
            # Adapt result to match existing workflow manager format
            workflow_state = {
                'case_id': case_id,
                'user_id': user_id,
                'patient_info': patient_info,
                'timestamp': datetime.now().isoformat(),
                'images_processed': 1,
                
                # Findings and analysis
                'abnormalities_detected': result.get('findings', []),
                'key_findings': result.get('key_findings', []),
                'clinical_impression': result.get('clinical_impression', ''),
                
                # Report
                'final_report': result.get('detailed_report', {}),
                
                # Literature
                'literature_references': result.get('literature_references', []),
                
                # Heatmap
                'heatmap_data': result.get('heatmap_data', {}),
                
                # Quality and metadata
                'quality_score': result.get('quality_score', 0),
                'quality_feedback': result.get('quality_feedback', ''),
                'severity': result.get('severity', 'low'),
                
                # Recommendations
                'recommendations': result.get('recommendations', []),
                
                # Processing info
                'processing_time': result.get('processing_time', 0),
                'workflow_version': 'langgraph_2.0',
                
                # Additional data
                'web_search_performed': bool(result.get('web_search_results')),
                'completed_steps': result.get('completed_steps', []),
                
                # Error handling
                'error': result.get('error')
            }
            
            # Send final progress update
            if websocket_state:
                await send_medical_progress(
                    user_id=user_id,
                    username=websocket_state.get('username', 'User'),
                    message='Analysis Complete',
                    progress=100,
                    data={
                        'case_id': case_id,
                        'findings_count': len(workflow_state['abnormalities_detected']),
                        'quality_score': workflow_state['quality_score'],
                        'has_report': bool(workflow_state['final_report'])
                    }
                )
            
            logger.info(f"LangGraph workflow completed successfully for case {case_id}")
            return workflow_state
            
        except Exception as e:
            logger.error(f"LangGraph workflow error: {str(e)}")
            
            # Return error state in expected format
            error_state = {
                'case_id': case_id,
                'user_id': user_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'workflow_version': 'langgraph_2.0',
                'completed_steps': []
            }
            
            # Send error via WebSocket
            if websocket_state:
                await send_medical_progress(
                    user_id=user_id,
                    username=websocket_state.get('username', 'User'),
                    message=f'Error: {str(e)}',
                    progress=0,
                    data={'error': True}
                )
            
            return error_state
    
    def should_use_langgraph(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine whether to use LangGraph workflow
        
        Can be configured via environment variable or config
        """
        import os
        
        # Check environment variable
        if os.getenv('USE_LANGGRAPH_WORKFLOW', '').lower() == 'true':
            return True
        
        # Check config
        if config and config.get('use_langgraph', False):
            return True
        
        # Default to False for now (can change to True when ready)
        return False