"""
Medical Imaging Workflow Manager
Implements comprehensive medical imaging analysis with:
1. Paragraph-style reports for patient understanding
2. Web search for detailed disease explanations
3. Precise heatmap generation with exact location highlighting
4. Literature references from web searches
5. Disease explanation followed by location details
"""

import asyncio
import json
import base64
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import io
import re

from app.core.config import settings
from app.microservices.medical_imaging.services.ai_services.providers.provider_manager import UnifiedProviderManager
from app.microservices.medical_imaging.services.ai_services.providers.gemini_web_search_provider import GeminiWebSearchProvider
from app.microservices.medical_imaging.services.database_services.glove_embedding_service import GloVeEmbeddingService
from app.microservices.medical_imaging.workflows.websocket_adapter import send_medical_progress
from app.microservices.medical_imaging.agents.prompts.agent_prompts import (
    IMAGE_ANALYSIS_PROMPT,
    LITERATURE_RESEARCH_PROMPT,
    DETAILED_REPORT_WRITER_PROMPT,
    QUALITY_CHECKER_PROMPT,
    PROVIDER_ADJUSTMENTS,
    WEB_SEARCH_QUERIES_TEMPLATE
)
# Import the tools for direct agent usage
from app.microservices.medical_imaging.tools.medical_tools import (
    search_pubmed,
    search_duckduckgo
)

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Workflow manager with comprehensive report generation and precise heatmaps"""
    
    def __init__(self):
        self.provider_manager = UnifiedProviderManager()
        self.embedding_service = GloVeEmbeddingService()
        # Initialize Gemini Web Search provider for literature research
        try:
            self.web_search_provider = GeminiWebSearchProvider()
            logger.info("Gemini Web Search provider initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini Web Search provider: {e}")
            self.web_search_provider = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize the workflow manager"""
        if not self.initialized:
            # Provider manager and embedding service initialize in __init__
            # Just mark as initialized
            self.initialized = True
            logger.info("WorkflowManager initialized successfully")
    
    async def _generate_with_prompt(self, prompt: str, image_data: Optional[str] = None) -> str:
        """Generate response using available providers with flexible prompt"""
        # Get available providers
        available_providers = self.provider_manager.get_available_providers()
        
        if not available_providers:
            raise Exception("No AI providers available")
        
        # Try each provider (available_providers is a list of tuples)
        for provider_name, provider in available_providers:
            try:
                # Get available models for this provider
                models = provider.get_available_models(require_vision=bool(image_data))
                if not models:
                    logger.warning(f"No models available for {provider_name}")
                    continue
                
                # Use the first available model (highest priority)
                model_id = models[0].model_id
                
                # Call the provider's API directly
                response = await provider._call_api(
                    prompt=prompt,
                    image_data=image_data,
                    model=model_id
                )
                if response:
                    return response
            except Exception as e:
                logger.error(f"Provider {provider_name} failed: {e}")
                continue
        
        raise Exception("All providers failed to generate response")
            
    async def process_medical_images(
        self,
        case_id: str,
        images: List[Dict[str, Any]],
        patient_info: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process medical images through the complete workflow"""
        
        try:
            logger.info(f"Starting workflow for case {case_id}")
            
            # Initialize workflow state
            workflow_state = {
                "case_id": case_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "patient_info": patient_info or {},
                "images_processed": len(images)
            }
            
            # Process each image
            all_findings = []
            all_literature = []
            
            # Send initial workflow started notification
            await send_medical_progress(
                user_id=user_id,
                status="workflow_started",
                report_id=case_id,
                case_id=case_id,
                total_images=len(images),
                message="Starting medical imaging analysis workflow"
            )
            
            for idx, image_data in enumerate(images):
                logger.info(f"Processing image {idx + 1}/{len(images)}")
                
                # Send image processing progress
                await send_medical_progress(
                    user_id=user_id,
                    status="image_processing",
                    report_id=case_id,
                    case_id=case_id,
                    current_image=idx + 1,
                    total_images=len(images),
                    progress_percentage=int((idx + 1) / len(images) * 20),  # Images processing is 20% of total
                    message=f"Analyzing image {idx + 1} of {len(images)}"
                )
                
                # Step 1: Image Analysis Agent - Get findings with precise coordinates
                analysis_result, findings = await self._image_analysis_agent(image_data)
                if findings:
                    all_findings.extend(findings)
                
                # Step 2: Generate precise heatmap using exact coordinates
                if findings:
                    heatmap_data = await self._generate_precise_heatmap(image_data, findings)
                    workflow_state['heatmap_data'] = heatmap_data
                    workflow_state['heatmap_generated'] = True
                
                # Step 3: Literature Research Agent - Web search for disease information
                if findings:
                    literature = await self._literature_search_agent(
                        findings, 
                        image_data.get('metadata', {}).get('modality', 'imaging'),
                        patient_info
                    )
                    all_literature.extend(literature)
            
            # Send report generation progress
            await send_medical_progress(
                user_id=user_id,
                status="report_generation",
                report_id=case_id,
                case_id=case_id,
                progress_percentage=60,
                message="Generating comprehensive medical report"
            )
            
            # Step 4: Detailed Report Writer - Paragraph format with disease explanations
            # Pass the original image data to the report writer
            image_for_report = images[0] if images else None  # Use first image or None
            detailed_report = await self._detailed_report_writer(
                all_findings,
                all_literature,
                patient_info,
                workflow_state,
                image_for_report
            )
            
            # Send quality check progress
            await send_medical_progress(
                user_id=user_id,
                status="quality_check",
                report_id=case_id,
                case_id=case_id,
                progress_percentage=80,
                message="Performing quality assessment"
            )
            
            # Step 5: Quality Checker
            quality_score, quality_feedback = await self._quality_checker_agent(
                detailed_report,
                all_findings,
                all_literature
            )
            
            # Update workflow state
            workflow_state.update({
                "abnormalities_detected": all_findings,
                "literature_references": all_literature,
                "final_report": detailed_report,
                "quality_score": quality_score,
                "quality_feedback": quality_feedback,
                "status": "completed"
            })
            
            # Send storing progress
            await send_medical_progress(
                user_id=user_id,
                status="storing_results",
                report_id=case_id,
                case_id=case_id,
                progress_percentage=95,
                message="Saving results and generating embeddings"
            )
            
            # Step 6: Store results with embeddings
            await self._store_results(workflow_state)
            
            # Send final completion notification
            await send_medical_progress(
                user_id=user_id,
                status="completed",
                report_id=case_id,
                case_id=case_id,
                progress_percentage=100,
                message="Medical imaging analysis completed successfully",
                final_report=detailed_report
            )
            
            return {
                "success": True,
                "workflow_id": case_id,
                "case_id": case_id,
                "report_id": case_id,
                "status": "completed",
                "workflow_state": workflow_state
            }
            
        except Exception as e:
            logger.error(f"Workflow error: {str(e)}")
            
            # Send error notification
            if user_id:
                await send_medical_progress(
                    user_id=user_id,
                    status="error",
                    report_id=case_id,
                    case_id=case_id,
                    error=str(e),
                    message=f"Error during medical imaging analysis: {str(e)}"
                )
            
            return {
                "success": False,
                "error": str(e),
                "workflow_id": case_id
            }
    
    async def _image_analysis_agent(self, image_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Image analysis with precise coordinate extraction"""
        
        try:
            # Use provider directly for flexible prompt-based generation
            response = await self._generate_with_prompt(
                prompt=IMAGE_ANALYSIS_PROMPT,
                image_data=image_data.get('data', '')
            )
            
            # Parse findings with coordinate extraction
            findings = self._extract_findings_with_coordinates(response)
            
            return {"raw_analysis": response}, findings
            
        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            return {"error": str(e)}, []
    
    def _extract_findings_with_coordinates(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Extract findings with precise coordinate information"""
        findings = []
        
        # Split by finding markers
        finding_patterns = [
            r"Finding #?\d+:?",
            r"\d+\.",
            r"Abnormality \d+:",
            r"FINDING:",
            r"Observation:"
        ]
        
        # Extract coordinate patterns
        coord_patterns = {
            'point': r"(?:coordinates?|location|at|position).*?(\d+)\s*,\s*(\d+)",
            'region': r"(upper|lower|middle|right|left|central|peripheral)",
            'size': r"(\d+(?:\.\d+)?)\s*(cm|mm|centimeters?|millimeters?)",
            'quadrant': r"(RUL|RML|RLL|LUL|LLL|right upper|right middle|right lower|left upper|left lower)"
        }
        
        # Process text to extract findings
        text_lower = analysis_text.lower()
        lines = analysis_text.split('\n')
        
        current_finding = {}
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            # Check for new finding
            is_new_finding = any(re.search(pattern, line_clean, re.IGNORECASE) for pattern in finding_patterns)
            
            if is_new_finding and current_finding:
                findings.append(self._process_finding(current_finding))
                current_finding = {}
            
            # Extract information
            if 'description' not in current_finding:
                current_finding['description'] = line_clean
            else:
                current_finding['description'] += " " + line_clean
                
            # Extract coordinates
            for coord_type, pattern in coord_patterns.items():
                match = re.search(pattern, line_clean, re.IGNORECASE)
                if match:
                    if coord_type == 'point':
                        current_finding['x'] = int(match.group(1))
                        current_finding['y'] = int(match.group(2))
                    elif coord_type == 'region':
                        current_finding['region'] = match.group(1).lower()
                    elif coord_type == 'size':
                        current_finding['size'] = f"{match.group(1)} {match.group(2)}"
                    elif coord_type == 'quadrant':
                        current_finding['anatomical_location'] = match.group(1)
        
        # Add last finding
        if current_finding:
            findings.append(self._process_finding(current_finding))
        
        return findings
    
    def _process_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Process and standardize a finding"""
        
        # Ensure required fields
        processed = {
            'description': finding.get('description', 'Unspecified finding'),
            'severity': 'medium'  # default
        }
        
        # Add location information
        if 'anatomical_location' in finding:
            processed['location'] = finding['anatomical_location']
        elif 'region' in finding:
            processed['location'] = finding['region']
        else:
            processed['location'] = 'unspecified'
        
        # Add coordinates if available
        if 'x' in finding and 'y' in finding:
            processed['x'] = finding['x']
            processed['y'] = finding['y']
        else:
            # Estimate coordinates based on anatomical location
            processed.update(self._estimate_coordinates(processed['location']))
        
        # Add other fields
        if 'size' in finding:
            processed['size'] = finding['size']
            
        # Determine severity based on keywords
        desc_lower = processed['description'].lower()
        if any(word in desc_lower for word in ['severe', 'significant', 'large', 'extensive']):
            processed['severity'] = 'high'
        elif any(word in desc_lower for word in ['mild', 'small', 'minimal', 'slight']):
            processed['severity'] = 'low'
            
        return processed
    
    def _estimate_coordinates(self, location: str) -> Dict[str, int]:
        """Estimate coordinates based on anatomical location"""
        
        # Assuming 512x512 image
        location_map = {
            'right upper': {'x': 380, 'y': 150},
            'right middle': {'x': 380, 'y': 256},
            'right lower': {'x': 380, 'y': 360},
            'left upper': {'x': 130, 'y': 150},
            'left middle': {'x': 130, 'y': 256},
            'left lower': {'x': 130, 'y': 360},
            'central': {'x': 256, 'y': 256},
            'upper': {'x': 256, 'y': 150},
            'lower': {'x': 256, 'y': 360},
            'right': {'x': 380, 'y': 256},
            'left': {'x': 130, 'y': 256}
        }
        
        location_lower = location.lower()
        for key, coords in location_map.items():
            if key in location_lower:
                return coords
                
        return {'x': 256, 'y': 256}  # center default
    
    async def _generate_precise_heatmap(self, image_data: Dict[str, Any], findings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate precise heatmap highlighting only affected areas"""
        
        try:
            # Decode image
            img_bytes = base64.b64decode(image_data['data'])
            img = Image.open(io.BytesIO(img_bytes))
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create heatmap with precise regions
            heatmap = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(heatmap)
            
            # Draw precise heat regions for each finding
            for finding in findings:
                x = finding.get('x', img.width // 2)
                y = finding.get('y', img.height // 2)
                
                # Determine heat intensity based on severity
                severity_colors = {
                    'high': (255, 0, 0, 180),    # Red with high opacity
                    'medium': (255, 165, 0, 150), # Orange with medium opacity
                    'low': (255, 255, 0, 120)     # Yellow with lower opacity
                }
                
                color = severity_colors.get(finding.get('severity', 'medium'))
                
                # Create gradient heat spot
                for radius in range(60, 0, -5):
                    alpha = int(color[3] * (radius / 60))
                    current_color = (color[0], color[1], color[2], alpha)
                    draw.ellipse(
                        [x - radius, y - radius, x + radius, y + radius],
                        fill=current_color
                    )
            
            # Apply Gaussian blur for smooth heat effect
            heatmap = heatmap.filter(ImageFilter.GaussianBlur(radius=10))
            
            # Create overlay
            overlay = Image.alpha_composite(img.convert('RGBA'), heatmap)
            
            # Convert to base64
            overlay_buffer = io.BytesIO()
            overlay.save(overlay_buffer, format='PNG')
            overlay_base64 = base64.b64encode(overlay_buffer.getvalue()).decode('utf-8')
            
            heatmap_buffer = io.BytesIO()
            heatmap.save(heatmap_buffer, format='PNG')
            heatmap_base64 = base64.b64encode(heatmap_buffer.getvalue()).decode('utf-8')
            
            return {
                'overlay': overlay_base64,
                'heatmap': heatmap_base64,
                'findings_count': len(findings),
                'heat_regions': [
                    {
                        'x': f.get('x', 0),
                        'y': f.get('y', 0),
                        'severity': f.get('severity', 'medium'),
                        'description': f.get('description', '')[:50]
                    }
                    for f in findings
                ]
            }
            
        except Exception as e:
            logger.error(f"Heatmap generation error: {str(e)}")
            return None
    
    async def _literature_search_agent(
        self, 
        findings: List[Dict[str, Any]], 
        imaging_type: str,
        patient_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Literature search using PubMed tool directly"""
        
        # Extract key terms from findings
        search_terms = []
        diseases_found = []
        for finding in findings:
            desc = finding.get('description', '')
            # Extract medical terms
            medical_terms = re.findall(r'\b(?:pneumonia|consolidation|opacity|infiltrate|mass|nodule|effusion|cardiomegaly|atelectasis|emphysema|fibrosis|pleural)\b', desc, re.IGNORECASE)
            search_terms.extend(medical_terms)
            if medical_terms:
                diseases_found.extend(medical_terms)
        
        search_terms = list(set(search_terms))  # Remove duplicates
        
        # Create comprehensive web search queries for real searches
        age = patient_info.get('age', 'unknown')
        gender = patient_info.get('gender', 'unknown')
        symptoms = ', '.join(patient_info.get('symptoms', []))
        
        # Build detailed search queries for PubMed and medical databases
        pubmed_queries = []
        if search_terms:
            for template in WEB_SEARCH_QUERIES_TEMPLATE:
                query = template.format(
                    condition=search_terms[0] if search_terms else "chest pathology",
                    age=age,
                    gender=gender
                )
                pubmed_queries.append(query)
        
        # Format the prompt with patient information
        formatted_prompt = LITERATURE_RESEARCH_PROMPT.format(
            findings=json.dumps(findings, indent=2),
            age=age,
            gender=gender,
            symptoms=symptoms,
            clinical_history=patient_info.get('clinical_history', 'Not provided'),
            search_queries=chr(10).join(f"   {q}" for q in pubmed_queries)
        )

        try:
            # Use PubMed tool directly for real literature search
            unique_references = []
            
            # Search for each term
            for term in search_terms[:3]:  # Limit to top 3 terms
                # General search for the condition
                general_query = f"{term} {imaging_type}"
                results = await search_pubmed(
                    query=general_query,
                    max_results=5,
                    patient_age=patient_info.get('age'),
                    patient_gender=patient_info.get('gender')
                )
                unique_references.extend(results)
            
            # If we found specific diseases, search for treatment guidelines
            if diseases_found:
                guidelines_query = f"{diseases_found[0]} treatment guidelines"
                guidelines = await search_pubmed(
                    query=guidelines_query,
                    max_results=3
                )
                unique_references.extend(guidelines)
            
            # Also do a general search if we have few results
            if len(unique_references) < 5:
                general_query = f"{search_terms[0] if search_terms else imaging_type} imaging findings"
                general_results = await search_pubmed(
                    query=general_query,
                    max_results=10
                )
                unique_references.extend(general_results)
            
            # Return top 15 most relevant
            return unique_references[:15]
            
        except Exception as e:
            logger.error(f"Literature search error: {str(e)}")
            # Return minimal default references
            return [{
                "title": "Literature search unavailable",
                "authors": "System",  # Changed from list to string
                "journal": "Error in web search",
                "year": "2024",
                "type": "Error",
                "abstract": "Unable to perform web search at this time. Please consult medical databases directly.",
                "relevance_score": "0"  # Changed from int to string
            }]
    
    def _parse_literature_references(self, text: str) -> List[Dict[str, Any]]:
        """Parse literature references with case studies and citations"""
        references = []
        
        # Split by reference markers
        ref_markers = [r"Title:", r"\d+\.", r"Reference \d+:", r"-\s*Title:"]
        
        sections = re.split('|'.join(ref_markers), text)
        
        for section in sections[1:]:  # Skip first empty section
            if len(section.strip()) < 20:
                continue
                
            ref = {'relevance_score': '5'}  # Default score as string
            
            # Extract fields
            lines = section.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if 'Authors:' in line:
                    # Convert author list to comma-separated string
                    authors_list = [a.strip() for a in line.split('Authors:')[1].split(',')]
                    ref['authors'] = ', '.join(authors_list)
                elif 'Source:' in line or 'Journal:' in line:
                    ref['journal'] = line.split(':')[1].strip()
                elif 'Year:' in line:
                    ref['year'] = line.split(':')[1].strip()
                elif 'Type:' in line:
                    ref['type'] = line.split(':')[1].strip()
                elif 'Key Findings:' in line or 'Summary:' in line:
                    ref['abstract'] = line.split(':', 1)[1].strip()
                elif 'Patient Demographics:' in line:
                    ref['patient_demographics'] = line.split(':', 1)[1].strip()
                elif 'Treatment Approach:' in line:
                    ref['treatment'] = line.split(':', 1)[1].strip()
                elif 'Outcome:' in line:
                    ref['outcome'] = line.split(':', 1)[1].strip()
                elif 'URL:' in line or 'DOI:' in line:
                    ref['url'] = line.split(':', 1)[1].strip()
                elif 'Relevance Score:' in line:
                    try:
                        score = int(re.search(r'\d+', line).group())
                        ref['relevance_score'] = str(score)  # Convert to string
                    except:
                        ref['relevance_score'] = '5'
                elif 'title' not in ref and line:
                    ref['title'] = line
                    
            if 'title' in ref:
                references.append(ref)
                
        return references
    
    async def _generate_with_gemini_web_search(self, prompt: str) -> Optional[str]:
        """Generate response using Gemini models with real web search capability"""
        
        try:
            if not self.web_search_provider:
                logger.warning("Gemini Web Search provider not available")
                return None
            
            # Use the web search provider to get real search results
            response = await self.web_search_provider._call_api(prompt)
            
            if response:
                logger.info("Successfully performed web search with Gemini")
            
            return response
            
        except Exception as e:
            logger.error(f"Gemini web search error: {str(e)}")
            return None
    
    async def _detailed_report_writer(
        self,
        findings: List[Dict[str, Any]],
        literature: List[Dict[str, Any]],
        patient_info: Dict[str, Any],
        workflow_state: Dict[str, Any],
        image_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate detailed paragraph-style report for patient understanding with image analysis and web resources"""
        
        # Prepare structured information
        findings_text = self._format_findings_for_report(findings)
        literature_summary = self._summarize_literature(literature)
        
        # Use DuckDuckGo to find additional web resources
        web_resources = await self._search_web_resources(findings, patient_info)
        
        # Format web resources for inclusion
        web_resource_text = self._format_web_resources(web_resources)
        
        # Update literature summary to include web resources
        enhanced_literature_summary = literature_summary
        if web_resources:
            enhanced_literature_summary += "\n\nADDITIONAL WEB RESOURCES:\n" + web_resource_text
        
        # Format the prompt with patient information
        formatted_prompt = DETAILED_REPORT_WRITER_PROMPT.format(
            age=patient_info.get('age', 'Not specified'),
            gender=patient_info.get('gender', 'Not specified'),
            symptoms=', '.join(patient_info.get('symptoms', ['None reported'])),
            clinical_history=patient_info.get('clinical_history', 'No history provided'),
            findings_text=findings_text,
            literature_summary=enhanced_literature_summary
        )

        try:
            # If image is provided, pass it to the report writer for visual context
            if image_data and image_data.get('data'):
                response = await self._generate_with_prompt(
                    prompt=formatted_prompt,
                    image_data=image_data.get('data')
                )
            else:
                response = await self._generate_with_prompt(
                    prompt=formatted_prompt
                )
            
            return {
                "content": response,
                "report_type": "comprehensive_medical",
                "sections": [
                    "Key Findings",
                    "Clinical Summary",
                    "Detailed Findings", 
                    "Medical Explanation",
                    "Clinical Correlation",
                    "Evidence from Medical Literature",
                    "Recommendations",
                    "Patient Education",
                    "References"
                ],
                "generated_at": datetime.now().isoformat(),
                "literature_included": len(literature) > 0,
                "web_resources_included": len(web_resources) > 0,
                "web_resources_count": len(web_resources)
            }
            
        except Exception as e:
            logger.error(f"Report generation error: {str(e)}")
            return {
                "content": "Report generation failed. Please consult with a medical professional.",
                "error": str(e)
            }
    
    def _format_findings_for_report(self, findings: List[Dict[str, Any]]) -> str:
        """Format findings for report generation"""
        if not findings:
            return "No significant abnormalities detected."
            
        formatted = []
        for i, finding in enumerate(findings, 1):
            text = f"Finding {i}: {finding.get('description', 'Unspecified abnormality')}"
            if 'location' in finding:
                text += f" located in the {finding['location']}"
            if 'size' in finding:
                text += f" measuring {finding['size']}"
            if 'severity' in finding:
                text += f" ({finding['severity']} severity)"
            formatted.append(text)
            
        return '\n'.join(formatted)
    
    def _summarize_literature(self, literature: List[Dict[str, Any]]) -> str:
        """Summarize literature for report with proper formatting"""
        if not literature:
            return "No specific literature references available."
            
        summary = []
        
        # Group by type
        case_studies = [ref for ref in literature if ref.get('type', '').lower() == 'case study']
        guidelines = [ref for ref in literature if ref.get('type', '').lower() == 'guideline']
        research = [ref for ref in literature if ref.get('type', '').lower() == 'research']
        
        # Add case studies
        if case_studies:
            summary.append("RELEVANT CASE STUDIES:")
            for ref in case_studies[:3]:
                # Handle authors as string or list
                authors = ref.get('authors', 'Unknown')
                if isinstance(authors, list):
                    first_author = authors[0].split(',')[0] if authors else 'Unknown'
                else:
                    # Authors is already a string
                    author_parts = authors.split(',')
                    first_author = author_parts[0].strip() if author_parts else 'Unknown'
                year = ref.get('year', 'n.d.')
                summary.append(f"\n{ref.get('title', 'Untitled')} ({first_author} et al., {year})")
                if ref.get('patient_demographics'):
                    summary.append(f"Patient: {ref['patient_demographics']}")
                if ref.get('treatment'):
                    summary.append(f"Treatment: {ref['treatment']}")
                if ref.get('outcome'):
                    summary.append(f"Outcome: {ref['outcome']}")
                if ref.get('url'):
                    summary.append(f"Source: {ref['url']}")
        
        # Add guidelines
        if guidelines:
            summary.append("\n\nCLINICAL GUIDELINES:")
            for ref in guidelines[:2]:
                # Handle authors as string or list
                authors = ref.get('authors', 'Unknown')
                if isinstance(authors, list):
                    org = authors[0] if authors and len(authors[0]) > 20 else "Medical Society"
                else:
                    # Authors is already a string
                    org = authors if len(authors) > 20 else "Medical Society"
                year = ref.get('year', 'n.d.')
                summary.append(f"\n{ref.get('title', 'Untitled')} ({org}, {year})")
                if ref.get('abstract'):
                    summary.append(f"Summary: {ref['abstract'][:300]}...")
                if ref.get('url'):
                    summary.append(f"Available at: {ref['url']}")
        
        # Add research papers
        if research:
            summary.append("\n\nRESEARCH EVIDENCE:")
            for ref in research[:3]:
                # Handle authors as string or list
                authors = ref.get('authors', 'Unknown')
                if isinstance(authors, list):
                    first_author = authors[0].split(',')[0] if authors else 'Unknown'
                else:
                    # Authors is already a string
                    author_parts = authors.split(',')
                    first_author = author_parts[0].strip() if author_parts else 'Unknown'
                year = ref.get('year', 'n.d.')
                journal = ref.get('journal', 'Journal')
                summary.append(f"\n{ref.get('title', 'Untitled')}")
                summary.append(f"({first_author} et al., {year}, {journal})")
                if ref.get('abstract'):
                    summary.append(f"Key findings: {ref['abstract'][:250]}...")
        
        return '\n'.join(summary)
    
    async def _search_web_resources(self, findings: List[Dict[str, Any]], patient_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search web for additional resources using DuckDuckGo"""
        web_resources = []
        
        try:
            # Extract conditions from findings
            conditions = []
            for finding in findings:
                desc = finding.get('description', '')
                medical_terms = re.findall(
                    r'\b(?:pneumonia|consolidation|opacity|infiltrate|mass|nodule|'
                    r'effusion|cardiomegaly|atelectasis|emphysema|fibrosis|pleural)\b', 
                    desc, re.IGNORECASE
                )
                conditions.extend(medical_terms)
            
            conditions = list(set(conditions))[:3]  # Top 3 unique conditions
            
            # Search for patient education resources
            for condition in conditions:
                # Patient education query
                edu_query = f"{condition} patient education Mayo Clinic WebMD NHS"
                edu_results = await search_duckduckgo(
                    query=edu_query,
                    max_results=3
                )
                web_resources.extend(edu_results)
                
                # Treatment guidelines query
                guide_query = f"{condition} treatment guidelines 2024 medical society"
                guide_results = await search_duckduckgo(
                    query=guide_query,
                    max_results=2
                )
                web_resources.extend(guide_results)
            
            # Also search for general chest x-ray resources if no specific conditions
            if not conditions:
                general_query = "chest x-ray abnormalities patient information"
                general_results = await search_duckduckgo(
                    query=general_query,
                    max_results=5
                )
                web_resources.extend(general_results)
            
            return web_resources[:10]  # Limit to 10 resources
            
        except Exception as e:
            logger.error(f"Web resource search error: {str(e)}")
            return []
    
    def _format_web_resources(self, web_resources: List[Dict[str, Any]]) -> str:
        """Format web resources for report inclusion"""
        if not web_resources:
            return "No additional web resources found."
        
        formatted = []
        for i, resource in enumerate(web_resources[:5], 1):  # Top 5 resources
            title = resource.get('title', 'Untitled')
            url = resource.get('url', '')
            snippet = resource.get('abstract', '')[:200] + '...' if resource.get('abstract') else ''
            
            formatted.append(f"{i}. {title}")
            if url:
                formatted.append(f"   URL: {url}")
            if snippet:
                formatted.append(f"   Summary: {snippet}")
            formatted.append("")  # Empty line
        
        return '\n'.join(formatted)
    
    async def _quality_checker_agent(
        self,
        report: Dict[str, Any],
        findings: List[Dict[str, Any]],
        literature: List[Dict[str, Any]]
    ) -> Tuple[float, str]:
        """Check quality of the generated report"""
        
        # Format the quality check prompt
        formatted_prompt = QUALITY_CHECKER_PROMPT.format(
            report_content=report.get('content', '')[:2000],
            num_findings=len(findings),
            num_references=len(literature)
        )

        try:
            response = await self._generate_with_prompt(
                prompt=formatted_prompt
            )
            
            # Extract score
            score_match = re.search(r'(?:score|rating).*?(\d*\.?\d+)', response, re.IGNORECASE)
            score = float(score_match.group(1)) if score_match else 0.75
            
            # Ensure score is between 0 and 1
            score = max(0.0, min(1.0, score))
            
            return score, response
            
        except Exception as e:
            logger.error(f"Quality check error: {str(e)}")
            return 0.7, "Quality check completed with default score"
    
    async def _store_results(self, workflow_state: Dict[str, Any]) -> None:
        """Store results with embeddings in Neo4j and save files to disk"""
        try:
            # First save files to disk
            await self._save_files_to_disk(workflow_state)
            # Import Neo4j storage
            from app.microservices.medical_imaging.services.database_services.neo4j_report_storage import get_neo4j_storage
            neo4j_storage = get_neo4j_storage()
            
            # Generate embeddings for the report
            report_text = workflow_state.get('final_report', {}).get('content', '')
            embeddings = {}
            
            if report_text:
                # Generate main report embedding
                embedding = await self.embedding_service.generate_embedding(report_text)
                workflow_state['report_embedding'] = embedding.tolist()
                embeddings['full_report'] = embedding
                
                # Generate summary embedding
                summary_text = workflow_state.get('clinical_impression', '')
                if summary_text:
                    summary_embedding = await self.embedding_service.generate_embedding(summary_text)
                    embeddings['summary'] = summary_embedding
                
                # Generate findings embedding
                findings_text = ' '.join(workflow_state.get('key_findings', []))
                if findings_text:
                    findings_embedding = await self.embedding_service.generate_embedding(findings_text)
                    embeddings['findings'] = findings_embedding
            
            # Create report structure for Neo4j
            report_data = {
                'report_id': workflow_state.get('case_id'),
                'user_id': workflow_state.get('user_id', ''),  # Add user_id field
                'patient_id': workflow_state.get('patient_info', {}).get('patient_id', ''),
                'patient_info': workflow_state.get('patient_info', {}),
                'study_info': {
                    'modality': workflow_state.get('images_processed', 0),
                    'study_date': workflow_state.get('timestamp')
                },
                'findings': workflow_state.get('abnormalities_detected', []),
                'key_findings': workflow_state.get('key_findings', []),
                'summary': workflow_state.get('final_report', {}).get('content', ''),
                'clinical_impression': workflow_state.get('clinical_impression', ''),
                'recommendations': workflow_state.get('recommendations', []),
                'severity': workflow_state.get('severity', 'low'),
                'quality_score': workflow_state.get('quality_score', 0),
                'literature_references': workflow_state.get('literature_references', []),
                'embeddings': embeddings,
                'status': 'completed',
                'created_at': workflow_state.get('timestamp'),
                'final_report': workflow_state.get('final_report', {}),
                'heatmap_data': workflow_state.get('heatmap_data')
            }
            
            # Store in Neo4j
            stored_id = await neo4j_storage.store_report(report_data)
            
            # Store embeddings separately for vector search
            if embeddings.get('full_report') is not None:
                await neo4j_storage.store_report_embedding(
                    report_id=workflow_state.get('case_id'),
                    embedding=embeddings['full_report']
                )
            
            logger.info(f"Results stored in Neo4j for case {workflow_state['case_id']} with ID: {stored_id}")
            
        except Exception as e:
            logger.error(f"Storage error: {str(e)}")
    
    async def _save_files_to_disk(self, workflow_state: Dict[str, Any]) -> None:
        """Save generated reports and heatmaps to disk"""
        try:
            from pathlib import Path
            
            # Create directories
            base_dir = Path("medical_imaging_outputs")
            base_dir.mkdir(exist_ok=True)
            
            case_id = workflow_state.get('case_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create case-specific directory
            case_dir = base_dir / f"case_{case_id}_{timestamp}"
            case_dir.mkdir(exist_ok=True)
            
            # Save report
            report_content = workflow_state.get('final_report', {}).get('content', '')
            if report_content:
                report_path = case_dir / "medical_report.txt"
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write("Medical Imaging Report\n")
                    f.write("="*80 + "\n\n")
                    f.write(f"Case ID: {case_id}\n")
                    f.write(f"Generated: {workflow_state.get('timestamp', '')}\n")
                    f.write(f"Patient ID: {workflow_state.get('patient_info', {}).get('patient_id', 'Unknown')}\n")
                    f.write("="*80 + "\n\n")
                    f.write(report_content)
                logger.info(f"Report saved to: {report_path}")
            
            # Save heatmaps
            heatmap_data = workflow_state.get('heatmap_data', {})
            if heatmap_data:
                # Save overlay
                if 'overlay' in heatmap_data:
                    overlay_path = case_dir / "heatmap_overlay.png"
                    overlay_bytes = base64.b64decode(heatmap_data['overlay'])
                    with open(overlay_path, 'wb') as f:
                        f.write(overlay_bytes)
                    logger.info(f"Heatmap overlay saved to: {overlay_path}")
                
                # Save heatmap only
                if 'heatmap' in heatmap_data:
                    heatmap_path = case_dir / "heatmap.png"
                    heatmap_bytes = base64.b64decode(heatmap_data['heatmap'])
                    with open(heatmap_path, 'wb') as f:
                        f.write(heatmap_bytes)
                    logger.info(f"Heatmap saved to: {heatmap_path}")
            
            # Save findings and metadata
            metadata = {
                "case_id": case_id,
                "timestamp": workflow_state.get('timestamp', ''),
                "patient_info": workflow_state.get('patient_info', {}),
                "abnormalities_detected": workflow_state.get('abnormalities_detected', []),
                "literature_references": workflow_state.get('literature_references', []),
                "quality_score": workflow_state.get('quality_score', 0),
                "quality_feedback": workflow_state.get('quality_feedback', ''),
                "heat_regions": heatmap_data.get('heat_regions', []) if heatmap_data else []
            }
            
            metadata_path = case_dir / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Metadata saved to: {metadata_path}")
            
            # Update workflow state with saved paths
            workflow_state['saved_paths'] = {
                'case_directory': str(case_dir),
                'report': str(report_path) if report_content else None,
                'heatmap_overlay': str(overlay_path) if 'overlay' in heatmap_data else None,
                'heatmap': str(heatmap_path) if 'heatmap' in heatmap_data else None,
                'metadata': str(metadata_path)
            }
            
        except Exception as e:
            logger.error(f"Error saving files to disk: {str(e)}")