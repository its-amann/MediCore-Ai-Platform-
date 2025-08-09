"""
Main LangGraph Medical Imaging Workflow
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import MedicalImagingState
from .nodes import (
    image_analysis_node,
    parallel_processing_node,
    report_generation_node,
    quality_check_node,
    final_processing_node
)

logger = logging.getLogger(__name__)


class MedicalImagingWorkflow:
    """LangGraph-based medical imaging workflow"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the workflow graph"""
        
        # Create the graph
        workflow = StateGraph(MedicalImagingState)
        
        # Add nodes
        async def image_analysis(state):
            return await image_analysis_node(state, self.provider_manager)
        
        async def report_generation(state):
            return await report_generation_node(state, self.provider_manager)
        
        async def quality_check(state):
            return await quality_check_node(state, self.provider_manager)
        
        workflow.add_node("image_analysis", image_analysis)
        workflow.add_node("parallel_processing", parallel_processing_node)
        workflow.add_node("report_generation", report_generation)
        workflow.add_node("quality_check", quality_check)
        workflow.add_node("final_processing", final_processing_node)
        
        # Define the flow
        workflow.set_entry_point("image_analysis")
        
        # Add edges
        workflow.add_edge("image_analysis", "parallel_processing")
        workflow.add_edge("parallel_processing", "report_generation")
        workflow.add_edge("report_generation", "quality_check")
        workflow.add_edge("quality_check", "final_processing")
        workflow.add_edge("final_processing", END)
        
        return workflow
    
    async def run(
        self,
        image_data: str,
        patient_info: Dict[str, Any],
        case_id: str,
        user_id: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Run the medical imaging workflow
        
        Args:
            image_data: Base64 encoded image data
            patient_info: Patient demographics and clinical information
            case_id: Unique case identifier
            user_id: User identifier
            progress_callback: Optional callback for progress updates
            
        Returns:
            Final workflow state with all results
        """
        
        start_time = datetime.now()
        
        # Initialize state
        initial_state = MedicalImagingState(
            image_data=image_data,
            patient_info=patient_info,
            case_id=case_id,
            user_id=user_id,
            image_analysis={},
            findings=[],
            literature_references=[],
            heatmap_data={},
            detailed_report={},
            key_findings=[],
            recommendations=[],
            quality_score=0.0,
            quality_feedback="",
            processing_time=0.0,
            error=None,
            current_step="starting",
            completed_steps=[],
            web_search_results=None,
            clinical_impression="",
            severity="low"
        )
        
        try:
            logger.info(f"Starting medical imaging workflow for case {case_id}")
            
            # Compile the workflow
            app = self.workflow.compile(
                checkpointer=MemorySaver()  # Use memory-based checkpointing
            )
            
            # Run the workflow
            config = {"configurable": {"thread_id": case_id}}
            
            # Stream execution for progress updates
            async for event in app.astream(initial_state, config):
                # Extract current node
                for node, state in event.items():
                    logger.info(f"Completed node: {node}")
                    
                    # Send progress update if callback provided
                    if progress_callback:
                        progress_info = {
                            'step': node,
                            'completed_steps': state.get('completed_steps', []),
                            'current_step': state.get('current_step', node),
                            'findings_count': len(state.get('findings', [])),
                            'literature_count': len(state.get('literature_references', [])),
                            'has_heatmap': bool(state.get('heatmap_data', {}).get('overlay')),
                            'quality_score': state.get('quality_score', 0)
                        }
                        await progress_callback(progress_info)
            
            # Get final state
            final_state = await app.aget_state(config)
            final_values = final_state.values
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            final_values['processing_time'] = processing_time
            
            logger.info(f"Workflow completed in {processing_time:.2f} seconds")
            
            # Convert to regular dict for return
            result = dict(final_values)
            
            # Add workflow metadata
            result['workflow_metadata'] = {
                'version': '2.0',
                'engine': 'langgraph',
                'completed_at': datetime.now().isoformat(),
                'total_steps': len(result.get('completed_steps', [])),
                'success': result.get('error') is None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow error: {str(e)}")
            
            # Return error state
            return {
                'error': str(e),
                'case_id': case_id,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'completed_steps': initial_state.get('completed_steps', []),
                'workflow_metadata': {
                    'version': '2.0',
                    'engine': 'langgraph',
                    'completed_at': datetime.now().isoformat(),
                    'success': False,
                    'error_type': type(e).__name__
                }
            }
    
    def visualize_workflow(self) -> str:
        """Generate a visual representation of the workflow"""
        
        try:
            # Compile the workflow
            app = self.workflow.compile()
            
            # Get the graph visualization
            return app.get_graph().draw_mermaid()
            
        except Exception as e:
            logger.error(f"Error visualizing workflow: {e}")
            return "Unable to generate workflow visualization"