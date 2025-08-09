"""
Updated Agents for LangGraph Medical Imaging Workflow
Using intelligent tool selection
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .tools import PubMedSearchTool, GeminiWebSearchTool, HeatmapGenerationTool
from .agent_tools import IntelligentSearchManager
from .state import MedicalImagingState
from app.microservices.medical_imaging.agents.prompts.agent_prompts import (
    IMAGE_ANALYSIS_PROMPT,
    LITERATURE_RESEARCH_PROMPT,
    DETAILED_REPORT_WRITER_PROMPT,
    QUALITY_CHECKER_PROMPT
)

logger = logging.getLogger(__name__)


class ImageAnalysisAgent:
    """Agent for analyzing medical images and extracting findings"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
        self.pubmed_tool = PubMedSearchTool()
    
    async def analyze(self, state: MedicalImagingState) -> MedicalImagingState:
        """Analyze image and extract findings with coordinates"""
        
        try:
            logger.info("Starting image analysis")
            
            # Get image data
            image_data = state.get('image_data', '')
            
            # Analyze image using provider
            available_providers = self.provider_manager.get_available_providers()
            if not available_providers:
                raise Exception("No AI providers available")
            
            # Use first available provider
            provider_name, provider = available_providers[0]
            
            # Get models that support vision
            models = provider.get_available_models(require_vision=True)
            if not models:
                raise Exception(f"No vision models available for {provider_name}")
            
            # Generate analysis
            response = await provider._call_api(
                prompt=IMAGE_ANALYSIS_PROMPT,
                image_data=image_data,
                model=models[0].model_id
            )
            
            # Extract findings with coordinates
            findings = self._extract_findings_with_coordinates(response)
            
            # Update state
            state['image_analysis'] = {"raw_analysis": response}
            state['findings'] = findings
            state['completed_steps'].append('image_analysis')
            
            logger.info(f"Image analysis completed with {len(findings)} findings")
            
        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            state['error'] = f"Image analysis failed: {str(e)}"
        
        return state
    
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
        
        # Split text into sections
        sections = re.split('|'.join(finding_patterns), analysis_text)
        
        for section in sections[1:]:  # Skip first empty section
            if len(section.strip()) < 20:
                continue
            
            finding = {
                'description': '',
                'location': '',
                'severity': 'moderate',
                'coordinates': {},
                'confidence': 0.8
            }
            
            # Extract severity
            if 'severe' in section.lower() or 'critical' in section.lower():
                finding['severity'] = 'severe'
            elif 'mild' in section.lower() or 'minor' in section.lower():
                finding['severity'] = 'mild'
            
            # Extract coordinates
            for coord_type, pattern in coord_patterns.items():
                match = re.search(pattern, section, re.IGNORECASE)
                if match:
                    if coord_type == 'point':
                        finding['coordinates'] = {
                            'x': int(match.group(1)),
                            'y': int(match.group(2))
                        }
                    elif coord_type == 'region':
                        finding['coordinates']['region'] = match.group(1).lower()
                        finding['location'] = match.group(1)
                    elif coord_type == 'size':
                        finding['size'] = f"{match.group(1)} {match.group(2)}"
            
            # Extract description
            lines = section.strip().split('\n')
            if lines:
                finding['description'] = lines[0]
            
            # Extract coordinates from the text if not already found
            if not finding['coordinates']:
                # Try point coordinates
                point_match = re.search(coord_patterns['point'], section, re.IGNORECASE)
                if point_match:
                    finding['coordinates']['x'] = int(point_match.group(1))
                    finding['coordinates']['y'] = int(point_match.group(2))
                else:
                    # Try region
                    region_match = re.search(coord_patterns['region'], section, re.IGNORECASE)
                    if region_match:
                        finding['coordinates']['region'] = region_match.group(1).lower()
            
            # Extract size if present
            size_match = re.search(coord_patterns['size'], section, re.IGNORECASE)
            if size_match and 'size' not in finding:
                finding['size'] = f"{size_match.group(1)} {size_match.group(2)}"
            
            if finding['description']:
                findings.append(finding)
        
        return findings


