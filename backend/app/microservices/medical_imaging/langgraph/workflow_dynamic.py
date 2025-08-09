"""
Dynamic LangGraph Medical Imaging Workflow
Uses provider manager for automatic LLM selection and agent creation
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from .state import MedicalImagingState
from .agents import (
    create_gemini_agent, invoke_gemini_agent,
    create_groq_agent, invoke_groq_agent,
    create_openrouter_agent, invoke_openrouter_agent
)
from .tools_refactored import generate_heatmap, search_pubmed, search_web
from .prompts import (
    IMAGE_ANALYSIS_SYSTEM_PROMPT,
    LITERATURE_SEARCH_SYSTEM_PROMPT,
    REPORT_WRITER_SYSTEM_PROMPT,
    QUALITY_CHECKER_SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)


class DynamicMedicalImagingWorkflow:
    """Dynamic workflow that adapts to available providers"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _create_agent_for_step(self, step: str, tools: List[Any]) -> Any:
        """Create appropriate agent based on available provider"""
        
        # Get available provider
        provider_info = self.provider_manager.get_next_available_provider()
        if not provider_info:
            raise Exception("No providers available")
        
        provider_type = provider_info['type']
        model_id = provider_info['model_id']
        api_key = provider_info['api_key']
        
        # Get appropriate system prompt
        prompt_map = {
            'image_analysis': IMAGE_ANALYSIS_SYSTEM_PROMPT,
            'literature_search': LITERATURE_SEARCH_SYSTEM_PROMPT,
            'report_generation': REPORT_WRITER_SYSTEM_PROMPT,
            'quality_check': QUALITY_CHECKER_SYSTEM_PROMPT
        }
        
        system_prompt = prompt_map.get(step, "You are a helpful medical AI assistant.")
        
        # Create agent based on provider type
        if provider_type == 'gemini':
            return create_gemini_agent(
                model_id=model_id,
                api_key=api_key,
                tools=tools,
                system_prompt=system_prompt
            )
        elif provider_type == 'groq':
            return create_groq_agent(
                model_id=model_id,
                api_key=api_key,
                tools=tools,
                system_prompt=system_prompt
            )
        elif provider_type == 'openrouter':
            return create_openrouter_agent(
                model_id=model_id,
                api_key=api_key,
                tools=tools,
                system_prompt=system_prompt
            )
        else:
            raise Exception(f"Unknown provider type: {provider_type}")
    
    async def image_analysis_node(self, state: MedicalImagingState) -> MedicalImagingState:
        """Image analysis with heatmap generation"""
        logger.info("Starting image analysis node")
        
        try:
            state['current_step'] = 'image_analysis'
            
            # Create agent with heatmap tool
            agent = self._create_agent_for_step('image_analysis', [generate_heatmap])
            
            # Prepare message for agent
            image_data = state.get('image_data', '')
            patient_info = state.get('patient_info', {})
            
            message = f"""Please analyze this medical image and identify all findings.
            
Patient Information:
- Age: {patient_info.get('age', 'Unknown')}
- Gender: {patient_info.get('gender', 'Unknown')}
- Symptoms: {', '.join(patient_info.get('symptoms', []))}
- Clinical History: {patient_info.get('clinical_history', 'Not provided')}

Analyze the image thoroughly and:
1. Identify all abnormalities and findings
2. Provide precise locations (coordinates or regions)
3. Assess severity of each finding
4. Generate a heatmap using the generate_heatmap tool with your findings

The image data is already available in the state."""
            
            state['messages'] = [{"role": "user", "content": message}]
            
            # Invoke agent
            if hasattr(agent, '__name__') and 'gemini' in agent.__name__:
                state = await invoke_gemini_agent(agent, state)
            elif hasattr(agent, '__name__') and 'groq' in agent.__name__:
                state = await invoke_groq_agent(agent, state)
            else:
                state = await invoke_openrouter_agent(agent, state)
            
            # Mark step complete
            state['completed_steps'].append('image_analysis')
            
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            state['error'] = str(e)
        
        return state
    
    async def literature_search_node(self, state: MedicalImagingState) -> MedicalImagingState:
        """Literature search using PubMed"""
        logger.info("Starting literature search node")
        
        try:
            state['current_step'] = 'literature_search'
            
            # Create agent with PubMed tool
            agent = self._create_agent_for_step('literature_search', [search_pubmed])
            
            # Prepare message for agent
            findings = state.get('findings', [])
            patient_info = state.get('patient_info', {})
            
            findings_summary = "\n".join([
                f"- {f.get('description', '')} (Severity: {f.get('severity', 'unknown')})"
                for f in findings[:5]
            ])
            
            message = f"""Based on the following imaging findings, search for relevant medical literature:

Findings:
{findings_summary}

Patient Demographics:
- Age: {patient_info.get('age', 'Unknown')}
- Gender: {patient_info.get('gender', 'Unknown')}

Use the search_pubmed tool to find:
1. Recent clinical guidelines for these conditions
2. Similar case studies
3. Treatment recommendations
4. Diagnostic criteria

Focus on high-quality, peer-reviewed sources from the last 5 years."""
            
            state['messages'] = [{"role": "user", "content": message}]
            
            # Invoke agent
            if hasattr(agent, '__name__') and 'gemini' in agent.__name__:
                state = await invoke_gemini_agent(agent, state)
            elif hasattr(agent, '__name__') and 'groq' in agent.__name__:
                state = await invoke_groq_agent(agent, state)
            else:
                state = await invoke_openrouter_agent(agent, state)
            
            # Mark step complete
            state['completed_steps'].append('literature_search')
            
        except Exception as e:
            logger.error(f"Literature search error: {e}")
            state['error'] = str(e)
        
        return state
    
    async def report_generation_node(self, state: MedicalImagingState) -> MedicalImagingState:
        """Generate detailed medical report"""
        logger.info("Starting report generation node")
        
        try:
            state['current_step'] = 'report_generation'
            
            # Create agent with web search tool
            agent = self._create_agent_for_step('report_generation', [search_web])
            
            # Prepare comprehensive context
            findings = state.get('findings', [])
            literature = state.get('literature_references', [])
            patient_info = state.get('patient_info', {})
            
            findings_text = "\n".join([
                f"{i+1}. {f.get('description', '')} - Location: {f.get('location', 'unspecified')}, Severity: {f.get('severity', 'moderate')}"
                for i, f in enumerate(findings)
            ])
            
            literature_text = "\n".join([
                f"- {ref.get('title', '')} ({ref.get('year', '')})"
                for ref in literature[:5]
            ])
            
            message = f"""Generate a comprehensive medical report based on the following information:

PATIENT INFORMATION:
- Age: {patient_info.get('age', 'Unknown')}
- Gender: {patient_info.get('gender', 'Unknown')}
- Symptoms: {', '.join(patient_info.get('symptoms', []))}
- Clinical History: {patient_info.get('clinical_history', 'Not provided')}

IMAGING FINDINGS:
{findings_text}

LITERATURE REFERENCES:
{literature_text}

Create a detailed report following the standard structure. If you need additional case studies or recent guidelines, use the search_web tool to find more information.

The report should be comprehensive, evidence-based, and include clear recommendations for patient management."""
            
            state['messages'] = [{"role": "user", "content": message}]
            
            # Invoke agent
            if hasattr(agent, '__name__') and 'gemini' in agent.__name__:
                state = await invoke_gemini_agent(agent, state)
            elif hasattr(agent, '__name__') and 'groq' in agent.__name__:
                state = await invoke_groq_agent(agent, state)
            else:
                state = await invoke_openrouter_agent(agent, state)
            
            # Extract report from messages
            if state.get('messages'):
                last_message = state['messages'][-1]
                if last_message.get('role') == 'assistant':
                    state['detailed_report'] = {
                        'content': last_message.get('content', ''),
                        'generated_at': datetime.now().isoformat()
                    }
            
            # Mark step complete
            state['completed_steps'].append('report_generation')
            
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            state['error'] = str(e)
        
        return state
    
    async def quality_check_node(self, state: MedicalImagingState) -> MedicalImagingState:
        """Quality check the generated report"""
        logger.info("Starting quality check node")
        
        try:
            state['current_step'] = 'quality_check'
            
            # Create agent (no tools needed for quality check)
            agent = self._create_agent_for_step('quality_check', [])
            
            # Prepare quality check request
            report = state.get('detailed_report', {})
            findings = state.get('findings', [])
            
            message = f"""Please review the following medical report for quality and accuracy:

REPORT CONTENT:
{report.get('content', 'No report generated')}

ORIGINAL FINDINGS COUNT: {len(findings)}

Assess the report based on:
1. Accuracy - findings correctly represented
2. Completeness - all significant findings addressed
3. Clinical appropriateness - recommendations are evidence-based
4. Clarity - clear and logical organization

Provide:
- Quality score (0.0 to 1.0)
- Strengths
- Areas for improvement
- Overall recommendation (Pass/Revise)"""
            
            state['messages'] = [{"role": "user", "content": message}]
            
            # Invoke agent
            if hasattr(agent, '__name__') and 'gemini' in agent.__name__:
                state = await invoke_gemini_agent(agent, state)
            elif hasattr(agent, '__name__') and 'groq' in agent.__name__:
                state = await invoke_groq_agent(agent, state)
            else:
                state = await invoke_openrouter_agent(agent, state)
            
            # Extract quality score (simplified - enhance with better parsing)
            if state.get('messages'):
                last_message = state['messages'][-1]
                content = last_message.get('content', '')
                
                # Simple score extraction
                import re
                score_match = re.search(r'(?:score|rating)[:\s]+(\d+\.?\d*)', content.lower())
                if score_match:
                    state['quality_score'] = float(score_match.group(1))
                else:
                    state['quality_score'] = 0.8  # Default
            
            # Mark step complete
            state['completed_steps'].append('quality_check')
            
        except Exception as e:
            logger.error(f"Quality check error: {e}")
            state['error'] = str(e)
            state['quality_score'] = 0.0
        
        return state
    
    def quality_check_router(self, state: MedicalImagingState) -> str:
        """Route based on quality score"""
        score = state.get('quality_score', 0.0)
        
        if score >= 0.7:
            return "pass"
        else:
            return "revise"
    
    async def final_processing_node(self, state: MedicalImagingState) -> MedicalImagingState:
        """Final processing and cleanup"""
        logger.info("Starting final processing")
        
        # Set completion status
        state['workflow_complete'] = True
        state['completed_at'] = datetime.now().isoformat()
        
        # Calculate total processing time
        if 'started_at' in state:
            start = datetime.fromisoformat(state['started_at'])
            end = datetime.now()
            state['processing_time'] = (end - start).total_seconds()
        
        return state
    
    def _build_workflow(self) -> StateGraph:
        """Build the workflow graph"""
        
        # Create graph
        workflow = StateGraph(MedicalImagingState)
        
        # Add nodes
        workflow.add_node("image_analysis", self.image_analysis_node)
        workflow.add_node("literature_search", self.literature_search_node)
        workflow.add_node("report_generation", self.report_generation_node)
        workflow.add_node("quality_check", self.quality_check_node)
        workflow.add_node("final_processing", self.final_processing_node)
        
        # Set entry point
        workflow.set_entry_point("image_analysis")
        
        # Add edges
        workflow.add_edge("image_analysis", "literature_search")
        workflow.add_edge("literature_search", "report_generation")
        
        # Add conditional edge for quality check
        workflow.add_conditional_edges(
            "quality_check",
            self.quality_check_router,
            {
                "pass": "final_processing",
                "revise": "report_generation"
            }
        )
        
        workflow.add_edge("report_generation", "quality_check")
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
        """Run the workflow"""
        
        logger.info(f"Starting dynamic workflow for case {case_id}")
        
        # Initialize state
        initial_state = {
            'image_data': image_data,
            'patient_info': patient_info,
            'case_id': case_id,
            'user_id': user_id,
            'started_at': datetime.now().isoformat(),
            'completed_steps': [],
            'messages': [],
            'findings': [],
            'literature_references': [],
            'detailed_report': {},
            'heatmap_data': {},
            'quality_score': 0.0,
            'workflow_complete': False
        }
        
        try:
            # Run workflow
            # Note: Running without checkpointer for now
            
            # Stream execution for progress updates
            final_state = initial_state
            async for output in self.app.astream(initial_state):
                # Report progress
                if progress_callback:
                    for node, state in output.items():
                        progress_info = {
                            'step': node,
                            'completed_steps': state.get('completed_steps', []),
                            'has_error': 'error' in state
                        }
                        await progress_callback(progress_info)
                        
                        # Update final state
                        final_state = state
            
            return dict(final_state)
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {
                'error': str(e),
                'completed_steps': initial_state.get('completed_steps', [])
            }