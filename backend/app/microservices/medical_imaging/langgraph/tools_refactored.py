"""
Refactored Tools for LangGraph Medical Imaging Workflow
Tools are designed to be used by agents autonomously
"""

import os
import logging
import httpx
import json
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
import urllib.parse
import xml.etree.ElementTree as ET
from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
def generate_heatmap(
    image_data: str,
    findings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate a heatmap overlay for medical image findings.
    
    Args:
        image_data: Base64 encoded medical image
        findings: List of findings with coordinates
            Each finding should have:
            - coordinates: {"x": int, "y": int} or {"region": str}
            - severity: "mild", "moderate", or "severe"
            - description: Text description
    
    Returns:
        Dictionary containing:
        - overlay: Base64 encoded heatmap overlay image
        - heatmap: Base64 encoded heatmap only
        - heat_regions: List of heat regions with details
    """
    
    try:
        from app.microservices.medical_imaging.services.image_processing.image_processor import get_image_processor
        import numpy as np
        from PIL import Image
        import io
        
        # Get image processor
        processor = get_image_processor()
        
        # Decode image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Generate heatmap
        heatmap_data = processor.generate_heatmap(
            image_array=image_array,
            findings=findings
        )
        
        return {
            'overlay': heatmap_data.heatmap_overlay,
            'heatmap': heatmap_data.heatmap_only,
            'heat_regions': heatmap_data.attention_regions,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Heatmap generation failed: {e}")
        return {
            'error': str(e),
            'success': False
        }


@tool
def search_pubmed(
    query: str,
    max_results: int = 10,
    patient_age: Optional[int] = None,
    patient_gender: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search PubMed for medical literature.
    
    Args:
        query: Search query (e.g., "pneumonia chest x-ray treatment")
        max_results: Maximum number of results to return
        patient_age: Patient age for more specific results
        patient_gender: Patient gender (male/female) for more specific results
    
    Returns:
        List of literature references with title, authors, abstract, journal, year, and URL
    """
    
    try:
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        email = os.getenv("PUBMED_EMAIL", "medical-ai@example.com")
        api_key = os.getenv("PUBMED_API_KEY", "")
        
        # Enhance query with demographics
        if patient_age and patient_gender:
            query = f"{query} AND {patient_age} year old {patient_gender}"
        
        # Search for IDs
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'email': email,
            'tool': 'MedicalAI'
        }
        
        if api_key:
            search_params['api_key'] = api_key
        
        # Use synchronous httpx for simplicity in tool
        with httpx.Client() as client:
            search_response = client.get(
                f"{base_url}/esearch.fcgi",
                params=search_params,
                timeout=30.0
            )
            
            if search_response.status_code != 200:
                logger.error(f"PubMed search failed: {search_response.status_code}")
                return []
            
            search_data = search_response.json()
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            
            if not id_list:
                return []
            
            # Fetch details
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(id_list),
                'rettype': 'abstract',
                'retmode': 'xml',
                'email': email,
                'tool': 'MedicalAI'
            }
            
            if api_key:
                fetch_params['api_key'] = api_key
            
            fetch_response = client.get(
                f"{base_url}/efetch.fcgi",
                params=fetch_params,
                timeout=30.0
            )
            
            if fetch_response.status_code != 200:
                return []
            
            # Parse XML
            root = ET.fromstring(fetch_response.text)
            results = []
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    citation = article.find('.//MedlineCitation')
                    article_elem = citation.find('.//Article')
                    
                    title = article_elem.find('.//ArticleTitle')
                    title_text = title.text if title is not None else 'No title'
                    
                    # Authors
                    authors_list = []
                    author_list = article_elem.find('.//AuthorList')
                    if author_list is not None:
                        for author in author_list.findall('.//Author')[:3]:
                            last_name = author.find('.//LastName')
                            fore_name = author.find('.//ForeName')
                            if last_name is not None and fore_name is not None:
                                authors_list.append(f"{last_name.text} {fore_name.text}")
                    
                    # Abstract
                    abstract_elem = article_elem.find('.//AbstractText')
                    abstract_text = abstract_elem.text if abstract_elem is not None else 'No abstract'
                    
                    # Journal and year
                    journal = article_elem.find('.//Journal/Title')
                    journal_name = journal.text if journal is not None else 'Unknown journal'
                    
                    year = 'Unknown'
                    pub_date = article_elem.find('.//Journal/JournalIssue/PubDate/Year')
                    if pub_date is not None:
                        year = pub_date.text
                    
                    # PMID
                    pmid = citation.find('.//PMID')
                    pmid_text = pmid.text if pmid is not None else 'Unknown'
                    
                    results.append({
                        'title': title_text,
                        'authors': authors_list,
                        'abstract': abstract_text[:500] + '...' if len(abstract_text) > 500 else abstract_text,
                        'journal': journal_name,
                        'year': year,
                        'pmid': pmid_text,
                        'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/"
                    })
                    
                except Exception as e:
                    logger.error(f"Error parsing article: {e}")
                    continue
            
            return results
            
    except Exception as e:
        logger.error(f"PubMed search error: {e}")
        return []


@tool
def search_web(
    query: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search the web for medical information using DuckDuckGo.
    
    Args:
        query: Search query
        max_results: Maximum number of results
    
    Returns:
        List of web search results with title, link, and snippet
    """
    
    results = []
    
    # Use DuckDuckGo for web search
    try:
        from duckduckgo_search import DDGS
        
        ddgs = DDGS()
        search_results = ddgs.text(
            keywords=query,
            max_results=max_results
        )
        
        for result in search_results:
            results.append({
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'snippet': result.get('body', ''),
                'source': 'DuckDuckGo'
            })
        
        return results
        
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []


# Export all tools
__all__ = [
    'generate_heatmap',
    'search_pubmed',
    'search_web'
]