class LiteratureSearchAgent:
    """Agent for searching medical literature using intelligent tool selection"""
    
    def __init__(self):
        # Use intelligent search manager that handles multiple tools
        self.search_manager = IntelligentSearchManager()
    
    async def search(self, state: MedicalImagingState) -> MedicalImagingState:
        """Search for relevant medical literature using all available tools"""
        
        try:
            logger.info("Starting intelligent literature search")
            
            findings = state.get('findings', [])
            patient_info = state.get('patient_info', {})
            
            # Extract conditions from findings
            conditions = self._extract_conditions_from_findings(findings)
            
            all_references = []
            
            # Let the intelligent search manager handle tool selection
            # It will use whatever tools are available and working
            for condition in conditions[:3]:  # Top 3 conditions
                query = f"{condition} chest x-ray diagnosis treatment guidelines"
                
                references = await self.search_manager.search_medical_literature(
                    query=query,
                    condition=condition,
                    patient_info=patient_info,
                    max_results=5
                )
                
                all_references.extend(references)
            
            # If no specific conditions, do general search
            if not conditions and findings:
                references = await self.search_manager.search_medical_literature(
                    query="chest x-ray abnormal findings diagnosis guidelines",
                    condition="chest abnormalities",
                    patient_info=patient_info,
                    max_results=10
                )
                all_references.extend(references)
            
            # Update state
            state['literature_references'] = all_references[:20]  # Top 20 references
            state['completed_steps'].append('literature_search')
            
            logger.info(f"Literature search completed with {len(all_references)} references")
            
        except Exception as e:
            logger.error(f"Literature search error: {str(e)}")
            state['error'] = f"Literature search failed: {str(e)}"
            state['literature_references'] = []
        
        return state
    
    def _extract_conditions_from_findings(self, findings: List[Dict]) -> List[str]:
        """Extract medical conditions from findings"""
        conditions = []
        
        # Common patterns to look for
        disease_patterns = [
            r'pneumonia', r'consolidation', r'infiltrate', r'opacity',
            r'effusion', r'nodule', r'mass', r'cardiomegaly',
            r'edema', r'atelectasis', r'emphysema', r'fibrosis',
            r'pneumothorax', r'hemothorax', r'tuberculosis'
        ]
        
        for finding in findings:
            desc = finding.get('description', '').lower()
            for pattern in disease_patterns:
                if pattern in desc and pattern not in conditions:
                    conditions.append(pattern)
        
        return conditions


