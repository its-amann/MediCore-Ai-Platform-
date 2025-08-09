"""
Tools for LangGraph Medical Imaging Workflow
"""

import os
import logging
import httpx
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import urllib.parse
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class PubMedSearchTool:
    """Tool for searching PubMed medical literature"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.email = os.getenv("PUBMED_EMAIL", "medical-ai@example.com")
        self.api_key = os.getenv("PUBMED_API_KEY", "")  # Optional but recommended
        
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        age: Optional[str] = None,
        gender: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed for medical literature
        
        Args:
            query: Search query (condition, symptoms, etc.)
            max_results: Maximum number of results to return
            age: Patient age for more specific results
            gender: Patient gender for more specific results
            
        Returns:
            List of literature references with title, authors, abstract, etc.
        """
        
        # Enhance query with demographics if provided
        if age and gender:
            query = f"{query} AND {age} year old {gender}"
        
        try:
            # Step 1: Search for IDs
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'json',
                'email': self.email,
                'tool': 'MedicalAI'
            }
            
            if self.api_key:
                search_params['api_key'] = self.api_key
            
            async with httpx.AsyncClient() as client:
                search_response = await client.get(
                    f"{self.base_url}/esearch.fcgi",
                    params=search_params,
                    timeout=30.0
                )
                
                if search_response.status_code != 200:
                    logger.error(f"PubMed search failed: {search_response.status_code}")
                    return []
                
                search_data = search_response.json()
                id_list = search_data.get('esearchresult', {}).get('idlist', [])
                
                if not id_list:
                    logger.info("No PubMed results found")
                    return []
                
                # Step 2: Fetch details for IDs
                fetch_params = {
                    'db': 'pubmed',
                    'id': ','.join(id_list),
                    'rettype': 'abstract',
                    'retmode': 'xml',
                    'email': self.email,
                    'tool': 'MedicalAI'
                }
                
                if self.api_key:
                    fetch_params['api_key'] = self.api_key
                
                fetch_response = await client.get(
                    f"{self.base_url}/efetch.fcgi",
                    params=fetch_params,
                    timeout=30.0
                )
                
                if fetch_response.status_code != 200:
                    logger.error(f"PubMed fetch failed: {fetch_response.status_code}")
                    return []
                
                # Parse XML response
                root = ET.fromstring(fetch_response.text)
                results = []
                
                for article in root.findall('.//PubmedArticle'):
                    try:
                        # Extract article details
                        citation = article.find('.//MedlineCitation')
                        article_elem = citation.find('.//Article')
                        
                        # Title
                        title_elem = article_elem.find('.//ArticleTitle')
                        title = title_elem.text if title_elem is not None else 'No title'
                        
                        # Authors
                        authors_list = []
                        author_list = article_elem.find('.//AuthorList')
                        if author_list is not None:
                            for author in author_list.findall('.//Author'):
                                last_name = author.find('.//LastName')
                                fore_name = author.find('.//ForeName')
                                if last_name is not None and fore_name is not None:
                                    authors_list.append(f"{last_name.text} {fore_name.text}")
                        
                        # Abstract
                        abstract_elem = article_elem.find('.//AbstractText')
                        abstract = abstract_elem.text if abstract_elem is not None else 'No abstract available'
                        
                        # Publication info
                        journal = article_elem.find('.//Journal/Title')
                        journal_name = journal.text if journal is not None else 'Unknown journal'
                        
                        pub_date = article_elem.find('.//Journal/JournalIssue/PubDate')
                        year = 'Unknown'
                        if pub_date is not None:
                            year_elem = pub_date.find('.//Year')
                            if year_elem is not None:
                                year = year_elem.text
                        
                        # PMID
                        pmid_elem = citation.find('.//PMID')
                        pmid = pmid_elem.text if pmid_elem is not None else 'Unknown'
                        
                        results.append({
                            'title': title,
                            'authors': authors_list[:3],  # First 3 authors
                            'abstract': abstract[:500] + '...' if len(abstract) > 500 else abstract,
                            'journal': journal_name,
                            'year': year,
                            'pmid': pmid,
                            'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                        })
                        
                    except Exception as e:
                        logger.error(f"Error parsing PubMed article: {e}")
                        continue
                
                logger.info(f"Retrieved {len(results)} PubMed articles")
                return results
                
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []


class GeminiWebSearchTool:
    """Tool for web search using Gemini models with built-in search capability"""
    
    def __init__(self):
        from app.microservices.medical_imaging.services.ai_services.providers.gemini_web_search_provider import GeminiWebSearchProvider
        self.provider = None
        try:
            self.provider = GeminiWebSearchProvider()
            logger.info("Gemini web search tool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini web search: {e}")
    
    async def search_medical_cases(
        self, 
        condition: str, 
        symptoms: List[str] = None,
        demographics: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for medical case studies and recent research
        
        Args:
            condition: Primary medical condition
            symptoms: List of associated symptoms
            demographics: Patient demographics (age, gender, etc.)
            
        Returns:
            List of relevant case studies and references
        """
        
        if not self.provider:
            logger.error("Gemini web search not available")
            return []
        
        # Build search query
        query_parts = [f"recent medical case studies {condition}"]
        
        if symptoms:
            symptoms_str = " ".join(symptoms[:3])  # First 3 symptoms
            query_parts.append(f"symptoms {symptoms_str}")
        
        if demographics:
            if 'age' in demographics:
                query_parts.append(f"{demographics['age']} year old")
            if 'gender' in demographics:
                query_parts.append(demographics['gender'])
        
        query = " ".join(query_parts)
        
        try:
            # Use Gemini's web search to find relevant cases
            prompt = f"""
            Search for recent medical case studies and literature about:
            Condition: {condition}
            {"Symptoms: " + ", ".join(symptoms) if symptoms else ""}
            {"Patient: " + str(demographics) if demographics else ""}
            
            Find and summarize:
            1. Recent case studies (2020-2025)
            2. Treatment approaches and outcomes
            3. Diagnostic considerations
            4. Similar cases in literature
            
            Provide structured results with citations.
            """
            
            response = await self.provider.generate_response(
                prompt=prompt,
                image_data=None,
                model_name="gemini-2.0-flash-exp"  # Using a model that supports web search
            )
            
            # Parse the response
            if response.get('success') and response.get('content'):
                # Extract structured information from the response
                content = response['content']
                
                # Simple parsing - can be enhanced with better extraction
                references = []
                
                # Split content into sections
                sections = content.split('\n\n')
                for section in sections:
                    if any(keyword in section.lower() for keyword in ['case', 'study', 'patient', 'treatment']):
                        references.append({
                            'snippet': section[:300] + '...' if len(section) > 300 else section,
                            'source': 'Gemini Web Search',
                            'relevance': 'high'
                        })
                
                return references[:10]  # Return top 10 references
            
            return []
            
        except Exception as e:
            logger.error(f"Gemini web search error: {e}")
            return []


class HeatmapGenerationTool:
    """Tool for generating heatmaps from medical imaging findings"""
    
    def __init__(self):
        # Import the existing image processor
        try:
            from app.microservices.medical_imaging.services.image_processing.image_processor import get_image_processor
            self.image_processor = get_image_processor()
            self.use_image_processor = True
            logger.info("Heatmap generation tool initialized with image processor")
        except ImportError:
            self.use_image_processor = False
            logger.warning("Image processor not available, using simple heatmap generation")
        
    async def generate_heatmap(
        self, 
        image_data: str, 
        findings: List[Dict[str, Any]],
        image_size: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Generate heatmap overlay from findings with coordinates
        
        Args:
            image_data: Base64 encoded image data
            findings: List of findings with location information
            image_size: Optional image dimensions (width, height)
            
        Returns:
            Dictionary with heatmap overlay data
        """
        
        if self.use_image_processor:
            try:
                import base64
                from PIL import Image
                import io
                import numpy as np
                
                # Decode base64 image
                image_bytes = base64.b64decode(image_data)
                base_image = Image.open(io.BytesIO(image_bytes))
                
                if image_size:
                    base_image = base_image.resize(image_size)
                
                # Convert to numpy array
                image_array = np.array(base_image)
                
                # Use the existing image processor's heatmap generation
                heatmap_data = await self.image_processor.generate_heatmap(
                    image_array=image_array,
                    findings=findings
                )
                
                return {
                    'overlay': heatmap_data.heatmap_overlay,
                    'heatmap': heatmap_data.heatmap_only,
                    'heat_regions': heatmap_data.attention_regions,
                    'original': heatmap_data.original_image,
                    'confidence': 0.85
                }
                
            except Exception as e:
                logger.error(f"Image processor heatmap generation error: {e}")
                # Fall back to simple generation
        
        # Use simple heatmap generation
        return await self._generate_simple_heatmap(image_data, findings, image_size)
    
    async def _generate_simple_heatmap(
        self, 
        image_data: str, 
        findings: List[Dict[str, Any]],
        image_size: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Fallback simple heatmap generation"""
        
        try:
            import base64
            from PIL import Image, ImageDraw, ImageFilter
            import io
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            base_image = Image.open(io.BytesIO(image_bytes))
            
            if image_size:
                base_image = base_image.resize(image_size)
            
            width, height = base_image.size
            
            # Create heatmap overlay
            heatmap = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(heatmap)
            
            # Process each finding
            heat_regions = []
            for finding in findings:
                coords = finding.get('coordinates', {})
                severity = finding.get('severity', 'moderate').lower()
                
                # Determine intensity
                intensity = {
                    'mild': 0.3,
                    'moderate': 0.6,
                    'severe': 0.9
                }.get(severity, 0.6)
                
                if 'x' in coords and 'y' in coords:
                    # Normalize coordinates if they're in 0-1 range
                    x = int(coords['x'] * width) if coords['x'] <= 1 else int(coords['x'])
                    y = int(coords['y'] * height) if coords['y'] <= 1 else int(coords['y'])
                    radius = int(width * 0.1)
                    
                    # Draw gradient circle
                    for r in range(radius, 0, -2):
                        alpha = int(255 * intensity * (r / radius))
                        draw.ellipse(
                            [(x - r, y - r), (x + r, y + r)],
                            fill=(255, 0, 0, alpha)
                        )
                    
                    heat_regions.append({
                        'id': f"region_{len(heat_regions)}",
                        'center': {'x': x, 'y': y},
                        'confidence': intensity,
                        'finding': finding.get('description', '')
                    })
                
                elif 'region' in coords:
                    region = coords['region'].lower()
                    x, y, w, h = self._get_region_coords(region, width, height)
                    
                    alpha = int(255 * intensity)
                    draw.rectangle([(x, y), (x + w, y + h)], fill=(255, 0, 0, alpha))
                    
                    heat_regions.append({
                        'id': f"region_{len(heat_regions)}",
                        'bounds': {'x_min': x, 'y_min': y, 'x_max': x + w, 'y_max': y + h},
                        'confidence': intensity,
                        'finding': finding.get('description', '')
                    })
            
            # Apply blur
            heatmap = heatmap.filter(ImageFilter.GaussianBlur(radius=width // 20))
            
            # Create overlay
            overlay = Image.alpha_composite(base_image.convert('RGBA'), heatmap)
            
            # Convert to base64
            overlay_buffer = io.BytesIO()
            overlay.save(overlay_buffer, format='PNG')
            overlay_base64 = base64.b64encode(overlay_buffer.getvalue()).decode('utf-8')
            
            heatmap_buffer = io.BytesIO()
            heatmap.save(heatmap_buffer, format='PNG')
            heatmap_base64 = base64.b64encode(heatmap_buffer.getvalue()).decode('utf-8')
            
            # Original image base64
            orig_buffer = io.BytesIO()
            base_image.save(orig_buffer, format='PNG')
            orig_base64 = base64.b64encode(orig_buffer.getvalue()).decode('utf-8')
            
            return {
                'overlay': overlay_base64,
                'heatmap': heatmap_base64,
                'heat_regions': heat_regions,
                'original': orig_base64,
                'confidence': 0.85
            }
            
        except Exception as e:
            logger.error(f"Simple heatmap generation error: {e}")
            return {
                'error': str(e),
                'heat_regions': []
            }
    
    def _get_region_coords(self, region: str, width: int, height: int) -> tuple:
        """Get coordinates for anatomical regions"""
        
        regions = {
            'upper right': (width * 0.5, 0, width * 0.5, height * 0.5),
            'upper left': (0, 0, width * 0.5, height * 0.5),
            'lower right': (width * 0.5, height * 0.5, width * 0.5, height * 0.5),
            'lower left': (0, height * 0.5, width * 0.5, height * 0.5),
            'central': (width * 0.25, height * 0.25, width * 0.5, height * 0.5),
            'right': (width * 0.5, 0, width * 0.5, height),
            'left': (0, 0, width * 0.5, height),
            'upper': (0, 0, width, height * 0.5),
            'lower': (0, height * 0.5, width, height * 0.5)
        }
        
        return regions.get(region, (0, 0, width, height))


class DuckDuckGoSearchTool:
    """Tool for searching the web using DuckDuckGo (free, no API key required)"""
    
    def __init__(self):
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
            self.available = True
            logger.info("DuckDuckGo search tool initialized successfully")
        except ImportError:
            logger.warning("duckduckgo-search package not installed. Run: pip install duckduckgo-search")
            self.available = False
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        region: str = "wt-wt",  # worldwide
        safesearch: str = "moderate",
        time_range: Optional[str] = None  # 'd', 'w', 'm', 'y'
    ) -> List[Dict[str, Any]]:
        """
        Search the web using DuckDuckGo
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            region: Region code (default: worldwide)
            safesearch: Safe search setting ('on', 'moderate', 'off')
            time_range: Time range for results ('d'=day, 'w'=week, 'm'=month, 'y'=year)
            
        Returns:
            List of search results with title, link, snippet
        """
        
        if not self.available:
            logger.error("DuckDuckGo search not available")
            return []
        
        try:
            # Perform search
            results = []
            search_results = self.ddgs.text(
                keywords=query,
                region=region,
                safesearch=safesearch,
                timelimit=time_range,
                max_results=max_results
            )
            
            for result in search_results:
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'snippet': result.get('body', ''),
                    'source': 'DuckDuckGo'
                })
            
            logger.info(f"DuckDuckGo search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    async def search_medical(
        self, 
        condition: str, 
        context: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for medical information with enhanced query
        
        Args:
            condition: Medical condition or topic
            context: Additional context (symptoms, demographics, etc.)
            max_results: Maximum number of results
            
        Returns:
            List of medical-focused search results
        """
        
        # Build medical-focused query
        query_parts = [condition, "medical", "treatment", "diagnosis"]
        
        if context:
            query_parts.append(context)
        
        # Add medical sites to improve relevance
        query = f"{' '.join(query_parts)} site:nih.gov OR site:mayoclinic.org OR site:webmd.com OR site:medlineplus.gov OR site:ncbi.nlm.nih.gov"
        
        return await self.search(query, max_results=max_results)