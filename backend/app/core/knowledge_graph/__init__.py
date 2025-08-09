"""
Knowledge Graph Module - Unified relationship management across microservices
"""

from .knowledge_graph_service import KnowledgeGraphService
from .relationship_manager import RelationshipManager
from .graph_validator import GraphValidator

# Singleton instance
_knowledge_graph_service = None

def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Get or create the singleton knowledge graph service instance"""
    global _knowledge_graph_service
    if _knowledge_graph_service is None:
        # Create the service - it will use settings for connection
        _knowledge_graph_service = KnowledgeGraphService()
    return _knowledge_graph_service

__all__ = [
    'KnowledgeGraphService',
    'RelationshipManager',
    'GraphValidator',
    'get_knowledge_graph_service'
]