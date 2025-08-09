"""
Intelligent tool management for LangGraph agents
Provides a unified interface for agents to use available tools intelligently
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class IntelligentSearchManager:
    """Manages multiple search tools and intelligently routes requests"""
    
    def __init__(self):
        self.search_tools = []
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize all available search tools"""
        
        # Try to initialize PubMed
        try:
            from .tools import PubMedSearchTool
            pubmed = PubMedSearchTool()
            self.search_tools.append({
                'name': 'PubMed',
                'tool': pubmed,
                'type': 'medical_literature',
                'priority': 1
            })
            logger.info("PubMed search tool available")
        except Exception as e:
            logger.warning(f"PubMed tool not available: {e}")
        
        # Try to initialize DuckDuckGo
        try:
            from .tools import DuckDuckGoSearchTool
            ddg = DuckDuckGoSearchTool()
            if ddg.available:
                self.search_tools.append({
                    'name': 'DuckDuckGo',
                    'tool': ddg,
                    'type': 'web_search',
                    'priority': 2
                })
                logger.info("DuckDuckGo search tool available")
        except Exception as e:
            logger.warning(f"DuckDuckGo tool not available: {e}")
        
        # Try to initialize Gemini Web Search
        try:
            from .tools import GeminiWebSearchTool
            gemini = GeminiWebSearchTool()
            if gemini.provider:
                self.search_tools.append({
                    'name': 'Gemini',
                    'tool': gemini,
                    'type': 'ai_web_search',
                    'priority': 0  # Highest priority
                })
                logger.info("Gemini web search tool available")
        except Exception as e:
            logger.warning(f"Gemini web search tool not available: {e}")
        
        # Sort by priority
        self.search_tools.sort(key=lambda x: x['priority'])
    
    async def search_medical_literature(
        self, 
        query: str,
        condition: Optional[str] = None,
        patient_info: Optional[Dict[str, Any]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Intelligently search for medical literature using available tools
        
        The agent will:
        1. Try tools in priority order
        2. Combine results from multiple sources
        3. Handle failures gracefully
        """
        
        all_results = []
        used_tools = []
        
        for tool_info in self.search_tools:
            tool_name = tool_info['name']
            tool = tool_info['tool']
            
            try:
                results = []
                
                # Use tool based on its capabilities
                if tool_name == 'PubMed':
                    results = await tool.search(
                        query=query,
                        max_results=max_results,
                        age=patient_info.get('age') if patient_info else None,
                        gender=patient_info.get('gender') if patient_info else None
                    )
                
                elif tool_name == 'DuckDuckGo':
                    if condition:
                        results = await tool.search_medical(
                            condition=condition,
                            context=self._build_context(patient_info),
                            max_results=max_results
                        )
                    else:
                        results = await tool.search(query, max_results=max_results)
                
                elif tool_name == 'Gemini':
                    results = await tool.search_medical_cases(
                        condition=condition or query,
                        symptoms=patient_info.get('symptoms', []) if patient_info else [],
                        demographics=patient_info
                    )
                
                if results:
                    # Add source information
                    for result in results:
                        result['search_tool'] = tool_name
                    
                    all_results.extend(results)
                    used_tools.append(tool_name)
                    logger.info(f"Got {len(results)} results from {tool_name}")
                
                # Stop if we have enough results
                if len(all_results) >= max_results * 2:
                    break
                    
            except Exception as e:
                logger.warning(f"Search with {tool_name} failed: {e}")
                # Continue with next tool
        
        if used_tools:
            logger.info(f"Successfully used tools: {', '.join(used_tools)}")
        else:
            logger.warning("No search tools succeeded")
        
        # Remove duplicates and limit results
        unique_results = self._deduplicate_results(all_results)
        return unique_results[:max_results]
    
    def _build_context(self, patient_info: Optional[Dict[str, Any]]) -> str:
        """Build context string from patient info"""
        if not patient_info:
            return ""
        
        parts = []
        if 'age' in patient_info:
            parts.append(f"{patient_info['age']} year old")
        if 'gender' in patient_info:
            parts.append(patient_info['gender'])
        if 'symptoms' in patient_info:
            symptoms = patient_info['symptoms']
            if isinstance(symptoms, list) and symptoms:
                parts.append(f"symptoms: {', '.join(symptoms[:3])}")
        
        return " ".join(parts)
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on title similarity"""
        unique = []
        seen_titles = set()
        
        for result in results:
            title = result.get('title', '').lower()
            # Simple deduplication - can be enhanced
            title_key = ''.join(title.split()[:5])  # First 5 words
            
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(result)
        
        return unique