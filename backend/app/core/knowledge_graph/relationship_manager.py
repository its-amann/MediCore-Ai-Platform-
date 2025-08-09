"""
Relationship Manager - Handles specific relationship operations
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from enum import Enum

from neo4j.exceptions import Neo4jError

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """Enumeration of all relationship types in the knowledge graph"""
    # User relationships
    OWNS = "OWNS"  # User -> Case
    OWNED_BY = "OWNED_BY"  # Case -> User
    
    # Case relationships
    HAS_REPORT = "HAS_REPORT"  # Case -> MedicalReport
    HAS_CHAT_SESSION = "HAS_CHAT_SESSION"  # Case -> ChatSession
    
    # Report relationships
    BELONGS_TO_CASE = "BELONGS_TO_CASE"  # MedicalReport -> Case
    CITES = "CITES"  # MedicalReport -> Citation
    HAS_FINDING = "HAS_FINDING"  # MedicalReport -> Finding
    ANALYZED_IMAGE = "ANALYZED_IMAGE"  # MedicalReport -> ImageAnalysis
    
    # Chat relationships
    HAS_MESSAGE = "HAS_MESSAGE"  # ChatSession -> ChatMessage
    
    # Cross-entity relationships
    RELATED_TO = "RELATED_TO"  # Case -> Case
    FOLLOW_UP_OF = "FOLLOW_UP_OF"  # Case -> Case
    REFERS_TO = "REFERS_TO"  # MedicalReport -> MedicalReport


class RelationshipManager:
    """
    Manages complex relationship operations in the knowledge graph
    """
    
    def __init__(self, knowledge_graph_service):
        """
        Initialize with reference to knowledge graph service
        
        Args:
            knowledge_graph_service: KnowledgeGraphService instance
        """
        self.kg_service = knowledge_graph_service
        logger.info("Relationship Manager initialized")
    
    async def create_relationship(
        self,
        from_node_type: str,
        from_node_id: str,
        to_node_type: str,
        to_node_id: str,
        relationship_type: RelationshipType,
        properties: Optional[Dict[str, Any]] = None,
        bidirectional: bool = False,
        reverse_type: Optional[RelationshipType] = None
    ) -> bool:
        """
        Create a relationship between two nodes
        
        Args:
            from_node_type: Type of source node (e.g., 'User', 'Case')
            from_node_id: ID of source node
            to_node_type: Type of target node
            to_node_id: ID of target node
            relationship_type: Type of relationship
            properties: Optional relationship properties
            bidirectional: Whether to create reverse relationship
            reverse_type: Type for reverse relationship (if different)
            
        Returns:
            True if successful
        """
        async with self.kg_service.get_session() as session:
            try:
                # Determine ID fields based on node types
                id_fields = {
                    'User': 'user_id',
                    'Case': 'case_id',
                    'MedicalReport': 'id',
                    'ChatSession': 'session_id',
                    'ChatMessage': 'id',
                    'Finding': 'id',
                    'Citation': 'id',
                    'ImageAnalysis': 'id'
                }
                
                from_id_field = id_fields.get(from_node_type, 'id')
                to_id_field = id_fields.get(to_node_type, 'id')
                
                # Build properties string
                props_str = ""
                if properties:
                    props_items = [f"{k}: ${k}" for k in properties.keys()]
                    props_str = "{" + ", ".join(props_items) + "}"
                
                # Create main relationship
                query = f"""
                    MATCH (from:{from_node_type} {{{from_id_field}: $from_id}})
                    MATCH (to:{to_node_type} {{{to_id_field}: $to_id}})
                    MERGE (from)-[r:{relationship_type.value} {props_str}]->(to)
                    RETURN from, to, r
                """
                
                params = {
                    "from_id": from_node_id,
                    "to_id": to_node_id
                }
                if properties:
                    params.update(properties)
                
                result = await session.run(query, **params)
                record = await result.single()
                
                if not record:
                    logger.error(f"Failed to create relationship: {from_node_type}({from_node_id}) -> {to_node_type}({to_node_id})")
                    return False
                
                # Create reverse relationship if requested
                if bidirectional:
                    rev_type = reverse_type or self._get_reverse_relationship_type(relationship_type)
                    if rev_type:
                        reverse_query = f"""
                            MATCH (from:{to_node_type} {{{to_id_field}: $to_id}})
                            MATCH (to:{from_node_type} {{{from_id_field}: $from_id}})
                            MERGE (from)-[r:{rev_type.value}]->(to)
                            RETURN r
                        """
                        await session.run(reverse_query, from_id=from_node_id, to_id=to_node_id)
                
                logger.info(f"Created relationship: {from_node_type}({from_node_id}) -[{relationship_type.value}]-> {to_node_type}({to_node_id})")
                return True
                
            except Neo4jError as e:
                logger.error(f"Error creating relationship: {e}")
                return False
    
    def _get_reverse_relationship_type(self, relationship_type: RelationshipType) -> Optional[RelationshipType]:
        """Get the reverse relationship type for bidirectional relationships"""
        reverse_map = {
            RelationshipType.OWNS: RelationshipType.OWNED_BY,
            RelationshipType.OWNED_BY: RelationshipType.OWNS,
            RelationshipType.HAS_REPORT: RelationshipType.BELONGS_TO_CASE,
            RelationshipType.BELONGS_TO_CASE: RelationshipType.HAS_REPORT,
            RelationshipType.HAS_CHAT_SESSION: RelationshipType.BELONGS_TO_CASE,
        }
        return reverse_map.get(relationship_type)
    
    async def create_case_relationships(
        self,
        case_id: str,
        user_id: str,
        related_case_ids: Optional[List[str]] = None,
        relationship_type: str = "RELATED_TO"
    ) -> bool:
        """
        Create all necessary relationships for a new case
        
        Args:
            case_id: Case ID
            user_id: User ID who owns the case
            related_case_ids: Optional list of related case IDs
            relationship_type: Type of relationship to related cases
            
        Returns:
            True if all relationships created successfully
        """
        success = True
        
        # Create User-Case relationship
        user_case_success = await self.kg_service.ensure_user_case_relationship(
            user_id, case_id, create_user_if_missing=True
        )
        success = success and user_case_success
        
        # Create relationships to related cases
        if related_case_ids:
            for related_id in related_case_ids:
                rel_success = await self.create_relationship(
                    'Case', case_id,
                    'Case', related_id,
                    RelationshipType.RELATED_TO,
                    properties={"created_at": datetime.utcnow().isoformat()},
                    bidirectional=True
                )
                success = success and rel_success
        
        return success
    
    async def link_report_to_case(
        self,
        report_id: str,
        case_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Link a medical report to a case with all necessary relationships
        
        Args:
            report_id: Report ID
            case_id: Case ID
            user_id: Optional user ID for verification
            
        Returns:
            True if successful
        """
        # Use the knowledge graph service method
        return await self.kg_service.create_case_report_relationship(
            case_id, report_id, user_id
        )
    
    async def get_relationship_graph(
        self,
        node_type: str,
        node_id: str,
        depth: int = 2,
        relationship_types: Optional[List[RelationshipType]] = None
    ) -> Dict[str, Any]:
        """
        Get a subgraph of relationships starting from a node
        
        Args:
            node_type: Type of starting node
            node_id: ID of starting node
            depth: How many relationship hops to traverse
            relationship_types: Optional filter for relationship types
            
        Returns:
            Graph data with nodes and relationships
        """
        async with self.kg_service.get_session() as session:
            try:
                # Build relationship filter
                rel_filter = ""
                if relationship_types:
                    rel_types = "|".join([rt.value for rt in relationship_types])
                    rel_filter = f":{rel_types}"
                
                # Determine ID field
                id_fields = {
                    'User': 'user_id',
                    'Case': 'case_id',
                    'MedicalReport': 'id',
                    'ChatSession': 'session_id'
                }
                id_field = id_fields.get(node_type, 'id')
                
                # Query for subgraph
                query = f"""
                    MATCH path = (start:{node_type} {{{id_field}: $node_id}})-[r{rel_filter}*1..{depth}]-(connected)
                    WITH start, relationships(path) as rels, nodes(path) as nodes
                    UNWIND rels as rel
                    WITH start, collect(DISTINCT rel) as relationships, collect(DISTINCT nodes) as all_nodes
                    UNWIND all_nodes as node_list
                    UNWIND node_list as node
                    WITH start, relationships, collect(DISTINCT node) as nodes
                    RETURN start, nodes, relationships
                """
                
                result = await session.run(query, node_id=node_id)
                record = await result.single()
                
                if not record:
                    return {
                        "start_node": None,
                        "nodes": [],
                        "relationships": [],
                        "statistics": {"node_count": 0, "relationship_count": 0}
                    }
                
                # Format response
                start_node = dict(record["start"])
                nodes = [dict(n) for n in record["nodes"]]
                relationships = []
                
                for rel in record["relationships"]:
                    rel_data = {
                        "type": rel.type,
                        "start_node": rel.start_node.element_id,
                        "end_node": rel.end_node.element_id,
                        "properties": dict(rel)
                    }
                    relationships.append(rel_data)
                
                return {
                    "start_node": start_node,
                    "nodes": nodes,
                    "relationships": relationships,
                    "statistics": {
                        "node_count": len(nodes),
                        "relationship_count": len(relationships)
                    }
                }
                
            except Neo4jError as e:
                logger.error(f"Error getting relationship graph: {e}")
                return {
                    "start_node": None,
                    "nodes": [],
                    "relationships": [],
                    "error": str(e)
                }
    
    async def find_connection_path(
        self,
        from_node_type: str,
        from_node_id: str,
        to_node_type: str,
        to_node_id: str,
        max_depth: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find the shortest path between two nodes
        
        Args:
            from_node_type: Type of source node
            from_node_id: ID of source node
            to_node_type: Type of target node
            to_node_id: ID of target node
            max_depth: Maximum path length
            
        Returns:
            Path as list of nodes and relationships, or None
        """
        async with self.kg_service.get_session() as session:
            try:
                # Determine ID fields
                id_fields = {
                    'User': 'user_id',
                    'Case': 'case_id',
                    'MedicalReport': 'id',
                    'ChatSession': 'session_id'
                }
                from_id_field = id_fields.get(from_node_type, 'id')
                to_id_field = id_fields.get(to_node_type, 'id')
                
                query = f"""
                    MATCH (from:{from_node_type} {{{from_id_field}: $from_id}})
                    MATCH (to:{to_node_type} {{{to_id_field}: $to_id}})
                    MATCH path = shortestPath((from)-[*..{max_depth}]-(to))
                    RETURN path
                """
                
                result = await session.run(
                    query,
                    from_id=from_node_id,
                    to_id=to_node_id
                )
                record = await result.single()
                
                if not record:
                    return None
                
                # Extract path information
                path = record["path"]
                path_data = []
                
                for i, node in enumerate(path.nodes):
                    path_data.append({
                        "type": "node",
                        "labels": list(node.labels),
                        "properties": dict(node)
                    })
                    
                    if i < len(path.relationships):
                        rel = path.relationships[i]
                        path_data.append({
                            "type": "relationship",
                            "relationship_type": rel.type,
                            "properties": dict(rel)
                        })
                
                return path_data
                
            except Neo4jError as e:
                logger.error(f"Error finding connection path: {e}")
                return None
    
    async def get_related_entities(
        self,
        node_type: str,
        node_id: str,
        target_types: Optional[List[str]] = None,
        relationship_types: Optional[List[RelationshipType]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all entities related to a given node
        
        Args:
            node_type: Type of source node
            node_id: ID of source node
            target_types: Optional filter for target node types
            relationship_types: Optional filter for relationship types
            
        Returns:
            Dictionary mapping entity types to lists of related entities
        """
        async with self.kg_service.get_session() as session:
            try:
                # Determine ID field
                id_fields = {
                    'User': 'user_id',
                    'Case': 'case_id',
                    'MedicalReport': 'id',
                    'ChatSession': 'session_id',
                    'ChatMessage': 'id'
                }
                id_field = id_fields.get(node_type, 'id')
                
                # Build filters
                rel_filter = ""
                if relationship_types:
                    rel_types = "|".join([rt.value for rt in relationship_types])
                    rel_filter = f":{rel_types}"
                
                node_filter = ""
                if target_types:
                    node_labels = "|".join(target_types)
                    node_filter = f":{node_labels}"
                
                query = f"""
                    MATCH (source:{node_type} {{{id_field}: $node_id}})
                    MATCH (source)-[r{rel_filter}]-(target{node_filter})
                    WITH labels(target)[0] as target_type, 
                         target, 
                         type(r) as rel_type,
                         CASE 
                            WHEN startNode(r) = source THEN 'outgoing'
                            ELSE 'incoming'
                         END as direction
                    RETURN target_type, 
                           collect(DISTINCT {{
                               node: target,
                               relationship_type: rel_type,
                               direction: direction
                           }}) as related
                """
                
                result = await session.run(query, node_id=node_id)
                
                related_entities = {}
                async for record in result:
                    target_type = record["target_type"]
                    related = []
                    
                    for item in record["related"]:
                        entity = dict(item["node"])
                        entity["_relationship_type"] = item["relationship_type"]
                        entity["_relationship_direction"] = item["direction"]
                        related.append(entity)
                    
                    related_entities[target_type] = related
                
                return related_entities
                
            except Neo4jError as e:
                logger.error(f"Error getting related entities: {e}")
                return {}