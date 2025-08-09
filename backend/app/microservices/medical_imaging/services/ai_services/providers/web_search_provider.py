"""
Web Search Provider for Medical Literature
Provides web search capabilities using Google Search API or fallback methods
"""

import os
import logging
import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import urllib.parse

logger = logging.getLogger(__name__)


class WebSearchProvider:
    """Provider for web search functionality"""
    
    def __init__(self):
        """Initialize web search provider"""
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")  # Custom Search Engine ID
        self.serp_api_key = os.getenv("SERP_API_KEY")  # Alternative search API
        
        # Select search method based on available credentials
        self.search_method = self._determine_search_method()
        logger.info(f"Web search provider initialized with method: {self.search_method}")
    
    def _determine_search_method(self) -> str:
        """Determine which search method to use based on available API keys"""
        if self.google_api_key and self.google_cse_id:
            return "google"
        elif self.serp_api_key:
            return "serp"
        else:
            return "duckduckgo"  # Free fallback
    
    async def search_medical_literature(
        self,
        query: str,
        num_results: int = 10,
        site_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for medical literature with specified query
        
        Args:
            query: Search query string
            num_results: Number of results to return
            site_filter: Optional list of sites to search (e.g., ["pubmed.ncbi.nlm.nih.gov", "radiopaedia.org"])
        
        Returns:
            List of search results with title, url, snippet, and source
        """
        
        # Add site filters if provided
        if site_filter:
            site_query = " OR ".join([f"site:{site}" for site in site_filter])
            query = f"{query} ({site_query})"
        
        try:
            if self.search_method == "google":
                return await self._google_search(query, num_results)
            elif self.search_method == "serp":
                return await self._serp_search(query, num_results)
            else:
                return await self._duckduckgo_search(query, num_results)
        except Exception as e:
            logger.error(f"Search error with {self.search_method}: {e}")
            # Try fallback method
            if self.search_method != "duckduckgo":
                logger.info("Falling back to DuckDuckGo search")
                return await self._duckduckgo_search(query, num_results)
            return []
    
    async def _google_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API"""
        if not self.google_api_key or not self.google_cse_id:
            raise ValueError("Google API credentials not configured")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": query,
            "num": min(num_results, 10),  # Google CSE max is 10 per request
            "lr": "lang_en"  # English results
        }
        
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                for item in items:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": self._extract_source_from_url(item.get("link", "")),
                        "date": item.get("pagemap", {}).get("metatags", [{}])[0].get("date", "")
                    }
                    results.append(result)
                
                return results[:num_results]
                
            except Exception as e:
                logger.error(f"Google search error: {e}")
                raise
    
    async def _serp_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using SERP API (alternative to Google)"""
        if not self.serp_api_key:
            raise ValueError("SERP API key not configured")
        
        url = "https://serpapi.com/search"
        params = {
            "api_key": self.serp_api_key,
            "q": query,
            "num": num_results,
            "engine": "google"
        }
        
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                organic_results = data.get("organic_results", [])
                
                for item in organic_results:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": self._extract_source_from_url(item.get("link", "")),
                        "date": item.get("date", "")
                    }
                    results.append(result)
                
                return results[:num_results]
                
            except Exception as e:
                logger.error(f"SERP API search error: {e}")
                raise
    
    async def _duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Free fallback search using DuckDuckGo (no API key required)"""
        # Using DuckDuckGo HTML API (simpler than their instant answer API)
        encoded_query = urllib.parse.quote(query)
        url = f"https://duckduckgo.com/html/?q={encoded_query}"
        
        results = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # For DuckDuckGo, we'll use their instant answer API instead
                api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
                response = await client.get(api_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Get abstract if available
                    if data.get("AbstractText"):
                        results.append({
                            "title": data.get("Heading", "DuckDuckGo Result"),
                            "url": data.get("AbstractURL", ""),
                            "snippet": data.get("AbstractText", ""),
                            "source": data.get("AbstractSource", "DuckDuckGo"),
                            "date": ""
                        })
                    
                    # Get related topics
                    for topic in data.get("RelatedTopics", [])[:num_results-1]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append({
                                "title": topic.get("Text", "").split(" - ")[0][:100],
                                "url": topic.get("FirstURL", ""),
                                "snippet": topic.get("Text", ""),
                                "source": "DuckDuckGo",
                                "date": ""
                            })
                    
                    # If no results yet, return a message
                    if not results:
                        results.append({
                            "title": "No specific results found",
                            "url": "",
                            "snippet": f"Try searching directly on medical databases for: {query}",
                            "source": "System",
                            "date": ""
                        })
                
                return results[:num_results]
                
            except Exception as e:
                logger.error(f"DuckDuckGo search error: {e}")
                return [{
                    "title": "Search unavailable",
                    "url": "",
                    "snippet": "Web search is temporarily unavailable. Please try again later.",
                    "source": "System",
                    "date": ""
                }]
    
    def _extract_source_from_url(self, url: str) -> str:
        """Extract source name from URL"""
        if not url:
            return "Unknown"
        
        # Common medical sources
        source_map = {
            "pubmed.ncbi.nlm.nih.gov": "PubMed",
            "radiopaedia.org": "Radiopaedia",
            "nejm.org": "NEJM",
            "jamanetwork.com": "JAMA",
            "thelancet.com": "The Lancet",
            "bmj.com": "BMJ",
            "mayoclinic.org": "Mayo Clinic",
            "uptodate.com": "UpToDate",
            "medscape.com": "Medscape",
            "webmd.com": "WebMD",
            "nih.gov": "NIH",
            "who.int": "WHO",
            "cdc.gov": "CDC"
        }
        
        for domain, source in source_map.items():
            if domain in url:
                return source
        
        # Extract domain name as fallback
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace("www.", "").split(".")[0].title()
        except:
            return "Web"
    
    async def search_pubmed(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Specialized search for PubMed articles"""
        pubmed_query = f"{query} site:pubmed.ncbi.nlm.nih.gov"
        results = await self.search_medical_literature(pubmed_query, num_results)
        
        # Enhance results with PubMed-specific formatting
        for result in results:
            result["type"] = "Research Article"
            result["source"] = "PubMed"
            
            # Try to extract PMID from URL
            if "pubmed.ncbi.nlm.nih.gov" in result.get("url", ""):
                try:
                    pmid = result["url"].split("/")[-1].split("?")[0]
                    if pmid.isdigit():
                        result["pmid"] = pmid
                except:
                    pass
        
        return results
    
    async def search_case_reports(self, condition: str, age: str, gender: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """Search for case reports matching patient demographics"""
        queries = [
            f'"{condition}" "case report" "{age} year old" "{gender}"',
            f'"{condition}" "case study" "patient presentation"',
            f'"{condition}" "clinical case" "treatment outcome"'
        ]
        
        all_results = []
        for query in queries:
            results = await self.search_medical_literature(
                query,
                num_results=num_results,
                site_filter=["pubmed.ncbi.nlm.nih.gov", "nejm.org", "jamanetwork.com"]
            )
            all_results.extend(results)
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result["url"] not in seen_urls:
                seen_urls.add(result["url"])
                result["type"] = "Case Report"
                unique_results.append(result)
        
        return unique_results[:num_results]
    
    async def search_clinical_guidelines(self, condition: str, year: int = 2024) -> List[Dict[str, Any]]:
        """Search for current clinical guidelines"""
        query = f'"{condition}" "clinical guidelines" "{year}" OR "{year-1}"'
        
        results = await self.search_medical_literature(
            query,
            num_results=5,
            site_filter=["nice.org.uk", "guidelines.gov", "who.int", "cdc.gov", "nih.gov"]
        )
        
        for result in results:
            result["type"] = "Clinical Guideline"
        
        return results