"""
Neo4j Embedding Storage Service
Stores medical report embeddings and metadata for retrieval via MCP server
"""

import logging
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

# Check if AsyncGraphDatabase is available
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    ASYNC_NEO4J_AVAILABLE = True
except ImportError:
    # Fall back to sync version
    AsyncGraphDatabase = None
    AsyncDriver = None
    ASYNC_NEO4J_AVAILABLE = False

logger = logging.getLogger(__name__)


class Neo4jEmbeddingStorage:
    """
    Service for storing medical report embeddings in Neo4j
    Designed for integration with MCP server for retrieval
    """
    
    def __init__(
        self, 
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password"
    ):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None  # Will be AsyncDriver or regular Driver
        self.is_async = ASYNC_NEO4J_AVAILABLE
        
        logger.info(f"Initializing Neo4j embedding storage at {uri}")
    
    async def connect(self):
        """Establish connection to Neo4j"""
        try:
            if self.is_async and AsyncGraphDatabase:
                # Use async driver if available
                self.driver = AsyncGraphDatabase.driver(
                    self.uri, 
                    auth=(self.username, self.password)
                )
                
                # Verify connection
                async with self.driver.session() as session:
                    result = await session.run("RETURN 1")
                    await result.single()
            else:
                # Use sync driver with asyncio wrapper
                self.driver = GraphDatabase.driver(
                    self.uri, 
                    auth=(self.username, self.password)
                )
                
                # Verify connection using sync driver
                def verify_sync():
                    with self.driver.session() as session:
                        result = session.run("RETURN 1")
                        result.single()
                
                await asyncio.get_event_loop().run_in_executor(None, verify_sync)
            
            # Create indexes for efficient retrieval
            await self._create_indexes()
            
            logger.info("Connected to Neo4j successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def _run_query(self, query: str, parameters: Dict[str, Any] = None):
        """Run a query with async/sync compatibility"""
        if self.is_async and self.driver:
            async with self.driver.session() as session:
                result = await session.run(query, parameters or {})
                return await result.data()
        else:
            def run_sync():
                with self.driver.session() as session:
                    result = session.run(query, parameters or {})
                    return result.data()
            
            return await asyncio.get_event_loop().run_in_executor(None, run_sync)
    
    async def _execute_write(self, transaction_function, *args):
        """Execute a write transaction with async/sync compatibility"""
        if self.is_async and self.driver:
            async with self.driver.session() as session:
                # Use write_transaction instead of execute_write
                return await session.write_transaction(transaction_function, *args)
        else:
            def run_sync():
                with self.driver.session() as session:
                    # Use write_transaction instead of execute_write
                    return session.write_transaction(transaction_function, *args)
            
            return await asyncio.get_event_loop().run_in_executor(None, run_sync)
    
    async def disconnect(self):
        """Close Neo4j connection"""
        if self.driver:
            if self.is_async:
                await self.driver.close()
            else:
                self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    async def _create_indexes(self):
        """Create necessary indexes for efficient querying"""
        indexes = [
            "CREATE INDEX report_id IF NOT EXISTS FOR (r:MedicalReport) ON (r.report_id)",
            "CREATE INDEX case_id IF NOT EXISTS FOR (r:MedicalReport) ON (r.case_id)",
            "CREATE INDEX patient_id IF NOT EXISTS FOR (r:MedicalReport) ON (r.patient_id)",
            "CREATE INDEX study_date IF NOT EXISTS FOR (r:MedicalReport) ON (r.study_date)",
            "CREATE INDEX modality IF NOT EXISTS FOR (r:MedicalReport) ON (r.modality)",
            "CREATE INDEX embedding_type IF NOT EXISTS FOR (e:Embedding) ON (e.type)",
            "CREATE INDEX finding_type IF NOT EXISTS FOR (f:Finding) ON (f.type)",
            "CREATE INDEX finding_severity IF NOT EXISTS FOR (f:Finding) ON (f.severity)"
        ]
        
        for index_query in indexes:
            try:
                await self._run_query(index_query)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")
    
    async def store_medical_report(
        self,
        report_data: Dict[str, Any],
        embeddings: Dict[str, List[float]],
        annotated_images: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store medical report with embeddings in Neo4j
        
        Args:
            report_data: Complete medical report data
            embeddings: Dictionary of embeddings (summary, full_report, findings)
            annotated_images: Optional annotated image data
            
        Returns:
            Report node ID
        """
        try:
            # Execute the transaction to store report with embeddings
            result = await self._execute_write(
                self._create_report_transaction,
                report_data,
                embeddings,
                annotated_images
            )
            
            report_id = result.get("report_id")
            logger.info(f"Medical report {report_id} stored with embeddings successfully")
            
            return report_id
        except Exception as e:
            logger.error(f"Failed to store medical report: {e}")
            raise
    
    async def _create_report_transaction(
        self, 
        tx,
        report_data: Dict[str, Any],
        embeddings: Dict[str, List[float]],
        annotated_images: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Transaction to create report and all related nodes"""
        
        # Generate unique report ID if not provided
        report_id = report_data.get("report_id", str(uuid.uuid4()))
        
        # Create main report node
        report_query = """
        CREATE (r:MedicalReport {
            report_id: $report_id,
            case_id: $case_id,
            study_date: $study_date,
            modality: $modality,
            clinical_impression: $clinical_impression,
            created_at: datetime(),
            patient_age: $patient_age,
            patient_gender: $patient_gender,
            urgency_level: $urgency_level,
            quality_score: $quality_score
        })
        RETURN r
        """
        
        patient_info = report_data.get("patient_info", {})
        metadata = report_data.get("generation_metadata", {})
        
        report_result = await tx.run(
            report_query,
            report_id=report_id,
            case_id=report_data.get("case_id", ""),
            study_date=report_data.get("study_date", datetime.utcnow().isoformat()),
            modality=report_data.get("modality", "Unknown"),
            clinical_impression=report_data.get("clinical_impression", ""),
            patient_age=patient_info.get("age", 0),
            patient_gender=patient_info.get("gender", "Unknown"),
            urgency_level=report_data.get("urgency_level", "routine"),
            quality_score=metadata.get("quality_score", 0.0)
        )
        
        # Store embeddings
        for embedding_type, embedding_vector in embeddings.items():
            await self._store_embedding(tx, report_id, embedding_type, embedding_vector)
        
        # Store findings
        for idx, finding in enumerate(report_data.get("key_findings", [])):
            await self._store_finding(tx, report_id, idx, finding, report_data)
        
        # Store recommendations
        for idx, recommendation in enumerate(report_data.get("recommendations", [])):
            await self._store_recommendation(tx, report_id, idx, recommendation)
        
        # Store citations
        for idx, citation in enumerate(report_data.get("citations", [])):
            await self._store_citation(tx, report_id, idx, citation)
        
        # Store annotated images if provided
        if annotated_images:
            await self._store_annotated_images(tx, report_id, annotated_images)
        
        return {"report_id": report_id}
    
    async def _store_embedding(
        self, 
        tx, 
        report_id: str, 
        embedding_type: str, 
        embedding_vector: List[float]
    ):
        """Store an embedding node linked to the report"""
        # For Neo4j, we store embeddings as properties
        # In production, consider using a vector index plugin
        
        query = """
        MATCH (r:MedicalReport {report_id: $report_id})
        CREATE (e:Embedding {
            type: $type,
            vector: $vector,
            dimension: $dimension,
            created_at: datetime()
        })
        CREATE (r)-[:HAS_EMBEDDING]->(e)
        """
        
        await tx.run(
            query,
            report_id=report_id,
            type=embedding_type,
            vector=embedding_vector,
            dimension=len(embedding_vector)
        )
    
    async def _store_finding(
        self, 
        tx, 
        report_id: str, 
        index: int, 
        finding_text: str,
        report_data: Dict[str, Any]
    ):
        """Store a finding node linked to the report"""
        # Extract finding details from annotations if available
        annotations = report_data.get("annotations", [])
        finding_detail = annotations[index] if index < len(annotations) else {}
        
        query = """
        MATCH (r:MedicalReport {report_id: $report_id})
        CREATE (f:Finding {
            index: $index,
            description: $description,
            type: $type,
            severity: $severity,
            confidence: $confidence,
            created_at: datetime()
        })
        CREATE (r)-[:HAS_FINDING]->(f)
        """
        
        await tx.run(
            query,
            report_id=report_id,
            index=index,
            description=finding_text,
            type=finding_detail.get("type", "unknown"),
            severity=finding_detail.get("severity", "medium"),
            confidence=finding_detail.get("confidence", 0.8)
        )
    
    async def _store_recommendation(self, tx, report_id: str, index: int, recommendation: str):
        """Store a recommendation node linked to the report"""
        query = """
        MATCH (r:MedicalReport {report_id: $report_id})
        CREATE (rec:Recommendation {
            index: $index,
            text: $text,
            created_at: datetime()
        })
        CREATE (r)-[:HAS_RECOMMENDATION]->(rec)
        """
        
        await tx.run(
            query,
            report_id=report_id,
            index=index,
            text=recommendation
        )
    
    async def _store_citation(self, tx, report_id: str, index: int, citation: Dict[str, str]):
        """Store a citation node linked to the report"""
        query = """
        MATCH (r:MedicalReport {report_id: $report_id})
        CREATE (c:Citation {
            index: $index,
            title: $title,
            authors: $authors,
            year: $year,
            source: $source,
            created_at: datetime()
        })
        CREATE (r)-[:HAS_CITATION]->(c)
        """
        
        await tx.run(
            query,
            report_id=report_id,
            index=index,
            title=citation.get("title", ""),
            authors=citation.get("authors", ""),
            year=citation.get("year", ""),
            source=citation.get("source", "")
        )
    
    async def _store_annotated_images(self, tx, report_id: str, annotated_images: Dict[str, str]):
        """Store annotated image references"""
        for image_type, image_data in annotated_images.items():
            query = """
            MATCH (r:MedicalReport {report_id: $report_id})
            CREATE (i:AnnotatedImage {
                type: $type,
                data_reference: $data_reference,
                created_at: datetime()
            })
            CREATE (r)-[:HAS_ANNOTATED_IMAGE]->(i)
            """
            
            # Store reference to image data (not the actual base64 data)
            # In production, store in object storage and save URL
            await tx.run(
                query,
                report_id=report_id,
                type=image_type,
                data_reference=f"image_{report_id}_{image_type}"
            )
    
    async def retrieve_similar_reports(
        self,
        query_embedding: List[float],
        embedding_type: str = "summary",
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar reports based on embedding similarity
        
        This method is designed for MCP server integration
        
        Args:
            query_embedding: Query embedding vector
            embedding_type: Type of embedding to search
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar reports with similarity scores
        """
        try:
            async with self.driver.session() as session:
                # In production, use Neo4j vector index
                # For now, retrieve all embeddings and compute similarity in memory
                query = """
                MATCH (r:MedicalReport)-[:HAS_EMBEDDING]->(e:Embedding {type: $type})
                RETURN r, e.vector as embedding
                LIMIT 1000
                """
                
                result = await session.run(query, type=embedding_type)
                records = await result.data()
                
                # Compute cosine similarity
                query_vec = np.array(query_embedding)
                similar_reports = []
                
                for record in records:
                    report = record["r"]
                    stored_vec = np.array(record["embedding"])
                    
                    # Cosine similarity
                    similarity = np.dot(query_vec, stored_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
                    )
                    
                    if similarity >= similarity_threshold:
                        similar_reports.append({
                            "report_id": report["report_id"],
                            "case_id": report["case_id"],
                            "clinical_impression": report["clinical_impression"],
                            "modality": report["modality"],
                            "study_date": report["study_date"],
                            "similarity_score": float(similarity)
                        })
                
                # Sort by similarity score
                similar_reports.sort(key=lambda x: x["similarity_score"], reverse=True)
                
                return similar_reports[:limit]
                
        except Exception as e:
            logger.error(f"Failed to retrieve similar reports: {e}")
            return []
    
    async def get_report_details(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete report details including findings and recommendations
        
        Args:
            report_id: Report ID to retrieve
            
        Returns:
            Complete report data or None if not found
        """
        try:
            async with self.driver.session() as session:
                # Get report with all related nodes
                query = """
                MATCH (r:MedicalReport {report_id: $report_id})
                OPTIONAL MATCH (r)-[:HAS_FINDING]->(f:Finding)
                OPTIONAL MATCH (r)-[:HAS_RECOMMENDATION]->(rec:Recommendation)
                OPTIONAL MATCH (r)-[:HAS_CITATION]->(c:Citation)
                OPTIONAL MATCH (r)-[:HAS_EMBEDDING]->(e:Embedding)
                RETURN r,
                       collect(DISTINCT f) as findings,
                       collect(DISTINCT rec) as recommendations,
                       collect(DISTINCT c) as citations,
                       collect(DISTINCT {type: e.type, dimension: e.dimension}) as embeddings
                """
                
                result = await session.run(query, report_id=report_id)
                record = await result.single()
                
                if not record:
                    return None
                
                report = record["r"]
                
                return {
                    "report_id": report["report_id"],
                    "case_id": report["case_id"],
                    "study_date": report["study_date"],
                    "modality": report["modality"],
                    "clinical_impression": report["clinical_impression"],
                    "patient_age": report.get("patient_age"),
                    "patient_gender": report.get("patient_gender"),
                    "urgency_level": report.get("urgency_level"),
                    "quality_score": report.get("quality_score"),
                    "findings": [
                        {
                            "description": f["description"],
                            "type": f["type"],
                            "severity": f["severity"],
                            "confidence": f["confidence"]
                        }
                        for f in sorted(record["findings"], key=lambda x: x["index"])
                    ],
                    "recommendations": [
                        rec["text"] 
                        for rec in sorted(record["recommendations"], key=lambda x: x["index"])
                    ],
                    "citations": [
                        {
                            "title": c["title"],
                            "authors": c["authors"],
                            "year": c["year"],
                            "source": c["source"]
                        }
                        for c in sorted(record["citations"], key=lambda x: x["index"])
                    ],
                    "embedding_info": record["embeddings"]
                }
                
        except Exception as e:
            logger.error(f"Failed to get report details: {e}")
            return None
    
    async def search_reports_by_criteria(
        self,
        modality: Optional[str] = None,
        severity: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        urgency_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search reports by various criteria
        
        Args:
            modality: Image modality (CT, MRI, etc.)
            severity: Finding severity level
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
            urgency_level: Urgency level of findings
            
        Returns:
            List of matching reports
        """
        try:
            where_clauses = []
            params = {}
            
            if modality:
                where_clauses.append("r.modality = $modality")
                params["modality"] = modality
            
            if urgency_level:
                where_clauses.append("r.urgency_level = $urgency_level")
                params["urgency_level"] = urgency_level
            
            if date_from:
                where_clauses.append("r.study_date >= $date_from")
                params["date_from"] = date_from
            
            if date_to:
                where_clauses.append("r.study_date <= $date_to")
                params["date_to"] = date_to
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            MATCH (r:MedicalReport)
            WHERE {where_clause}
            {"MATCH (r)-[:HAS_FINDING]->(f:Finding {severity: $severity})" if severity else ""}
            RETURN DISTINCT r
            ORDER BY r.study_date DESC
            LIMIT 100
            """
            
            if severity:
                params["severity"] = severity
            
            async with self.driver.session() as session:
                result = await session.run(query, **params)
                records = await result.data()
                
                return [
                    {
                        "report_id": record["r"]["report_id"],
                        "case_id": record["r"]["case_id"],
                        "study_date": record["r"]["study_date"],
                        "modality": record["r"]["modality"],
                        "clinical_impression": record["r"]["clinical_impression"],
                        "urgency_level": record["r"].get("urgency_level", "routine")
                    }
                    for record in records
                ]
                
        except Exception as e:
            logger.error(f"Failed to search reports: {e}")
            return []


# Singleton instance
_storage_instance: Optional[Neo4jEmbeddingStorage] = None


async def get_neo4j_embedding_storage() -> Neo4jEmbeddingStorage:
    """Get or create Neo4j embedding storage instance"""
    global _storage_instance
    
    if not _storage_instance:
        _storage_instance = Neo4jEmbeddingStorage(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="medical123"
        )
        await _storage_instance.connect()
    
    return _storage_instance


async def cleanup_neo4j_storage():
    """Cleanup Neo4j connections"""
    global _storage_instance
    
    if _storage_instance:
        await _storage_instance.disconnect()
        _storage_instance = None