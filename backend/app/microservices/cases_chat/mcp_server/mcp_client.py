"""
MCP Client for communicating with the Medical History Service
"""

import logging
import requests
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with the Medical Context Protocol (MCP) server"""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        """
        Initialize MCP client
        
        Args:
            host: MCP server host
            port: MCP server port
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        self.connected = True  # HTTP client is always "connected"
        self.async_session = None
        logger.info(f"MCP Client initialized for {self.base_url}")
    
    async def connect(self):
        """Initialize async session (no-op for compatibility)"""
        if not self.async_session:
            self.async_session = aiohttp.ClientSession()
        self.connected = True
    
    async def disconnect(self):
        """Close async session"""
        if self.async_session:
            await self.async_session.close()
            self.async_session = None
        self.connected = False
    
    async def find_similar_cases(
        self,
        case_id: str,
        similarity_threshold: float = 0.5,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar cases (async version)
        
        Args:
            case_id: Case ID to find similar cases for
            similarity_threshold: Minimum similarity score
            limit: Maximum number of results
            
        Returns:
            List of similar cases
        """
        if not self.async_session:
            await self.connect()
            
        try:
            async with self.async_session.post(
                f"{self.base_url}/find_similar_cases",
                json={
                    "case_id": case_id,
                    "similarity_threshold": similarity_threshold,
                    "limit": limit
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to find similar cases: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error finding similar cases: {e}")
            return []
    
    def get_case_context(self, case_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive case context from MCP server
        
        Args:
            case_id: Case ID
            user_id: User ID
            
        Returns:
            Case context including history, similar cases, and patterns
        """
        try:
            # Get case history
            history_response = self.session.post(
                f"{self.base_url}/get_case_history",
                json={
                    "case_id": case_id,
                    "user_id": user_id,
                    "include_chat": True,
                    "include_analysis": True
                },
                timeout=10
            )
            
            if history_response.status_code != 200:
                logger.warning(f"Failed to get case history: {history_response.status_code}")
                return None
            
            history = history_response.json()
            
            # Get similar cases
            similar_response = self.session.post(
                f"{self.base_url}/find_similar_cases",
                json={
                    "case_id": case_id,
                    "user_id": user_id,
                    "similarity_threshold": 0.5,
                    "limit": 5
                },
                timeout=10
            )
            
            similar_cases = []
            if similar_response.status_code == 200:
                similar_cases = similar_response.json()
            
            # Get symptom patterns
            patterns_response = self.session.post(
                f"{self.base_url}/analyze_patterns",
                json={
                    "user_id": user_id,
                    "pattern_type": "symptoms"
                },
                timeout=10
            )
            
            patterns = {}
            if patterns_response.status_code == 200:
                patterns = patterns_response.json()
            
            return {
                "case_history": history,
                "similar_cases": similar_cases,
                "symptom_patterns": patterns,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except requests.exceptions.Timeout:
            logger.error("MCP server timeout")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to MCP server")
            return None
        except Exception as e:
            logger.error(f"MCP client error: {e}")
            return None
    
    def search_cases(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search cases based on query and filters
        
        Args:
            user_id: User ID
            query: Search query
            filters: Optional filters (status, priority, etc.)
            limit: Maximum results
            
        Returns:
            List of matching cases
        """
        try:
            response = self.session.post(
                f"{self.base_url}/search_cases",
                json={
                    "user_id": user_id,
                    "query": query,
                    "filters": filters or {},
                    "limit": limit
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_patient_timeline(
        self,
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get patient's medical timeline
        
        Args:
            user_id: User ID
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
            
        Returns:
            Timeline of medical events
        """
        try:
            response = self.session.post(
                f"{self.base_url}/get_patient_timeline",
                json={
                    "user_id": user_id,
                    "date_from": date_from,
                    "date_to": date_to
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Timeline retrieval failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Timeline error: {e}")
            return []
    
    def get_case_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get case statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Statistics dictionary
        """
        try:
            response = self.session.post(
                f"{self.base_url}/get_case_statistics",
                json={"user_id": user_id},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Statistics retrieval failed: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Statistics error: {e}")
            return {}
    
    def health_check(self) -> bool:
        """
        Check if MCP server is healthy
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class AsyncMCPClient(MCPClient):
    """Fully async MCP client for async-first applications"""
    
    async def send_request(self, method: str, params: Optional[Dict] = None) -> Any:
        """Send async request to MCP server"""
        if not self.async_session:
            await self.connect()
            
        try:
            async with self.async_session.post(
                f"{self.base_url}/{method}",
                json=params or {},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Request failed with status {response.status}")
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def search_cases(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Async version of search_cases"""
        return await self.send_request("search_cases", {
            "user_id": user_id,
            "query": query,
            "limit": limit
        })


class MCPConnection:
    """Async context manager for MCP connections"""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.client = AsyncMCPClient(host, port)
    
    async def __aenter__(self):
        await self.client.connect()
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()