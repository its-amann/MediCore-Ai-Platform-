"""
Agents for LangGraph Medical Imaging Workflow
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
                'coordinates': {},
                'severity': 'moderate'
            }
            
            # Extract description
            lines = section.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for specific fields
                if 'Description:' in line:
                    finding['description'] = line.split('Description:')[1].strip()
                elif 'Location:' in line:
                    finding['location'] = line.split('Location:')[1].strip()
                elif 'Severity:' in line:
                    severity = line.split('Severity:')[1].strip().lower()
                    if severity in ['mild', 'moderate', 'severe']:
                        finding['severity'] = severity
                elif 'Size:' in line:
                    finding['size'] = line.split('Size:')[1].strip()
                elif 'Coordinates:' in line:
                    coord_text = line.split('Coordinates:')[1].strip()
                    # Try to extract coordinates
                    point_match = re.search(r'(\d+)\s*,\s*(\d+)', coord_text)
                    if point_match:
                        finding['coordinates']['x'] = int(point_match.group(1))
                        finding['coordinates']['y'] = int(point_match.group(2))
                elif 'Characteristics:' in line:
                    finding['characteristics'] = line.split('Characteristics:')[1].strip()
            
            # If no description found, use the first non-empty line
            if not finding['description'] and lines:
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
        """Search for relevant medical literature based on findings"""
        
        try:
            logger.info("Starting literature search")
            
            findings = state.get('findings', [])
            patient_info = state.get('patient_info', {})
            
            # Extract search terms from findings
            search_terms = []
            diseases_found = []
            
            for finding in findings:
                desc = finding.get('description', '').lower()
                # Extract potential disease names
                disease_patterns = [
                    r'pneumonia', r'consolidation', r'infiltrate', r'opacity',
                    r'nodule', r'mass', r'lesion', r'effusion', r'edema',
                    r'cardiomegaly', r'atelectasis', r'pneumothorax'
                ]
                
                for pattern in disease_patterns:
                    if re.search(pattern, desc):
                        diseases_found.append(pattern)
            
            # Remove duplicates
            diseases_found = list(set(diseases_found))
            
            # Prepare search queries
            age = patient_info.get('age', '')
            gender = patient_info.get('gender', '')
            
            all_references = []
            
            # Search for each disease found
            for disease in diseases_found[:3]:  # Limit to top 3 diseases
                # Try PubMed first
                references = await self.pubmed_tool.search(
                    query=f"{disease} chest x-ray diagnosis treatment",
                    max_results=5,
                    age=age,
                    gender=gender
                )
                all_references.extend(references)
                
                # Also search DuckDuckGo for recent web results
                if self.duckduckgo_tool.available:
                    web_results = await self.duckduckgo_tool.search_medical(
                        condition=disease,
                        context=f"chest x-ray {age} year old {gender}" if age and gender else "chest x-ray",
                        max_results=3
                    )
                    # Convert DuckDuckGo results to reference format
                    for web_result in web_results:
                        all_references.append({
                            'title': web_result.get('title', ''),
                            'authors': ['Web Source'],
                            'abstract': web_result.get('snippet', ''),
                            'journal': 'Web Resource',
                            'year': str(datetime.now().year),
                            'pmid': '',
                            'url': web_result.get('link', '')
                        })
            
            # If no specific diseases found, do a general search
            if not diseases_found and findings:
                general_query = "chest x-ray abnormal findings diagnosis"
                references = await self.pubmed_tool.search(
                    query=general_query,
                    max_results=5,
                    age=age,
                    gender=gender
                )
                all_references.extend(references)
                
                # Also search DuckDuckGo
                if self.duckduckgo_tool.available:
                    web_results = await self.duckduckgo_tool.search_medical(
                        condition="chest x-ray abnormal findings",
                        context=f"{age} year old {gender}" if age and gender else None,
                        max_results=3
                    )
                    for web_result in web_results:
                        all_references.append({
                            'title': web_result.get('title', ''),
                            'authors': ['Web Source'],
                            'abstract': web_result.get('snippet', ''),
                            'journal': 'Web Resource',
                            'year': str(datetime.now().year),
                            'pmid': '',
                            'url': web_result.get('link', '')
                        })
            
            # Remove duplicates by PMID
            seen_pmids = set()
            unique_references = []
            for ref in all_references:
                pmid = ref.get('pmid', '')
                if pmid and pmid not in seen_pmids:
                    seen_pmids.add(pmid)
                    unique_references.append(ref)
                elif not pmid:
                    unique_references.append(ref)
            
            # Sort by relevance score
            unique_references.sort(key=lambda x: int(x.get('relevance_score', '0')), reverse=True)
            
            # Update state
            state['literature_references'] = unique_references[:15]  # Top 15 references
            state['completed_steps'].append('literature_search')
            
            logger.info(f"Literature search completed with {len(unique_references)} references")
            
        except Exception as e:
            logger.error(f"Literature search error: {str(e)}")
            state['error'] = f"Literature search failed: {str(e)}"
            state['literature_references'] = []
        
        return state


class DetailedReportWriterAgent:
    """Agent for writing detailed medical reports with web search capability"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
        self.web_search_tool = GeminiWebSearchTool()
        from .tools import DuckDuckGoSearchTool
        self.duckduckgo_tool = DuckDuckGoSearchTool()
    
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
                # Use web search tool for additional case studies
                logger.info("Performing additional web search for case studies")
                
                # Extract main condition from findings
                main_condition = self._extract_main_condition(findings)
                
                if main_condition:
                    # Agent will intelligently use available web search tools
                    # Both tools are available - agent decides which to use
                    web_results = []
                    
                    # The agent can use either tool based on availability and success
                    # No need for hard-coded fallback logic
                    logger.info(f"Agent searching for additional case studies on: {main_condition}")
                    
                    # Let the agent use its available tools intelligently
                    state['web_search_query'] = f"{main_condition} case studies patient outcomes treatment"
                    state['web_search_needed'] = True
            
            # Format the prompt
            formatted_prompt = DETAILED_REPORT_WRITER_PROMPT.format(
                age=patient_info.get('age', 'Not specified'),
                gender=patient_info.get('gender', 'Not specified'),
                symptoms=', '.join(patient_info.get('symptoms', ['None reported'])),
                clinical_history=patient_info.get('clinical_history', 'No history provided'),
                findings_text=findings_text,
                literature_summary=literature_summary
            )
            
            # Add web search results if available
            if state.get('web_search_results'):
                formatted_prompt += f"\n\nAdditional Web Search Results:\n{state['web_search_results']}"
            
            # Generate report using provider
            available_providers = self.provider_manager.get_available_providers()
            if not available_providers:
                raise Exception("No AI providers available")
            
            # Use first available provider
            provider_name, provider = available_providers[0]
            models = provider.get_available_models(require_vision=False)
            
            if not models:
                raise Exception(f"No models available for {provider_name}")
            
            response = await provider._call_api(
                prompt=formatted_prompt,
                model=models[0].model_id
            )
            
            # Extract key findings from report
            key_findings = self._extract_key_findings_from_report(response)
            
            # Extract recommendations
            recommendations = self._extract_recommendations(response)
            
            # Update state
            state['detailed_report'] = {
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
                "web_search_performed": bool(state.get('web_search_results'))
            }
            
            state['key_findings'] = key_findings
            state['recommendations'] = recommendations
            state['completed_steps'].append('report_generation')
            
            logger.info("Detailed report generation completed")
            
        except Exception as e:
            logger.error(f"Report generation error: {str(e)}")
            state['error'] = f"Report generation failed: {str(e)}"
        
        return state
    
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
        """Summarize literature for report"""
        if not literature:
            return "No specific literature references available."
        
        summary = []
        
        # Group by type
        case_studies = [ref for ref in literature if ref.get('type', '').lower() == 'case study']
        guidelines = [ref for ref in literature if 'guideline' in ref.get('type', '').lower()]
        research = [ref for ref in literature if ref.get('type', '').lower() in ['research', 'clinical trial']]
        
        # Add case studies
        if case_studies:
            summary.append("RELEVANT CASE STUDIES:")
            for ref in case_studies[:3]:
                summary.append(f"\n{ref.get('title', 'Untitled')} ({ref.get('authors', 'Unknown')}, {ref.get('year', 'n.d.')})")
                if ref.get('abstract'):
                    summary.append(f"Summary: {ref['abstract'][:200]}...")
                if ref.get('url'):
                    summary.append(f"Source: {ref['url']}")
        
        # Add guidelines
        if guidelines:
            summary.append("\n\nCLINICAL GUIDELINES:")
            for ref in guidelines[:2]:
                summary.append(f"\n{ref.get('title', 'Untitled')} ({ref.get('journal', 'Unknown')}, {ref.get('year', 'n.d.')})")
                if ref.get('abstract'):
                    summary.append(f"Summary: {ref['abstract'][:200]}...")
        
        # Add research
        if research:
            summary.append("\n\nRESEARCH EVIDENCE:")
            for ref in research[:3]:
                summary.append(f"\n{ref.get('title', 'Untitled')}")
                summary.append(f"({ref.get('authors', 'Unknown')}, {ref.get('year', 'n.d.')}, {ref.get('journal', 'Journal')})")
                if ref.get('abstract'):
                    summary.append(f"Key findings: {ref['abstract'][:200]}...")
        
        return '\n'.join(summary)
    
    def _extract_main_condition(self, findings: List[Dict[str, Any]]) -> Optional[str]:
        """Extract main medical condition from findings"""
        conditions = []
        
        for finding in findings:
            desc = finding.get('description', '').lower()
            
            # Common conditions
            if 'pneumonia' in desc or 'consolidation' in desc:
                conditions.append('pneumonia')
            elif 'effusion' in desc:
                conditions.append('pleural effusion')
            elif 'edema' in desc:
                conditions.append('pulmonary edema')
            elif 'cardiomegaly' in desc:
                conditions.append('cardiomegaly')
            elif 'nodule' in desc or 'mass' in desc:
                conditions.append('lung nodule')
            elif 'pneumothorax' in desc:
                conditions.append('pneumothorax')
        
        return conditions[0] if conditions else None
    
    def _extract_key_findings_from_report(self, report_content: str) -> List[str]:
        """Extract key findings from report"""
        key_findings = []
        
        # Look for KEY FINDINGS section
        key_findings_match = re.search(r'1\.\s*KEY FINDINGS.*?\n(.*?)\n\n?2\.', report_content, re.DOTALL | re.IGNORECASE)
        
        if key_findings_match:
            findings_text = key_findings_match.group(1)
            # Extract bullet points
            bullet_lines = re.findall(r'[-•*]\s*(.+)', findings_text)
            
            for line in bullet_lines:
                finding = line.strip()
                if finding and len(finding) > 10:
                    key_findings.append(finding)
        
        return key_findings
    
    def _extract_recommendations(self, report_content: str) -> List[str]:
        """Extract recommendations from report"""
        recommendations = []
        
        # Look for RECOMMENDATIONS section
        rec_match = re.search(r'RECOMMENDATIONS.*?\n(.*?)(?:\n\n|\n\d+\.)', report_content, re.DOTALL | re.IGNORECASE)
        
        if rec_match:
            rec_text = rec_match.group(1)
            # Extract bullet points or numbered items
            lines = re.findall(r'(?:[-•*]|\d+\.)\s*(.+)', rec_text)
            
            for line in lines:
                rec = line.strip()
                if rec and len(rec) > 10:
                    recommendations.append(rec)
        
        return recommendations