class DetailedReportWriterAgent:
    """Agent for writing detailed medical reports with web search capability"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
        # Agent has access to multiple search tools
        self.search_manager = IntelligentSearchManager()
    
    async def write_report(self, state: MedicalImagingState) -> MedicalImagingState:
        """Generate detailed medical report"""
        
        try:
            logger.info("Starting detailed report generation")
            
            findings = state.get('findings', [])
            literature = state.get('literature_references', [])
            patient_info = state.get('patient_info', {})
            
            # Format findings for report
            findings_text = self._format_findings_for_report(findings)
            
            # Summarize literature
            literature_summary = self._summarize_literature(literature)
            
            # Check if we need additional web search
            if len(literature) < 5 or not any(ref.get('type') == 'Case Study' for ref in literature):
                logger.info("Agent deciding to search for additional case studies")
                
                # Extract main condition from findings
                main_condition = self._extract_main_condition(findings)
                
                if main_condition:
                    # Agent uses intelligent search manager
                    web_results = await self.search_manager.search_medical_literature(
                        query=f"{main_condition} case studies patient outcomes",
                        condition=main_condition,
                        patient_info=patient_info,
                        max_results=5
                    )
                    state['web_search_results'] = web_results
            
            # Format the prompt
            formatted_prompt = DETAILED_REPORT_WRITER_PROMPT.format(
                age=patient_info.get('age', 'Not specified'),
                gender=patient_info.get('gender', 'Not specified'),
                symptoms=', '.join(patient_info.get('symptoms', [])),
                clinical_history=patient_info.get('clinical_history', 'Not provided'),
                findings=findings_text,
                literature_summary=literature_summary,
                additional_context=json.dumps(state.get('web_search_results', []))
            )
            
            # Generate report using provider
            available_providers = self.provider_manager.get_available_providers()
            if not available_providers:
                raise Exception("No AI providers available")
            
            provider_name, provider = available_providers[0]
            models = provider.get_available_models()
            
            if not models:
                raise Exception(f"No models available for {provider_name}")
            
            response = await provider._call_api(
                prompt=formatted_prompt,
                model=models[0].model_id
            )
            
            # Parse and structure the report
            report_data = self._parse_report_response(response)
            
            # Extract key information
            key_findings = self._extract_key_findings(report_data.get('findings_section', ''))
            recommendations = self._extract_recommendations(report_data.get('recommendations_section', ''))
            
            # Update state
            state['detailed_report'] = report_data
            state['key_findings'] = key_findings
            state['recommendations'] = recommendations
            state['completed_steps'].append('report_generation')
            
            logger.info("Detailed report generation completed")
            
        except Exception as e:
            logger.error(f"Report generation error: {str(e)}")
            state['error'] = f"Report generation failed: {str(e)}"
            state['detailed_report'] = {
                'content': 'Report generation failed',
                'error': str(e)
            }
        
        return state
    
    def _format_findings_for_report(self, findings: List[Dict]) -> str:
        """Format findings for report generation"""
        if not findings:
            return "No specific findings identified"
        
        formatted = []
        for i, finding in enumerate(findings, 1):
            location = finding.get('location', 'Not specified')
            severity = finding.get('severity', 'moderate')
            description = finding.get('description', '')
            
            formatted.append(f"{i}. {description} (Location: {location}, Severity: {severity})")
        
        return '\n'.join(formatted)
    
    def _summarize_literature(self, references: List[Dict]) -> str:
        """Summarize literature references"""
        if not references:
            return "No literature references available"
        
        summary = []
        for i, ref in enumerate(references[:5], 1):  # Top 5 references
            title = ref.get('title', 'No title')
            authors = ref.get('authors', [])
            year = ref.get('year', 'Unknown')
            
            author_str = authors[0] if authors else 'Unknown'
            if len(authors) > 1:
                author_str += " et al."
            
            summary.append(f"{i}. {author_str} ({year}): {title}")
        
        return '\n'.join(summary)
    
    def _extract_main_condition(self, findings: List[Dict]) -> Optional[str]:
        """Extract the main medical condition from findings"""
        # Priority conditions
        priority_conditions = [
            'pneumonia', 'tuberculosis', 'cancer', 'tumor', 'mass',
            'pneumothorax', 'hemothorax', 'cardiomegaly'
        ]
        
        for finding in findings:
            desc = finding.get('description', '').lower()
            for condition in priority_conditions:
                if condition in desc:
                    return condition
        
        # If no priority condition found, return first mentioned condition
        for finding in findings:
            desc = finding.get('description', '').lower()
            conditions = ['consolidation', 'opacity', 'infiltrate', 'effusion', 'nodule']
            for condition in conditions:
                if condition in desc:
                    return condition
        
        return None
    
    def _parse_report_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into structured report sections"""
        # Implementation to parse response into sections
        # This is a simplified version - enhance based on actual response format
        
        sections = {
            'content': response,
            'findings_section': '',
            'recommendations_section': '',
            'references_section': ''
        }
        
        # Extract sections using patterns
        findings_match = re.search(r'(?:FINDINGS?|KEY FINDINGS?):(.*?)(?:RECOMMENDATION|CLINICAL|$)', 
                                 response, re.IGNORECASE | re.DOTALL)
        if findings_match:
            sections['findings_section'] = findings_match.group(1).strip()
        
        recommendations_match = re.search(r'(?:RECOMMENDATIONS?):(.*?)(?:PATIENT|REFERENCE|$)', 
                                        response, re.IGNORECASE | re.DOTALL)
        if recommendations_match:
            sections['recommendations_section'] = recommendations_match.group(1).strip()
        
        return sections
    
    def _extract_key_findings(self, findings_text: str) -> List[str]:
        """Extract key findings from the findings section"""
        key_findings = []
        
        # Split by numbered items or bullet points
        items = re.split(r'\n\s*(?:\d+\.|-|\*)', findings_text)
        
        for item in items:
            item = item.strip()
            if len(item) > 20:  # Meaningful finding
                key_findings.append(item)
        
        return key_findings[:10]  # Top 10 key findings
    
    def _extract_recommendations(self, recommendations_text: str) -> List[str]:
        """Extract recommendations from the recommendations section"""
        recommendations = []
        
        # Split by numbered items or bullet points
        items = re.split(r'\n\s*(?:\d+\.|-|\*)', recommendations_text)
        
        for item in items:
            item = item.strip()
            if len(item) > 20:  # Meaningful recommendation
                recommendations.append(item)
        
        return recommendations[:10]  # Top 10 recommendations


