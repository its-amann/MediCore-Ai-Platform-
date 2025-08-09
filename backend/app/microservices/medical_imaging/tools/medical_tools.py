"""
Medical Imaging Tools for AI Agents
Provides PubMed search and DuckDuckGo web search capabilities
"""

import os
import logging
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import urllib.parse

logger = logging.getLogger(__name__)


async def search_pubmed(
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
        
        # Use async httpx
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
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
                logger.info("No PubMed results found")
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
            
            fetch_response = await client.get(
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
                    
                    # Format authors as string
                    authors_str = ', '.join(authors_list) if authors_list else 'Unknown'
                    
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
                        'authors': authors_str,  # String format
                        'abstract': abstract_text[:500] + '...' if len(abstract_text) > 500 else abstract_text,
                        'journal': journal_name,
                        'year': year,
                        'pmid': pmid_text,
                        'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/",
                        'type': 'research',
                        'relevance_score': '8'  # String format
                    })
                    
                except Exception as e:
                    logger.error(f"Error parsing article: {e}")
                    continue
            
            return results
            
    except Exception as e:
        logger.error(f"PubMed search error: {e}")
        return []


async def search_duckduckgo(
    query: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search DuckDuckGo for medical information.
    
    Args:
        query: Search query
        max_results: Maximum number of results
    
    Returns:
        List of web search results with title, link, and snippet
    """
    
    try:
        # Use the new ddgs package
        from ddgs import DDGS
        
        # Perform search using the new API
        ddgs = DDGS()
        search_results = ddgs.text(
            query,  # First positional argument
            max_results=max_results
        )
        
        results = []
        for result in search_results:
            try:
                # Ensure all text is properly encoded
                title = str(result.get('title', '')).encode('utf-8', 'ignore').decode('utf-8')
                url = str(result.get('href', ''))  # Use 'href' field
                body = str(result.get('body', '')).encode('utf-8', 'ignore').decode('utf-8')
                
                if title and url:  # Only add if we have both title and URL
                    results.append({
                        'title': title,
                        'url': url,
                        'abstract': body,
                        'source': 'DuckDuckGo',
                        'type': 'web',
                        'relevance_score': '5'  # Default relevance
                    })
            except Exception as e:
                logger.warning(f"Error processing result: {e}")
                continue
        
        logger.info(f"DuckDuckGo search for '{query}' returned {len(results)} results (using new ddgs package)")
        return results
        
    except (ImportError, AttributeError):
        # Fall back to old package if new one not available
        try:
            from duckduckgo_search import DDGS
            
            ddgs = DDGS()
            search_results = ddgs.text(
                keywords=query,
                max_results=max_results
            )
            
            results = []
            for result in search_results:
                try:
                    # Ensure all text is properly encoded
                    title = str(result.get('title', '')).encode('utf-8', 'ignore').decode('utf-8')
                    # Old package uses 'link', new package uses 'href'
                    url = str(result.get('link', result.get('href', '')))
                    body = str(result.get('body', '')).encode('utf-8', 'ignore').decode('utf-8')
                    
                    if title and url:  # Only add if we have both title and URL
                        results.append({
                            'title': title,
                            'url': url,
                            'abstract': body,
                            'source': 'DuckDuckGo',
                            'type': 'web',
                            'relevance_score': '5'  # Default relevance
                        })
                except Exception as e:
                    logger.warning(f"Error processing result: {e}")
                    continue
            
            logger.info(f"DuckDuckGo search for '{query}' returned {len(results)} results (using old package)")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed with old package: {e}")
            return []
        
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []


def format_pubmed_tool_description() -> str:
    """Get PubMed tool description for AI agents"""
    return """search_pubmed: Search PubMed medical database for peer-reviewed literature.
Parameters:
- query: Medical search terms (e.g. "pneumonia treatment guidelines")
- max_results: Number of results (default 10)
- patient_age: Optional patient age for specific results
- patient_gender: Optional patient gender

Returns medical literature with titles, authors, abstracts, and PubMed URLs."""


def format_duckduckgo_tool_description() -> str:
    """Get DuckDuckGo tool description for AI agents"""
    return """search_duckduckgo: Search the web for medical information and resources.
Parameters:
- query: Search terms
- max_results: Number of results (default 10)

Returns web results with titles, URLs, and snippets. Use for finding medical websites, patient resources, and current guidelines."""