"""
Neo4j Storage Service for Medical Imaging
Handles all database operations for medical imaging reports and embeddings
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
import asyncio
import json

from app.microservices.medical_imaging.models import ImagingReport, ReportStatus, ImageAnalysis
from .neo4j_utils import sanitize_neo4j_record, ensure_user_fields

logger = logging.getLogger(__name__)


class MedicalImagingStorage:
    """
    Neo4j storage service for medical imaging reports and embeddings
    """
    
    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j URI (e.g., bolt://localhost:7687)
            user: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"Medical Imaging Neo4j storage initialized with URI: {uri}")
    
    async def close(self):
        """Close Neo4j connection"""
        self.driver.close()
    
    def begin_transaction(self):
        """Begin a new transaction"""
        return self.driver.session().begin_transaction()
    
    async def begin_async_transaction(self):
        """Begin a new async transaction"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.begin_transaction)
    
    def _run_sync_query(self, query: str, params: dict = None):
        """Run a synchronous query and return results"""
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    
    async def _run_async_query(self, query: str, params: dict = None):
        """Run a query asynchronously using executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_sync_query, query, params)
    
    async def create_imaging_report(self, report: ImagingReport) -> str:
        """
        Create a new imaging report in Neo4j using simplified structure
        
        Args:
            report: ImagingReport instance
            
        Returns:
            Created report ID
        """
        # First ensure User node exists
        user_query = """
        MERGE (u:User {user_id: $user_id})
        """
        
        await self._run_async_query(user_query, {
            'user_id': report.user_id if hasattr(report, 'user_id') else 'unknown'
        })
        
        # Create Report node with minimal data
        query = """
        CREATE (r:Report {
            report_id: $report_id,
            case_id: $case_id,
            created_at: datetime($created_at),
            updated_at: datetime($updated_at),
            study_type: $study_type
        })
        
        // Link to User
        WITH r
        MATCH (u:User {user_id: $user_id})
        CREATE (u)-[:HAS_REPORT]->(r)
        
        RETURN r.report_id as report_id
        """
        
        params = {
            "report_id": report.report_id,
            "case_id": report.case_id,
            "user_id": report.user_id if hasattr(report, 'user_id') else 'unknown',
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat() if report.updated_at else report.created_at.isoformat(),
            "study_type": "Medical Imaging"
        }
        
        try:
            result = await self._run_async_query(query, params)
            if result:
                logger.info(f"Created imaging report: {report.report_id}")
                
                # Create ReportText node with the actual content
                if hasattr(report, 'overall_analysis') and report.overall_analysis:
                    text_query = """
                    CREATE (t:ReportText {
                        id: $text_id,
                        content: $content,
                        recommendations: $recommendations,
                        key_findings: $key_findings,
                        created_at: datetime($created_at)
                    })
                    WITH t
                    MATCH (r:Report {report_id: $report_id})
                    CREATE (r)-[:HAS_TEXT]->(t)
                    """
                    
                    text_params = {
                        "text_id": f"{report.report_id}_text",
                        "content": report.overall_analysis,
                        "recommendations": json.dumps(report.recommendations) if hasattr(report, 'recommendations') else "[]",
                        "key_findings": json.dumps([]),  # Extract from report if available
                        "created_at": datetime.now().isoformat(),
                        "report_id": report.report_id
                    }
                    
                    await self._run_async_query(text_query, text_params)
                
                return result[0]["report_id"]
            else:
                raise Exception("Failed to create imaging report")
        except Neo4jError as e:
            logger.error(f"Neo4j error creating imaging report: {e}")
            raise
    
    async def _create_image_analysis(self, report_id: str, image: ImageAnalysis):
        """Create image analysis node and link to report"""
        # Build the base query
        base_properties = """
            image_id: $image_id,
            filename: $filename,
            image_type: $image_type,
            analysis_text: $analysis_text,
            findings: $findings,
            keywords: $keywords,
            created_at: datetime($created_at)
        """
        
        # Add heatmap properties if available
        heatmap_properties = ""
        if image.heatmap_data:
            heatmap_properties = """,
            heatmap_original_image: $heatmap_original_image,
            heatmap_overlay: $heatmap_overlay,
            heatmap_only: $heatmap_only,
            heatmap_attention_regions: $heatmap_attention_regions
            """
        
        query = f"""
        MATCH (r:ImagingReport {{report_id: $report_id}})
        CREATE (i:ImageAnalysis {{
            {base_properties}{heatmap_properties}
        }})
        CREATE (r)-[:CONTAINS_IMAGE]->(i)
        RETURN i.image_id as image_id
        """
        
        params = {
            "report_id": report_id,
            "image_id": image.image_id,
            "filename": image.filename,
            "image_type": image.image_type.value,
            "analysis_text": image.analysis_text,
            "findings": json.dumps(image.findings),
            "keywords": json.dumps(image.keywords),
            "created_at": image.created_at.isoformat()
        }
        
        # Add heatmap data to params if available
        if image.heatmap_data:
            params.update({
                "heatmap_original_image": image.heatmap_data.original_image,
                "heatmap_overlay": image.heatmap_data.heatmap_overlay,
                "heatmap_only": image.heatmap_data.heatmap_only,
                "heatmap_attention_regions": json.dumps(image.heatmap_data.attention_regions)
            })
        
        await self._run_async_query(query, params)
    
    async def store_report_embedding(self, report_id: str, embedding: List[float]):
        """
        Store embedding vector for a report
        
        Args:
            report_id: Report ID
            embedding: Embedding vector
        """
        query = """
        MATCH (r:ImagingReport {report_id: $report_id})
        SET r.report_embedding = $embedding,
            r.embedding_dimension = $dimension,
            r.semantic_search_enabled = true,
            r.updated_at = datetime($updated_at)
        RETURN r.report_id as report_id
        """
        
        params = {
            "report_id": report_id,
            "embedding": embedding,
            "dimension": len(embedding),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = await self._run_async_query(query, params)
            if result:
                logger.info(f"Stored embedding for report: {report_id} (dimensions: {len(embedding)})")
            else:
                raise Exception(f"Report {report_id} not found")
        except Neo4jError as e:
            logger.error(f"Neo4j error storing embedding: {e}")
            raise
    
    async def store_image_analysis_embedding(self, image_id: str, embedding: List[float]):
        """
        Store embedding vector for an image analysis
        
        Args:
            image_id: Image analysis ID
            embedding: Embedding vector
        """
        query = """
        MATCH (i:ImageAnalysis {image_id: $image_id})
        SET i.analysis_embedding = $embedding,
            i.embedding_dimension = $dimension,
            i.embedding_model = 'gemini-embedding-001'
        RETURN i.image_id as image_id
        """
        
        params = {
            "image_id": image_id,
            "embedding": embedding,
            "dimension": len(embedding)
        }
        
        try:
            result = await self._run_async_query(query, params)
            if result:
                logger.info(f"Stored embedding for image analysis: {image_id} (dimensions: {len(embedding)})")
            else:
                raise Exception(f"Image analysis {image_id} not found")
        except Neo4jError as e:
            logger.error(f"Neo4j error storing image embedding: {e}")
            raise
    
    async def find_similar_reports(self, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar reports using cosine similarity
        
        Args:
            embedding: Query embedding vector
            limit: Maximum number of results
            
        Returns:
            List of similar reports with similarity scores
        """
        query = """
        MATCH (r:ImagingReport)
        WHERE r.report_embedding IS NOT NULL AND r.semantic_search_enabled = true
        WITH r, gds.similarity.cosine(r.report_embedding, $embedding) AS similarity
        WHERE similarity > 0.7
        RETURN r {
            .report_id,
            .case_id,
            .overall_analysis,
            .clinical_impression,
            .created_at,
            similarity: similarity
        } as report
        ORDER BY similarity DESC
        LIMIT $limit
        """
        
        params = {
            "embedding": embedding,
            "limit": limit
        }
        
        try:
            result = await self._run_async_query(query, params)
            return [record["report"] for record in result]
        except Neo4jError as e:
            # If GDS is not available, use a fallback method
            if "gds.similarity.cosine" in str(e):
                logger.warning("GDS not available, using fallback similarity search")
                return await self._find_similar_reports_fallback(embedding, limit)
            else:
                logger.error(f"Neo4j error finding similar reports: {e}")
                return []
    
    async def _find_similar_reports_fallback(self, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fallback method for finding similar reports without GDS
        Uses in-memory cosine similarity calculation
        """
        import numpy as np
        
        # Get all reports with embeddings
        query = """
        MATCH (r:ImagingReport)
        WHERE r.report_embedding IS NOT NULL AND r.semantic_search_enabled = true
        RETURN r {
            .report_id,
            .case_id,
            .overall_analysis,
            .clinical_impression,
            .created_at,
            .report_embedding
        } as report
        """
        
        try:
            results = await self._run_async_query(query)
            if not results:
                return []
            
            # Calculate cosine similarity for each report
            query_embedding = np.array(embedding)
            query_norm = np.linalg.norm(query_embedding)
            
            similarities = []
            for record in results:
                report = record["report"]
                report_embedding = report.get("report_embedding", [])
                
                # Skip if no embedding or empty embedding
                if not report_embedding or len(report_embedding) == 0:
                    continue
                
                report_embedding = np.array(report_embedding)
                
                # Calculate cosine similarity
                dot_product = np.dot(query_embedding, report_embedding)
                report_norm = np.linalg.norm(report_embedding)
                
                if query_norm > 0 and report_norm > 0:
                    similarity = dot_product / (query_norm * report_norm)
                    
                    if similarity > 0.7:  # Threshold
                        # Remove embedding from result
                        report_data = {k: v for k, v in report.items() if k != "report_embedding"}
                        report_data["similarity"] = float(similarity)
                        similarities.append(report_data)
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            logger.error(f"Error in fallback similarity search: {e}")
            return []
    
    async def get_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get imaging report by ID using new simplified structure
        
        Args:
            report_id: Report ID
            
        Returns:
            Report data or None
        """
        query = """
        MATCH (u:User)-[:HAS_REPORT]->(r:Report {report_id: $report_id})
        OPTIONAL MATCH (r)-[:HAS_TEXT]->(t:ReportText)
        OPTIONAL MATCH (r)-[:HAS_HEATMAP]->(h:HeatmapImage)
        RETURN 
            u.user_id as userId,
            r.report_id as id,
            r.case_id as caseId,
            r.created_at as createdAt,
            r.updated_at as updatedAt,
            r.study_type as studyType,
            t.content as radiologicalAnalysis,
            t.recommendations as recommendations,
            t.key_findings as keyFindings,
            h.overlay_image as heatmapOverlay
        """
        
        params = {"report_id": report_id}
        
        try:
            result = await self._run_async_query(query, params)
            if result and len(result) > 0:
                report_data = result[0]
                
                # Parse JSON fields if they exist
                if report_data.get("recommendations"):
                    try:
                        report_data["recommendations"] = json.loads(report_data["recommendations"])
                    except:
                        report_data["recommendations"] = []
                        
                if report_data.get("keyFindings"):
                    try:
                        report_data["key_findings"] = json.loads(report_data["keyFindings"])
                    except:
                        report_data["key_findings"] = []
                
                # Structure heatmap data if present
                if report_data.get("heatmapOverlay"):
                    report_data["heatmap_data"] = {
                        "overlay": report_data.pop("heatmapOverlay")
                    }
                
                # Add empty images array for compatibility
                report_data["images"] = []
                
                # Ensure all fields for compatibility
                report_data["patientName"] = "Patient"
                report_data["patientId"] = report_data.get("userId", "")
                
                return report_data
            return None
        except Neo4jError as e:
            logger.error(f"Neo4j error getting report: {e}")
            return None
    
    async def update_report_status(self, report_id: str, status: ReportStatus):
        """Update report status"""
        # In the new simplified schema, we don't store status
        # This method is kept for compatibility with workflow code
        # Status updates are only sent via WebSocket for real-time progress
        logger.debug(f"Status update for report {report_id}: {status.value} (not persisted in new schema)")
    
    def get_report_by_case_id(self, case_id: str) -> Optional[ImagingReport]:
        """Get the most recent imaging report for a case (synchronous version)"""
        query = """
        MATCH (r:ImagingReport {case_id: $case_id})
        OPTIONAL MATCH (r)-[:CONTAINS_IMAGE]->(i:ImageAnalysis)
        WITH r, collect(i) as images
        ORDER BY r.created_at DESC
        LIMIT 1
        RETURN r {
            .*,
            created_at: toString(r.created_at),
            updated_at: toString(r.updated_at),
            images: [img IN images | img {
                .*,
                created_at: toString(img.created_at)
            }]
        } as report
        """
        
        try:
            results = self._run_sync_query(query, {"case_id": case_id})
            if results and results[0]["report"]:
                report_data = results[0]["report"]
                
                # Convert to ImagingReport object
                report = ImagingReport(
                    report_id=report_data["report_id"],
                    case_id=report_data["case_id"],
                    user_id=report_data["user_id"],
                    patient_id=report_data.get("patient_id", ""),
                    overall_analysis=report_data.get("overall_analysis", ""),
                    clinical_impression=report_data.get("clinical_impression", ""),
                    recommendations=json.loads(report_data.get("recommendations", "[]")),
                    citations=json.loads(report_data.get("citations", "[]")),
                    complete_report=report_data.get("complete_report", ""),
                    embedding_model=report_data.get("embedding_model", ""),
                    status=ReportStatus(report_data.get("status", "pending")),
                    created_at=datetime.fromisoformat(report_data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(report_data["updated_at"].replace("Z", "+00:00"))
                )
                
                # Add images
                for img_data in report_data.get("images", []):
                    image = ImageAnalysis(
                        image_id=img_data["image_id"],
                        filename=img_data["filename"],
                        image_type=img_data.get("image_type", "UNKNOWN"),
                        analysis_text=img_data.get("analysis_text", ""),
                        findings=json.loads(img_data.get("findings", "{}")),
                        keywords=json.loads(img_data.get("keywords", "[]")),
                        created_at=datetime.fromisoformat(img_data["created_at"].replace("Z", "+00:00"))
                    )
                    report.images.append(image)
                
                # If patient_id is not set in the report, try to get it from Case relationship
                if not report.patient_id:
                    patient_query = """
                    MATCH (c:Case {case_id: $case_id})
                    OPTIONAL MATCH (c)-[:BELONGS_TO]->(p:Patient)
                    RETURN c.case_id as case_id, p.patient_id as patient_id
                    """
                    patient_results = self._run_sync_query(patient_query, {"case_id": case_id})
                    if patient_results and patient_results[0].get("patient_id"):
                        report.patient_id = patient_results[0].get("patient_id", "")
                
                # Get image paths from images
                report.image_paths = [img.filename for img in report.images]
                
                return report
            return None
        except Exception as e:
            logger.error(f"Error getting report by case ID {case_id}: {e}")
            return None
    
    async def get_reports_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all imaging reports for a case"""
        query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_IMAGING_REPORT]->(r:ImagingReport)
        OPTIONAL MATCH (r)-[:CONTAINS_IMAGE]->(i:ImageAnalysis)
        WITH r, collect(i {
            .image_id,
            .filename,
            .image_type,
            .created_at
        }) as images
        RETURN r {
            .*,
            image_count: size(images),
            images: images
        } as report
        ORDER BY r.created_at DESC
        """
        
        params = {"case_id": case_id}
        
        try:
            result = await self._run_async_query(query, params)
            reports = []
            for record in result:
                report_data = record["report"]
                # Sanitize Neo4j DateTime objects and ensure user fields
                report_data = sanitize_neo4j_record(report_data)
                report_data = ensure_user_fields(report_data)
                if "recommendations" in report_data:
                    report_data["recommendations"] = json.loads(report_data["recommendations"])
                reports.append(report_data)
            return reports
        except Neo4jError as e:
            logger.error(f"Neo4j error getting reports by case: {e}")
            return []
    
    async def get_recent_reports(self, limit: int = 10, study_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent imaging reports using new schema"""
        if study_type:
            query = """
            MATCH (u:User)-[:HAS_REPORT]->(r:Report {study_type: $study_type})
            OPTIONAL MATCH (r)-[:HAS_TEXT]->(t:ReportText)
            RETURN {
                userId: u.user_id,
                id: r.report_id,
                caseId: r.case_id,
                createdAt: r.created_at,
                studyType: r.study_type,
                radiologicalAnalysis: t.content
            } as report
            ORDER BY r.created_at DESC
            LIMIT $limit
            """
            params = {"study_type": study_type, "limit": limit}
        else:
            query = """
            MATCH (u:User)-[:HAS_REPORT]->(r:Report)
            OPTIONAL MATCH (r)-[:HAS_TEXT]->(t:ReportText)
            RETURN {
                userId: u.user_id,
                id: r.report_id,
                caseId: r.case_id,
                createdAt: r.created_at,
                studyType: r.study_type,
                radiologicalAnalysis: t.content
            } as report
            ORDER BY r.created_at DESC
            LIMIT $limit
            """
            params = {"limit": limit}
        
        try:
            result = await self._run_async_query(query, params)
            reports = []
            for record in result:
                report_data = record["report"]
                # Sanitize Neo4j DateTime objects and ensure user fields
                report_data = sanitize_neo4j_record(report_data)
                report_data = ensure_user_fields(report_data)
                if "recommendations" in report_data:
                    report_data["recommendations"] = json.loads(report_data["recommendations"])
                reports.append(report_data)
            return reports
        except Neo4jError as e:
            logger.error(f"Neo4j error getting recent reports: {e}")
            return []
    
    async def search_reports(self, query: str, filters: dict = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search imaging reports"""
        cypher_query = """
        MATCH (r:ImagingReport)
        WHERE toLower(r.clinical_impression) CONTAINS toLower($query)
           OR toLower(r.findings) CONTAINS toLower($query)
           OR toLower(r.patient_name) CONTAINS toLower($query)
        """
        
        params = {"query": query, "limit": limit}
        
        # Add filters
        if filters:
            if filters.get("study_type"):
                cypher_query += " AND r.study_type = $study_type"
                params["study_type"] = filters["study_type"]
            if filters.get("severity"):
                cypher_query += " AND r.severity = $severity"
                params["severity"] = filters["severity"]
        
        cypher_query += """
        RETURN r {.*} as report
        ORDER BY r.created_at DESC
        LIMIT $limit
        """
        
        try:
            result = await self._run_async_query(cypher_query, params)
            reports = []
            for record in result:
                report_data = record["report"]
                # Sanitize Neo4j DateTime objects and ensure user fields
                report_data = sanitize_neo4j_record(report_data)
                report_data = ensure_user_fields(report_data)
                if "recommendations" in report_data:
                    report_data["recommendations"] = json.loads(report_data["recommendations"])
                reports.append(report_data)
            return reports
        except Neo4jError as e:
            logger.error(f"Neo4j error searching reports: {e}")
            return []
    
    async def get_patient_reports(self, patient_id: str, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """Get all reports for a user (renamed from patient for compatibility)"""
        # In new schema, we use user_id instead of patient_id
        query = """
        MATCH (u:User {user_id: $userId})-[:HAS_REPORT]->(r:Report)
        OPTIONAL MATCH (r)-[:HAS_TEXT]->(t:ReportText)
        OPTIONAL MATCH (r)-[:HAS_HEATMAP]->(h:HeatmapImage)
        RETURN 
            u.user_id as userId,
            r.report_id as id,
            r.case_id as caseId,
            r.created_at as createdAt,
            r.study_type as studyType,
            t.content as radiologicalAnalysis,
            h.overlay_image as heatmapOverlay
        ORDER BY r.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        
        params = {"userId": patient_id, "limit": limit, "skip": skip}  # patient_id is actually user_id
        
        try:
            result = await self._run_async_query(query, params)
            reports = []
            for record in result:
                report_data = record["report"]
                # Sanitize Neo4j DateTime objects and ensure user fields
                report_data = sanitize_neo4j_record(report_data)
                report_data = ensure_user_fields(report_data)
                if "recommendations" in report_data:
                    report_data["recommendations"] = json.loads(report_data["recommendations"])
                reports.append(report_data)
            return reports
        except Neo4jError as e:
            logger.error(f"Neo4j error getting patient reports: {e}")
            return []