class QualityCheckerAgent:
    """Agent for quality checking the generated report"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
    
    async def check_quality(self, state: MedicalImagingState) -> MedicalImagingState:
        """Check quality of the generated report"""
        
        try:
            logger.info("Starting quality check")
            
            report = state.get('detailed_report', {})
            findings = state.get('findings', [])
            
            # Prepare quality check prompt
            quality_prompt = QUALITY_CHECKER_PROMPT.format(
                report_content=report.get('content', ''),
                original_findings=json.dumps(findings),
                patient_age=state.get('patient_info', {}).get('age', 'Unknown'),
                patient_gender=state.get('patient_info', {}).get('gender', 'Unknown')
            )
            
            # Run quality check using provider
            available_providers = self.provider_manager.get_available_providers()
            if not available_providers:
                raise Exception("No AI providers available")
            
            provider_name, provider = available_providers[0]
            models = provider.get_available_models()
            
            if not models:
                raise Exception(f"No models available for {provider_name}")
            
            response = await provider._call_api(
                prompt=quality_prompt,
                model=models[0].model_id
            )
            
            # Parse quality check results
            quality_score = self._extract_quality_score(response)
            issues = self._extract_issues(response)
            
            # Update state
            state['quality_score'] = quality_score
            state['quality_issues'] = issues
            state['quality_check_passed'] = quality_score >= 0.8
            state['completed_steps'].append('quality_check')
            
            logger.info(f"Quality check completed with score: {quality_score}")
            
        except Exception as e:
            logger.error(f"Quality check error: {str(e)}")
            state['error'] = f"Quality check failed: {str(e)}"
            state['quality_score'] = 0.0
            state['quality_check_passed'] = False
        
        return state
    
    def _extract_quality_score(self, response: str) -> float:
        """Extract quality score from response"""
        # Look for score patterns
        score_match = re.search(r'(?:score|rating):\s*(\d+(?:\.\d+)?)', response, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
            # Normalize to 0-1 range if needed
            if score > 1:
                score = score / 10 if score <= 10 else score / 100
            return score
        
        # Default score based on content
        if 'excellent' in response.lower():
            return 0.9
        elif 'good' in response.lower():
            return 0.8
        elif 'satisfactory' in response.lower():
            return 0.7
        else:
            return 0.6
    
    def _extract_issues(self, response: str) -> List[str]:
        """Extract any quality issues from the response"""
        issues = []
        
        # Look for issue patterns
        issue_patterns = [
            r'issue[s]?:(.*?)(?:\n|$)',
            r'problem[s]?:(.*?)(?:\n|$)',
            r'concern[s]?:(.*?)(?:\n|$)',
            r'missing:(.*?)(?:\n|$)'
        ]
        
        for pattern in issue_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                issue = match.group(1).strip()
                if issue:
                    issues.append(issue)
        
        return issues