"""
Neo4j Storage Service for Medical Imaging Reports
Handles persistent storage of reports, embeddings, and similarity search
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from uuid import uuid4

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from app.core.config import settings
from .neo4j_utils import sanitize_neo4j_record, ensure_user_fields
from app.microservices.medical_imaging.models import (
    ImagingReport,
    ImageAnalysis,
    ReportStatus,
    ImageType
)
from app.core.knowledge_graph import get_knowledge_graph_service

logger = logging.getLogger(__name__)


class Neo4jReportStorageService:
    """
    Service for storing and retrieving medical imaging reports in Neo4j
    with vector embeddings for similarity search
    """
    
    def __init__(self):
        """Initialize Neo4j connection"""
        self.uri = settings.neo4j_uri
        self.username = settings.neo4j_user
        self.password = settings.neo4j_password
        self.database = getattr(settings, 'neo4j_database', 'neo4j')
        self.driver = None
        self.embedding_dimension = 768  # Updated to match actual embedding model dimension
        self.kg_service = None  # Will be initialized on connect
        
        logger.info("Neo4j Report Storage Service initialized")
    
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            # Try to use unified database manager first
            try:
                from app.core.services.database_manager import unified_db_manager
                
                # Check if already connected
                if unified_db_manager.is_connected_sync():
                    self.driver = unified_db_manager.get_sync_driver()
                    logger.info("Using existing shared Neo4j connection from unified database manager")
                else:
                    # Connect the unified database manager
                    logger.info("Unified database manager not connected. Attempting to connect...")
                    driver = unified_db_manager.connect_sync()
                    if driver:
                        self.driver = driver
                        logger.info("Successfully connected using unified database manager")
                    else:
                        raise Exception("Failed to connect unified database manager")
                
                # Verify we have a working driver
                if not self.driver:
                    raise Exception("No driver available from unified database manager")
                    
            except Exception as e:
                logger.warning(f"Could not use unified database manager: {e}")
                # Fallback to direct connection
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password)
                )
                logger.info("Using direct Neo4j connection")
            
            # Verify connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record['test'] == 1:
                    logger.info("Neo4j connection verified successfully")
            
            # Create indexes if they don't exist
            self._create_indexes()
            
            # Initialize knowledge graph service
            try:
                self.kg_service = get_knowledge_graph_service()
            except Exception as kg_error:
                logger.warning(f"Could not initialize knowledge graph service: {kg_error}")
                self.kg_service = None
            
            logger.info("Neo4j Report Storage connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            # Fallback - try direct connection one more time
            try:
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password)
                )
                with self.driver.session(database=self.database) as session:
                    session.run("RETURN 1")
                logger.info("Fallback direct connection successful")
                self._create_indexes()
            except:
                logger.error("All connection attempts failed - service will work without Neo4j")
                self.driver = None
    
    def disconnect(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    def _create_indexes(self):
        """Create necessary indexes and constraints"""
        with self.driver.session(database=self.database) as session:
            try:
                # Create unique constraint on report ID
                session.run("""
                    CREATE CONSTRAINT report_id_unique IF NOT EXISTS
                    FOR (r:MedicalReport) REQUIRE r.id IS UNIQUE
                """)
                
                # Create index on patient ID
                session.run("""
                    CREATE INDEX patient_id_index IF NOT EXISTS
                    FOR (r:MedicalReport) ON (r.patientId)
                """)
                
                # Create index on creation date
                session.run("""
                    CREATE INDEX created_at_index IF NOT EXISTS
                    FOR (r:MedicalReport) ON (r.createdAt)
                """)
                
                # Create index on study type
                session.run("""
                    CREATE INDEX study_type_index IF NOT EXISTS
                    FOR (r:MedicalReport) ON (r.studyType)
                """)
                
                logger.info("Neo4j indexes created successfully")
            except Exception as e:
                logger.warning(f"Error creating indexes (may already exist): {e}")
    
    def save_report(
        self,
        report: ImagingReport,
        embeddings: Optional[Dict[str, List[float]]] = None
    ) -> str:
        """
        Save a medical imaging report to Neo4j with embeddings
        
        Args:
            report: ImagingReport object to save
            embeddings: Dictionary containing embeddings for different sections
                       Keys: 'summary', 'findings', 'full_report'
                       
        Returns:
            Report ID
        """
        # Check if Neo4j is available
        if not self.driver:
            logger.warning("Neo4j not available - skipping report storage")
            return report.report_id
            
        with self.driver.session(database=self.database) as session:
            try:
                # Extract patient info from report or create defaults
                patient_info = getattr(report, 'patient_info', {})
                if not patient_info:
                    # Try to extract from case_id
                    patient_info = {
                        'patient_id': f'patient_{report.case_id}',
                        'name': 'Unknown Patient',
                        'age': 0,
                        'gender': 'unknown'
                    }
                
                # Extract study info from images or create defaults
                study_info = getattr(report, 'study_info', {})
                if not study_info:
                    # Extract modality from images
                    modalities = set()
                    if report.images:
                        for img in report.images:
                            if hasattr(img, 'image_type'):
                                modalities.add(str(img.image_type.value if hasattr(img.image_type, 'value') else img.image_type))
                    study_info = {
                        'modality': '/'.join(modalities) if modalities else 'CT',
                        'study_date': datetime.now().isoformat()
                    }
                
                # Map field names appropriately
                radiological_analysis = getattr(report, 'radiological_analysis', report.overall_analysis)
                image_analyses = getattr(report, 'image_analyses', report.images)
                severity = getattr(report, 'severity', 'routine')
                key_findings = getattr(report, 'key_findings', [])
                
                # If no key findings, extract from overall analysis
                if not key_findings and report.overall_analysis:
                    sentences = report.overall_analysis.split('.')[:3]
                    key_findings = [s.strip() for s in sentences if s.strip()]
                
                # Simplified structure - only essential metadata in Report node
                report_id = report.report_id
                user_id = report.user_id if hasattr(report, 'user_id') and report.user_id else 'unknown'
                
                # Create or get User node
                session.run("""
                    MERGE (u:User {user_id: $userId})
                """, userId=user_id)
                
                # Create Report node with minimal data
                report_data = {
                    'report_id': report_id,
                    'case_id': report.case_id,
                    'created_at': report.created_at.isoformat(),
                    'updated_at': report.updated_at.isoformat() if report.updated_at else report.created_at.isoformat(),
                    'study_type': study_info.get('modality', 'Medical Imaging')
                }
                
                # Create Report node and link to User
                result = session.run("""
                    CREATE (r:Report $props)
                    WITH r
                    MATCH (u:User {user_id: $userId})
                    CREATE (u)-[:HAS_REPORT]->(r)
                    RETURN r.report_id as reportId
                """, props=report_data, userId=user_id)
                
                record = result.single()
                report_id = record['reportId']
                
                # Create ReportText node with the actual report content
                text_data = {
                    'id': f"{report_id}_text",
                    'content': radiological_analysis,
                    'recommendations': json.dumps(report.recommendations),
                    'key_findings': json.dumps(key_findings),
                    'created_at': datetime.now().isoformat()
                }
                
                session.run("""
                    CREATE (t:ReportText $props)
                    WITH t
                    MATCH (r:Report {report_id: $reportId})
                    CREATE (r)-[:HAS_TEXT]->(t)
                """, props=text_data, reportId=report_id)
                
                # Store heatmap as separate node if available
                if hasattr(report, 'heatmap_data') and report.heatmap_data:
                    heatmap_data = report.heatmap_data
                    if isinstance(heatmap_data, dict):
                        # Only store the overlay image (the combined heatmap + original image)
                        if 'overlay' in heatmap_data and heatmap_data['overlay']:
                            heatmap_node = {
                                'id': f"{report_id}_heatmap",
                                'overlay_image': heatmap_data['overlay'],  # Base64 encoded image
                                'created_at': datetime.now().isoformat()
                            }
                            session.run("""
                                CREATE (h:HeatmapImage $props)
                                WITH h
                                MATCH (r:Report {report_id: $reportId})
                                CREATE (r)-[:HAS_HEATMAP]->(h)
                            """, props=heatmap_node, reportId=report_id)
                
                # Store embeddings as separate node if provided (for MCP server use in other microservices)
                if embeddings:
                    embedding_data = {
                        'id': f"{report_id}_embeddings",
                        'created_at': datetime.now().isoformat()
                    }
                    
                    # Store each embedding type if available
                    if 'summary' in embeddings and embeddings['summary'] is not None:
                        if hasattr(embeddings['summary'], 'tolist'):
                            embedding_data['summary_embedding'] = embeddings['summary'].tolist()
                        else:
                            embedding_data['summary_embedding'] = list(embeddings['summary'])
                    
                    if 'full_report' in embeddings and embeddings['full_report'] is not None:
                        if hasattr(embeddings['full_report'], 'tolist'):
                            embedding_data['full_report_embedding'] = embeddings['full_report'].tolist()
                        else:
                            embedding_data['full_report_embedding'] = list(embeddings['full_report'])
                    
                    # Only create embedding node if we have actual embeddings
                    if len(embedding_data) > 2:  # More than just id and created_at
                        session.run("""
                            CREATE (e:ReportEmbedding $props)
                            WITH e
                            MATCH (r:Report {report_id: $reportId})
                            CREATE (r)-[:HAS_EMBEDDING]->(e)
                        """, props=embedding_data, reportId=report_id)
                
                # We don't create Finding, Citation, or ImageAnalysis nodes anymore
                # All that information is already included in the ReportText node
                
                logger.info(f"Report {report_id} saved to Neo4j successfully")
                
                # Create Case-Report relationship if case_id is provided
                if report.case_id and self.kg_service:
                    try:
                        # Check if we're in an async context
                        import asyncio
                        try:
                            # Try to get the current event loop
                            loop = asyncio.get_running_loop()
                            # We're in an async context, create a task
                            task = asyncio.create_task(
                                self.kg_service.create_case_report_relationship(
                                    report.case_id,
                                    report_id
                                )
                            )
                            # Don't wait for it to complete to avoid blocking
                            logger.info(f"Scheduled Case-Report relationship creation for case {report.case_id}")
                        except RuntimeError:
                            # No event loop running, use sync approach
                            # For now, skip the relationship creation in sync context
                            logger.warning(f"Cannot create Case-Report relationship in sync context for report {report_id}")
                    except Exception as rel_error:
                        logger.error(f"Error creating Case-Report relationship: {rel_error}")
                        # Don't fail the entire save operation if relationship creation fails
                
                return report_id
                
            except Exception as e:
                logger.error(f"Error saving report to Neo4j: {e}")
                raise
    
    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a report from Neo4j by ID using simplified structure
        
        Args:
            report_id: Report ID to retrieve
            
        Returns:
            Report data as dictionary or None if not found
        """
        with self.driver.session(database=self.database) as session:
            try:
                logger.info(f"Attempting to retrieve report with ID: {report_id}")
                
                # Get report with related nodes using new structure (no embeddings for now)
                result = session.run("""
                    MATCH (u:User)-[:HAS_REPORT]->(r:Report {report_id: $reportId})
                    OPTIONAL MATCH (r)-[:HAS_TEXT]->(t:ReportText)
                    OPTIONAL MATCH (r)-[:HAS_HEATMAP]->(h:HeatmapImage)
                    RETURN u.user_id as userId,
                           r as report,
                           t as text,
                           h as heatmap
                """, reportId=report_id)
                
                record = result.single()
                if not record:
                    logger.warning(f"No report found with ID: {report_id}")
                    
                    # Check if any reports exist at all
                    count_result = session.run("MATCH (r:Report) RETURN count(r) as count")
                    count = count_result.single()['count']
                    logger.info(f"Total Report nodes in database: {count}")
                    
                    # List first few report IDs for debugging
                    if count > 0:
                        id_result = session.run("MATCH (r:Report) RETURN r.report_id as id LIMIT 5")
                        ids = [record['id'] for record in id_result]
                        logger.info(f"Sample report IDs in database: {ids}")
                    
                    return None
                
                # Build report data from the simplified structure
                report_data = {
                    'id': record['report']['report_id'],
                    'report_id': record['report']['report_id'],
                    'userId': record['userId'],
                    'case_id': record['report'].get('case_id'),
                    'created_at': record['report'].get('created_at'),
                    'updated_at': record['report'].get('updated_at'),
                    'study_type': record['report'].get('study_type')
                }
                
                # Add text content if available
                if record['text']:
                    report_data['radiologicalAnalysis'] = record['text'].get('content')
                    if record['text'].get('recommendations'):
                        report_data['recommendations'] = json.loads(record['text']['recommendations'])
                    if record['text'].get('key_findings'):
                        report_data['key_findings'] = json.loads(record['text']['key_findings'])
                
                # Add heatmap data if available
                if record['heatmap']:
                    report_data['heatmap_data'] = {
                        'overlay': record['heatmap'].get('overlay_image')
                    }
                
                return report_data
                
            except Exception as e:
                logger.error(f"Error retrieving report from Neo4j: {e}")
                return None
    
    def get_patient_reports(
        self,
        patient_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all reports for a specific patient
        
        Args:
            patient_id: Patient ID
            limit: Maximum number of reports to return
            skip: Number of reports to skip (for pagination)
            
        Returns:
            List of report summaries
        """
        with self.driver.session(database=self.database) as session:
            try:
                result = session.run("""
                    MATCH (r:MedicalReport {patientId: $patientId})
                    RETURN r.id as id,
                           r.studyType as studyType,
                           r.studyDate as studyDate,
                           r.createdAt as createdAt,
                           r.severity as severity,
                           r.status as status,
                           r.clinicalImpression as summary
                    ORDER BY r.createdAt DESC
                    SKIP $skip
                    LIMIT $limit
                """, patientId=patient_id, skip=skip, limit=limit)
                
                reports = []
                for record in result:
                    # Sanitize Neo4j DateTime objects and ensure user fields
                    report_dict = dict(record)
                    report_dict = sanitize_neo4j_record(report_dict)
                    report_dict = ensure_user_fields(report_dict)
                    reports.append(report_dict)
                
                return reports
                
            except Exception as e:
                logger.error(f"Error retrieving patient reports: {e}")
                return []
    
    def find_similar_reports(
        self,
        embedding: List[float],
        similarity_threshold: float = 0.8,
        limit: int = 5,
        exclude_report_id: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find similar reports based on embedding similarity
        
        Args:
            embedding: Query embedding vector
            similarity_threshold: Minimum cosine similarity (0-1)
            limit: Maximum number of results
            exclude_report_id: Report ID to exclude from results
            
        Returns:
            List of (report, similarity_score) tuples
        """
        with self.driver.session(database=self.database) as session:
            try:
                # Build query based on whether to exclude a report
                exclude_clause = "AND r.id <> $excludeId" if exclude_report_id else ""
                
                # Use cosine similarity for vector comparison
                result = session.run(f"""
                    MATCH (r:MedicalReport)
                    WHERE r.fullReportEmbedding IS NOT NULL
                    {exclude_clause}
                    WITH r, gds.similarity.cosine(r.fullReportEmbedding, $embedding) AS similarity
                    WHERE similarity >= $threshold
                    RETURN r.id as id,
                           r.patientName as patientName,
                           r.studyType as studyType,
                           r.studyDate as studyDate,
                           r.clinicalImpression as summary,
                           r.severity as severity,
                           similarity
                    ORDER BY similarity DESC
                    LIMIT $limit
                """, embedding=embedding, threshold=similarity_threshold, 
                    limit=limit, excludeId=exclude_report_id)
                
                similar_reports = []
                for record in result:
                    report_data = dict(record)
                    similarity = report_data.pop('similarity')
                    similar_reports.append((report_data, similarity))
                
                return similar_reports
                
            except Exception as e:
                logger.error(f"Error finding similar reports: {e}")
                # Fallback to simpler similarity if GDS not available
                return self._find_similar_reports_fallback(
                    embedding, similarity_threshold, limit, exclude_report_id
                )
    
    def _find_similar_reports_fallback(
        self,
        embedding: List[float],
        similarity_threshold: float,
        limit: int,
        exclude_report_id: Optional[str]
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Fallback method for finding similar reports without GDS
        """
        with self.driver.session(database=self.database) as session:
            try:
                # Get all reports with embeddings
                exclude_clause = "WHERE r.id <> $excludeId" if exclude_report_id else ""
                
                result = session.run(f"""
                    MATCH (r:MedicalReport)
                    WHERE r.fullReportEmbedding IS NOT NULL
                    {exclude_clause}
                    RETURN r.id as id,
                           r.patientName as patientName,
                           r.studyType as studyType,
                           r.studyDate as studyDate,
                           r.clinicalImpression as summary,
                           r.severity as severity,
                           r.fullReportEmbedding as embedding
                """, excludeId=exclude_report_id)
                
                # Calculate similarities in Python
                similar_reports = []
                query_embedding = np.array(embedding)
                
                for record in result:
                    report_data = dict(record)
                    report_embedding = np.array(report_data.pop('embedding'))
                    
                    # Calculate cosine similarity
                    similarity = np.dot(query_embedding, report_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(report_embedding)
                    )
                    
                    if similarity >= similarity_threshold:
                        similar_reports.append((report_data, float(similarity)))
                
                # Sort by similarity and limit
                similar_reports.sort(key=lambda x: x[1], reverse=True)
                return similar_reports[:limit]
                
            except Exception as e:
                logger.error(f"Error in fallback similar reports search: {e}")
                return []
    
    def update_report_status(
        self,
        report_id: str,
        status: ReportStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update report status
        
        Args:
            report_id: Report ID to update
            status: New status
            error_message: Optional error message
            
        Returns:
            True if successful, False otherwise
        """
        with self.driver.session(database=self.database) as session:
            try:
                query = """
                    MATCH (r:MedicalReport {id: $reportId})
                    SET r.status = $status,
                        r.updatedAt = $updatedAt
                """
                
                params = {
                    'reportId': report_id,
                    'status': status.value,
                    'updatedAt': datetime.utcnow().isoformat()
                }
                
                if error_message:
                    query += ", r.errorMessage = $errorMessage"
                    params['errorMessage'] = error_message
                
                query += " RETURN r.id as id"
                
                result = session.run(query, **params)
                record = result.single()
                
                return record is not None
                
            except Exception as e:
                logger.error(f"Error updating report status: {e}")
                return False
    
    def get_recent_reports(
        self,
        limit: int = 10,
        study_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent reports across all users using simplified structure
        
        Args:
            limit: Maximum number of reports
            study_type: Optional filter by study type
            
        Returns:
            List of recent report summaries
        """
        with self.driver.session(database=self.database) as session:
            try:
                where_clause = "AND r.study_type = $studyType" if study_type else ""
                
                # Query using new simplified structure
                result = session.run(f"""
                    MATCH (u:User)-[:HAS_REPORT]->(r:Report)
                    {where_clause if study_type else ""}
                    OPTIONAL MATCH (r)-[:HAS_TEXT]->(t:ReportText)
                    RETURN r.report_id as id,
                           r.report_id as report_id,
                           u.user_id as userId,
                           r.study_type as studyType,
                           r.created_at as createdAt,
                           r.updated_at as updatedAt,
                           t.content as summary
                    ORDER BY r.created_at DESC
                    LIMIT $limit
                """, limit=limit, studyType=study_type)
                
                reports = []
                for record in result:
                    # Sanitize Neo4j DateTime objects and ensure user fields
                    report_dict = dict(record)
                    report_dict = sanitize_neo4j_record(report_dict)
                    report_dict = ensure_user_fields(report_dict)
                    reports.append(report_dict)
                
                return reports
                
            except Exception as e:
                logger.error(f"Error retrieving recent reports: {e}")
                return []
    
    async def get_reports_by_user(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all reports for a specific user using simplified structure
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of reports
            
        Returns:
            List of user's reports
        """
        with self.driver.session(database=self.database) as session:
            try:
                # Query using new simplified structure
                result = session.run("""
                    MATCH (u:User {user_id: $userId})-[:HAS_REPORT]->(r:Report)
                    OPTIONAL MATCH (r)-[:HAS_TEXT]->(t:ReportText)
                    RETURN r.report_id as id,
                           r.report_id as report_id,
                           u.user_id as userId,
                           r.study_type as studyType,
                           r.created_at as createdAt,
                           r.updated_at as updatedAt,
                           t.content as summary,
                           t.content as radiologicalAnalysis
                    ORDER BY r.created_at DESC
                    LIMIT $limit
                """, userId=user_id, limit=limit)
                
                reports = []
                for record in result:
                    # Sanitize Neo4j DateTime objects and ensure user fields
                    report_dict = dict(record)
                    report_dict = sanitize_neo4j_record(report_dict)
                    report_dict = ensure_user_fields(report_dict, user_id)
                    reports.append(report_dict)
                
                return reports
                
            except Exception as e:
                logger.error(f"Error retrieving user reports: {e}")
                return []
    
    def search_reports(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search reports by text query and filters
        
        Args:
            query: Search query text
            filters: Optional filters (patientId, studyType, dateRange, severity)
            limit: Maximum number of results
            
        Returns:
            List of matching reports
        """
        with self.driver.session(database=self.database) as session:
            try:
                # Build WHERE clauses
                where_clauses = []
                params = {'query': query.lower(), 'limit': limit}
                
                # Text search in multiple fields
                where_clauses.append("""
                    (toLower(r.clinicalImpression) CONTAINS $query OR
                     toLower(r.radiologicalAnalysis) CONTAINS $query OR
                     toLower(r.patientName) CONTAINS $query)
                """)
                
                # Apply filters
                if filters:
                    if 'patientId' in filters:
                        where_clauses.append("r.patientId = $patientId")
                        params['patientId'] = filters['patientId']
                    
                    if 'studyType' in filters:
                        where_clauses.append("r.studyType = $studyType")
                        params['studyType'] = filters['studyType']
                    
                    if 'severity' in filters:
                        where_clauses.append("r.severity = $severity")
                        params['severity'] = filters['severity']
                    
                    if 'dateRange' in filters:
                        if 'start' in filters['dateRange']:
                            where_clauses.append("r.studyDate >= $startDate")
                            params['startDate'] = filters['dateRange']['start']
                        
                        if 'end' in filters['dateRange']:
                            where_clauses.append("r.studyDate <= $endDate")
                            params['endDate'] = filters['dateRange']['end']
                
                where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                
                result = session.run(f"""
                    MATCH (r:MedicalReport)
                    {where_clause}
                    RETURN r.id as id,
                           r.patientName as patientName,
                           r.patientId as patientId,
                           r.studyType as studyType,
                           r.studyDate as studyDate,
                           r.createdAt as createdAt,
                           r.severity as severity,
                           r.status as status,
                           r.clinicalImpression as summary
                    ORDER BY r.createdAt DESC
                    LIMIT $limit
                """, **params)
                
                reports = []
                for record in result:
                    # Sanitize Neo4j DateTime objects and ensure user fields
                    report_dict = dict(record)
                    report_dict = sanitize_neo4j_record(report_dict)
                    report_dict = ensure_user_fields(report_dict)
                    reports.append(report_dict)
                
                return reports
                
            except Exception as e:
                logger.error(f"Error searching reports: {e}")
                return []
    
    async def store_report(self, report_data: Dict[str, Any]) -> str:
        """
        Store a medical report (wrapper for workflow compatibility)
        
        Args:
            report_data: Report data dictionary with all fields
            
        Returns:
            Report ID
        """
        # Create ImagingReport object from data
        from app.microservices.medical_imaging.models import ImagingReport, ImageAnalysis, ImageType, ReportStatus
        from datetime import datetime
        
        # Extract embeddings if present
        embeddings = report_data.pop('embeddings', None)
        
        # Extract heatmap data if present
        heatmap_data = report_data.pop('heatmap_data', None)
        
        # Create report object
        report = ImagingReport(
            report_id=report_data.get('report_id', report_data.get('id')),
            case_id=report_data.get('case_id', report_data.get('report_id')),
            user_id=report_data.get('user_id', ''),  # Add user_id field
            patient_id=report_data.get('patient_id'),
            patient_info=report_data.get('patient_info', {}),
            study_info=report_data.get('study_info', {}),
            overall_analysis=report_data.get('summary', ''),
            images=[],  # Empty for now
            clinical_impression=report_data.get('clinical_impression', ''),
            recommendations=report_data.get('recommendations', []),
            key_findings=report_data.get('key_findings', []),
            severity=report_data.get('severity', 'low'),
            citations=report_data.get('literature_references', []),
            created_at=datetime.fromisoformat(report_data.get('created_at', datetime.now().isoformat())),
            status=ReportStatus.COMPLETED
        )
        
        # Add heatmap data to report if available
        if heatmap_data:
            report.heatmap_data = heatmap_data
        
        # Save report with embeddings
        return self.save_report(report, embeddings)
    
    async def store_report_embedding(self, report_id: str, embedding: Any) -> None:
        """
        Store embedding for a report (no-op for now as embeddings are stored with report)
        
        Args:
            report_id: Report ID
            embedding: Embedding vector
        """
        # Embeddings are already stored as part of save_report
        # This is just for compatibility
        logger.info(f"Embedding for report {report_id} already stored with report")
        pass


# Singleton instance
_neo4j_storage_instance = None


def get_neo4j_storage() -> Neo4jReportStorageService:
    """Get or create Neo4j storage service instance"""
    global _neo4j_storage_instance
    if _neo4j_storage_instance is None:
        _neo4j_storage_instance = Neo4jReportStorageService()
        _neo4j_storage_instance.connect()
    return _neo4j_storage_instance