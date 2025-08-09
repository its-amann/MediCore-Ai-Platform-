"""
Graph Validator - Validates and repairs the knowledge graph structure
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict

from neo4j.exceptions import Neo4jError

logger = logging.getLogger(__name__)


class GraphValidator:
    """
    Validates the integrity of the medical knowledge graph
    """
    
    def __init__(self, knowledge_graph_service):
        """
        Initialize with reference to knowledge graph service
        
        Args:
            knowledge_graph_service: KnowledgeGraphService instance
        """
        self.kg_service = knowledge_graph_service
        logger.info("Graph Validator initialized")
    
    async def run_full_validation(
        self,
        fix_issues: bool = False,
        detailed_report: bool = True
    ) -> Dict[str, Any]:
        """
        Run comprehensive validation of the entire knowledge graph
        
        Args:
            fix_issues: Whether to automatically fix found issues
            detailed_report: Include detailed information about each issue
            
        Returns:
            Comprehensive validation report
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_checks": [],
            "issues_by_type": defaultdict(list),
            "fixes_applied": [],
            "statistics": {},
            "recommendations": []
        }
        
        # Run validation checks
        checks = [
            self._validate_node_integrity,
            self._validate_relationships,
            self._validate_bidirectional_relationships,
            self._validate_data_consistency,
            self._validate_orphaned_nodes,
            self._validate_duplicate_relationships,
            self._validate_required_properties
        ]
        
        for check_func in checks:
            check_name = check_func.__name__.replace('_validate_', '')
            logger.info(f"Running validation check: {check_name}")
            
            try:
                check_result = await check_func(fix_issues, detailed_report)
                report["validation_checks"].append({
                    "check": check_name,
                    "status": "completed",
                    "result": check_result
                })
                
                # Aggregate issues
                if "issues" in check_result:
                    for issue in check_result["issues"]:
                        report["issues_by_type"][issue["type"]].append(issue)
                
                # Aggregate fixes
                if "fixes" in check_result:
                    report["fixes_applied"].extend(check_result["fixes"])
                    
            except Exception as e:
                logger.error(f"Error in validation check {check_name}: {e}")
                report["validation_checks"].append({
                    "check": check_name,
                    "status": "error",
                    "error": str(e)
                })
        
        # Generate statistics and recommendations
        report["statistics"] = await self._generate_statistics()
        report["recommendations"] = self._generate_recommendations(report)
        
        return report
    
    async def _validate_node_integrity(
        self,
        fix_issues: bool,
        detailed: bool
    ) -> Dict[str, Any]:
        """Validate that all nodes have required properties"""
        async with self.kg_service.get_session() as session:
            result = {"issues": [], "fixes": []}
            
            # Define required properties for each node type
            required_properties = {
                "User": ["user_id"],
                "Case": ["case_id", "user_id", "status", "created_at"],
                "MedicalReport": ["id", "caseId", "createdAt"],
                "ChatSession": ["session_id", "case_id", "created_at"],
                "ChatMessage": ["id", "session_id", "case_id", "role", "content"]
            }
            
            for node_type, properties in required_properties.items():
                # Check for missing properties
                for prop in properties:
                    query = f"""
                        MATCH (n:{node_type})
                        WHERE n.{prop} IS NULL
                        RETURN n, id(n) as node_id
                        LIMIT 100
                    """
                    
                    nodes = await session.run(query)
                    async for record in nodes:
                        node = dict(record["n"])
                        issue = {
                            "type": "missing_property",
                            "node_type": node_type,
                            "node_id": record["node_id"],
                            "property": prop,
                            "node_data": node if detailed else None
                        }
                        result["issues"].append(issue)
                        
                        if fix_issues and prop == "created_at":
                            # Fix missing created_at
                            fix_query = f"""
                                MATCH (n:{node_type})
                                WHERE id(n) = $node_id
                                SET n.created_at = datetime()
                                RETURN n
                            """
                            await session.run(fix_query, node_id=record["node_id"])
                            result["fixes"].append(issue)
            
            return result
    
    async def _validate_relationships(
        self,
        fix_issues: bool,
        detailed: bool
    ) -> Dict[str, Any]:
        """Validate that relationships connect to correct node types"""
        async with self.kg_service.get_session() as session:
            result = {"issues": [], "fixes": []}
            
            # Define expected node types for relationships
            expected_relationships = {
                "OWNS": ("User", "Case"),
                "OWNED_BY": ("Case", "User"),
                "HAS_REPORT": ("Case", "MedicalReport"),
                "BELONGS_TO_CASE": ("MedicalReport", "Case"),
                "HAS_CHAT_SESSION": ("Case", "ChatSession"),
                "HAS_MESSAGE": ("ChatSession", "ChatMessage")
            }
            
            for rel_type, (expected_from, expected_to) in expected_relationships.items():
                # Check for incorrect node types
                query = f"""
                    MATCH (from)-[r:{rel_type}]->(to)
                    WHERE NOT (from:{expected_from} AND to:{expected_to})
                    RETURN from, to, r, labels(from) as from_labels, labels(to) as to_labels
                    LIMIT 50
                """
                
                invalid_rels = await session.run(query)
                async for record in invalid_rels:
                    issue = {
                        "type": "invalid_relationship",
                        "relationship_type": rel_type,
                        "from_labels": record["from_labels"],
                        "to_labels": record["to_labels"],
                        "expected": f"{expected_from} -> {expected_to}"
                    }
                    result["issues"].append(issue)
            
            return result
    
    async def _validate_bidirectional_relationships(
        self,
        fix_issues: bool,
        detailed: bool
    ) -> Dict[str, Any]:
        """Validate that bidirectional relationships are properly maintained"""
        async with self.kg_service.get_session() as session:
            result = {"issues": [], "fixes": []}
            
            # Check User <-> Case relationships
            missing_reverse = await session.run("""
                MATCH (u:User)-[:OWNS]->(c:Case)
                WHERE NOT (c)-[:OWNED_BY]->(u)
                RETURN u.user_id as user_id, c.case_id as case_id
                LIMIT 100
            """)
            
            async for record in missing_reverse:
                issue = {
                    "type": "missing_bidirectional",
                    "relationship": "User-Case",
                    "user_id": record["user_id"],
                    "case_id": record["case_id"]
                }
                result["issues"].append(issue)
                
                if fix_issues:
                    # Create missing reverse relationship
                    await session.run("""
                        MATCH (u:User {user_id: $user_id})
                        MATCH (c:Case {case_id: $case_id})
                        MERGE (c)-[:OWNED_BY]->(u)
                    """, user_id=record["user_id"], case_id=record["case_id"])
                    result["fixes"].append(issue)
            
            # Check Case <-> Report relationships
            missing_report_reverse = await session.run("""
                MATCH (c:Case)-[:HAS_REPORT]->(r:MedicalReport)
                WHERE NOT (r)-[:BELONGS_TO_CASE]->(c)
                RETURN c.case_id as case_id, r.id as report_id
                LIMIT 100
            """)
            
            async for record in missing_report_reverse:
                issue = {
                    "type": "missing_bidirectional",
                    "relationship": "Case-Report",
                    "case_id": record["case_id"],
                    "report_id": record["report_id"]
                }
                result["issues"].append(issue)
                
                if fix_issues:
                    await session.run("""
                        MATCH (c:Case {case_id: $case_id})
                        MATCH (r:MedicalReport {id: $report_id})
                        MERGE (r)-[:BELONGS_TO_CASE]->(c)
                    """, case_id=record["case_id"], report_id=record["report_id"])
                    result["fixes"].append(issue)
            
            return result
    
    async def _validate_data_consistency(
        self,
        fix_issues: bool,
        detailed: bool
    ) -> Dict[str, Any]:
        """Validate data consistency across related nodes"""
        async with self.kg_service.get_session() as session:
            result = {"issues": [], "fixes": []}
            
            # Check Case user_id matches User relationship
            mismatched_users = await session.run("""
                MATCH (u:User)-[:OWNS]->(c:Case)
                WHERE c.user_id <> u.user_id
                RETURN u.user_id as actual_user, c.case_id as case_id, c.user_id as case_user
                LIMIT 50
            """)
            
            async for record in mismatched_users:
                issue = {
                    "type": "data_inconsistency",
                    "entity": "Case",
                    "case_id": record["case_id"],
                    "field": "user_id",
                    "expected": record["actual_user"],
                    "actual": record["case_user"]
                }
                result["issues"].append(issue)
                
                if fix_issues:
                    # Fix case user_id
                    await session.run("""
                        MATCH (c:Case {case_id: $case_id})
                        SET c.user_id = $correct_user
                    """, case_id=record["case_id"], correct_user=record["actual_user"])
                    result["fixes"].append(issue)
            
            # Check Report caseId matches Case relationship
            mismatched_cases = await session.run("""
                MATCH (c:Case)-[:HAS_REPORT]->(r:MedicalReport)
                WHERE r.caseId <> c.case_id
                RETURN c.case_id as actual_case, r.id as report_id, r.caseId as report_case
                LIMIT 50
            """)
            
            async for record in mismatched_cases:
                issue = {
                    "type": "data_inconsistency",
                    "entity": "MedicalReport",
                    "report_id": record["report_id"],
                    "field": "caseId",
                    "expected": record["actual_case"],
                    "actual": record["report_case"]
                }
                result["issues"].append(issue)
                
                if fix_issues:
                    await session.run("""
                        MATCH (r:MedicalReport {id: $report_id})
                        SET r.caseId = $correct_case
                    """, report_id=record["report_id"], correct_case=record["actual_case"])
                    result["fixes"].append(issue)
            
            return result
    
    async def _validate_orphaned_nodes(
        self,
        fix_issues: bool,
        detailed: bool
    ) -> Dict[str, Any]:
        """Check for orphaned nodes without proper relationships"""
        async with self.kg_service.get_session() as session:
            result = {"issues": [], "fixes": []}
            
            # Orphaned Cases (no User relationship)
            orphan_cases = await session.run("""
                MATCH (c:Case)
                WHERE NOT (c)<-[:OWNS]-(:User)
                RETURN c.case_id as case_id, c.user_id as user_id
                LIMIT 100
            """)
            
            async for record in orphan_cases:
                issue = {
                    "type": "orphaned_node",
                    "node_type": "Case",
                    "case_id": record["case_id"],
                    "user_id": record["user_id"]
                }
                result["issues"].append(issue)
                
                if fix_issues and record["user_id"]:
                    # Create user and relationship
                    fixed = await self.kg_service.ensure_user_case_relationship(
                        record["user_id"],
                        record["case_id"],
                        create_user_if_missing=True
                    )
                    if fixed:
                        result["fixes"].append(issue)
            
            # Orphaned Reports (no Case relationship)
            orphan_reports = await session.run("""
                MATCH (r:MedicalReport)
                WHERE NOT (r)<-[:HAS_REPORT]-(:Case)
                AND r.caseId IS NOT NULL
                RETURN r.id as report_id, r.caseId as case_id
                LIMIT 100
            """)
            
            async for record in orphan_reports:
                issue = {
                    "type": "orphaned_node",
                    "node_type": "MedicalReport",
                    "report_id": record["report_id"],
                    "case_id": record["case_id"]
                }
                result["issues"].append(issue)
                
                if fix_issues and record["case_id"]:
                    # Check if case exists
                    case_exists = await session.run("""
                        MATCH (c:Case {case_id: $case_id})
                        RETURN c
                    """, case_id=record["case_id"])
                    
                    if await case_exists.single():
                        fixed = await self.kg_service.create_case_report_relationship(
                            record["case_id"],
                            record["report_id"]
                        )
                        if fixed:
                            result["fixes"].append(issue)
            
            # Orphaned ChatSessions
            orphan_sessions = await session.run("""
                MATCH (s:ChatSession)
                WHERE NOT (s)<-[:HAS_CHAT_SESSION]-(:Case)
                RETURN s.session_id as session_id, s.case_id as case_id
                LIMIT 100
            """)
            
            async for record in orphan_sessions:
                issue = {
                    "type": "orphaned_node",
                    "node_type": "ChatSession",
                    "session_id": record["session_id"],
                    "case_id": record["case_id"]
                }
                result["issues"].append(issue)
                
                if fix_issues and record["case_id"]:
                    fixed = await self.kg_service.ensure_session_case_relationship(
                        record["session_id"],
                        record["case_id"]
                    )
                    if fixed:
                        result["fixes"].append(issue)
            
            return result
    
    async def _validate_duplicate_relationships(
        self,
        fix_issues: bool,
        detailed: bool
    ) -> Dict[str, Any]:
        """Check for duplicate relationships between nodes"""
        async with self.kg_service.get_session() as session:
            result = {"issues": [], "fixes": []}
            
            # Check for duplicate OWNS relationships
            duplicates = await session.run("""
                MATCH (u:User)-[r:OWNS]->(c:Case)
                WITH u, c, count(r) as rel_count
                WHERE rel_count > 1
                MATCH (u)-[r:OWNS]->(c)
                RETURN u.user_id as user_id, c.case_id as case_id, id(r) as rel_id
            """)
            
            seen_pairs = set()
            async for record in duplicates:
                pair = (record["user_id"], record["case_id"])
                if pair in seen_pairs:
                    issue = {
                        "type": "duplicate_relationship",
                        "relationship_type": "OWNS",
                        "user_id": record["user_id"],
                        "case_id": record["case_id"],
                        "rel_id": record["rel_id"]
                    }
                    result["issues"].append(issue)
                    
                    if fix_issues:
                        # Delete duplicate relationship
                        await session.run("""
                            MATCH ()-[r]->()
                            WHERE id(r) = $rel_id
                            DELETE r
                        """, rel_id=record["rel_id"])
                        result["fixes"].append(issue)
                else:
                    seen_pairs.add(pair)
            
            return result
    
    async def _validate_required_properties(
        self,
        fix_issues: bool,
        detailed: bool
    ) -> Dict[str, Any]:
        """Validate that nodes have all required properties with valid values"""
        async with self.kg_service.get_session() as session:
            result = {"issues": [], "fixes": []}
            
            # Check for empty or invalid values
            checks = [
                ("Case", "status", ["active", "closed", "archived"]),
                ("Case", "priority", ["low", "medium", "high", "critical"]),
                ("ChatMessage", "role", ["user", "assistant", "system"]),
                ("MedicalReport", "status", ["draft", "completed", "error"])
            ]
            
            for node_type, property_name, valid_values in checks:
                query = f"""
                    MATCH (n:{node_type})
                    WHERE n.{property_name} IS NULL 
                       OR NOT n.{property_name} IN $valid_values
                    RETURN n, id(n) as node_id
                    LIMIT 50
                """
                
                invalid_nodes = await session.run(query, valid_values=valid_values)
                async for record in invalid_nodes:
                    node = dict(record["n"])
                    issue = {
                        "type": "invalid_property_value",
                        "node_type": node_type,
                        "node_id": record["node_id"],
                        "property": property_name,
                        "current_value": node.get(property_name),
                        "valid_values": valid_values
                    }
                    result["issues"].append(issue)
                    
                    if fix_issues:
                        # Set default value
                        default_value = valid_values[0]
                        await session.run(f"""
                            MATCH (n:{node_type})
                            WHERE id(n) = $node_id
                            SET n.{property_name} = $default_value
                        """, node_id=record["node_id"], default_value=default_value)
                        result["fixes"].append(issue)
            
            return result
    
    async def _generate_statistics(self) -> Dict[str, Any]:
        """Generate graph statistics"""
        async with self.kg_service.get_session() as session:
            stats = {}
            
            # Count nodes by type
            node_counts = await session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            
            stats["nodes"] = {}
            async for record in node_counts:
                stats["nodes"][record["label"]] = record["count"]
            
            # Count relationships by type
            rel_counts = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            
            stats["relationships"] = {}
            async for record in rel_counts:
                stats["relationships"][record["type"]] = record["count"]
            
            # Get graph density metrics
            total_nodes = sum(stats["nodes"].values())
            total_relationships = sum(stats["relationships"].values())
            
            stats["metrics"] = {
                "total_nodes": total_nodes,
                "total_relationships": total_relationships,
                "avg_relationships_per_node": total_relationships / max(total_nodes, 1)
            }
            
            return stats
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check for high number of orphaned nodes
        orphan_count = len(report["issues_by_type"].get("orphaned_node", []))
        if orphan_count > 10:
            recommendations.append(
                f"High number of orphaned nodes ({orphan_count}). "
                "Consider running repair with fix_issues=True"
            )
        
        # Check for missing bidirectional relationships
        bidir_count = len(report["issues_by_type"].get("missing_bidirectional", []))
        if bidir_count > 0:
            recommendations.append(
                f"Found {bidir_count} missing bidirectional relationships. "
                "This may affect graph traversal performance"
            )
        
        # Check for data inconsistencies
        inconsistency_count = len(report["issues_by_type"].get("data_inconsistency", []))
        if inconsistency_count > 0:
            recommendations.append(
                f"Found {inconsistency_count} data inconsistencies. "
                "These should be fixed to ensure data integrity"
            )
        
        # Check for duplicate relationships
        duplicate_count = len(report["issues_by_type"].get("duplicate_relationship", []))
        if duplicate_count > 0:
            recommendations.append(
                f"Found {duplicate_count} duplicate relationships. "
                "Remove duplicates to improve performance"
            )
        
        # General recommendation if no issues
        if not report["issues_by_type"]:
            recommendations.append("Knowledge graph is in good health!")
        
        return recommendations