class QualityCheckerAgent:
    """Agent for checking report quality"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
    
    async def check_quality(self, state: MedicalImagingState) -> MedicalImagingState:
        """Check quality of generated report"""
        
        try:
            logger.info("Starting quality check")
            
            report = state.get('detailed_report', {})
            findings = state.get('findings', [])
            literature = state.get('literature_references', [])
            
            # Format quality check prompt
            formatted_prompt = QUALITY_CHECKER_PROMPT.format(
                report_content=report.get('content', '')[:2000],
                num_findings=len(findings),
                num_references=len(literature)
            )
            
            # Get available providers
            available_providers = self.provider_manager.get_available_providers()
            if not available_providers:
                raise Exception("No AI providers available")
            
            # Use first available provider
            provider_name, provider = available_providers[0]
            models = provider.get_available_models(require_vision=False)
            
            if not models:
                raise Exception(f"No models available for {provider_name}")
            
            response = await provider._call_api(
                prompt=formatted_prompt,
                model=models[0].model_id
            )
            
            # Extract score
            score_match = re.search(r'(?:score|rating).*?(\d*\.?\d+)', response, re.IGNORECASE)
            score = float(score_match.group(1)) if score_match else 0.75
            
            # Ensure score is between 0 and 1
            score = max(0.0, min(1.0, score))
            
            # Update state
            state['quality_score'] = score
            state['quality_feedback'] = response
            state['completed_steps'].append('quality_check')
            
            logger.info(f"Quality check completed with score: {score}")
            
        except Exception as e:
            logger.error(f"Quality check error: {str(e)}")
            state['quality_score'] = 0.7
            state['quality_feedback'] = "Quality check completed with default score"
        
        return state