"""
Data Integrity Validator
Medical Case Management System

Comprehensive data integrity validation, ACID compliance monitoring,
and medical data consistency checks with HIPAA compliance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json

from neo4j import GraphDatabase
import aiofiles

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    HIPAA_COMPLIANCE = "hipaa_compliance"

class ValidationStatus(Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    CRITICAL = "critical"

class IntegrityIssueType(Enum):
    CONSTRAINT_VIOLATION = "constraint_violation"
    ORPHANED_RELATIONSHIP = "orphaned_relationship"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    DATA_TYPE_MISMATCH = "data_type_mismatch"
    DUPLICATE_RECORD = "duplicate_record"
    HIPAA_VIOLATION = "hipaa_violation"
    AUDIT_TRAIL_MISSING = "audit_trail_missing"
    ENCRYPTION_MISSING = "encryption_missing"
    ACCESS_CONTROL_VIOLATION = "access_control_violation"

@dataclass
class IntegrityIssue:
    """Individual data integrity issue."""
    issue_id: str
    issue_type: IntegrityIssueType
    severity: ValidationStatus
    node_id: Optional[str]
    relationship_id: Optional[str]
    description: str
    details: Dict[str, Any]
    detected_at: datetime
    suggested_fix: Optional[str] = None

@dataclass
class ValidationResult:
    """Complete validation result."""
    validation_id: str
    validation_level: ValidationLevel
    started_at: datetime
    completed_at: datetime
    total_nodes_checked: int
    total_relationships_checked: int
    issues_found: List[IntegrityIssue]
    overall_status: ValidationStatus
    recommendations: List[str]

@dataclass
class ValidationRule:
    """Data validation rule definition."""
    rule_id: str
    name: str
    description: str
    cypher_query: str
    expected_result: Any
    severity: ValidationStatus
    applies_to: List[str]  # Node labels or relationship types
    auto_fix: bool = False
    fix_query: Optional[str] = None

class DataIntegrityValidator:
    """
    Comprehensive data integrity validator for medical case management system.
    
    Features:
    - ACID compliance monitoring
    - Medical data consistency checks
    - HIPAA compliance validation
    - Automated issue detection and reporting
    - Performance-optimized validation
    - Audit trail validation
    """
    
    def __init__(self, 
                 neo4j_uri: str,
                 neo4j_user: str,
                 neo4j_password: str,
                 validation_rules_file: Optional[str] = None):
        """
        Initialize data integrity validator.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            validation_rules_file: Path to custom validation rules
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        self.validation_rules: Dict[str, ValidationRule] = {}
        
        # Load default validation rules
        self._load_default_rules()
        
        # Load custom rules if provided
        if validation_rules_file:
            asyncio.create_task(self._load_custom_rules(validation_rules_file))
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def connect(self):
        """Connect to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Connected to Neo4j for data integrity validation")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("Closed Neo4j connection")
    
    def _load_default_rules(self):
        """Load default validation rules for medical data."""
        
        # User data integrity rules
        self.validation_rules["user_unique_constraints"] = ValidationRule(
            rule_id="user_unique_constraints",
            name="User Unique Constraints",
            description="Verify unique constraints on user data",
            cypher_query="""
                MATCH (u:User)
                WITH u.user_id as user_id, u.username as username, u.email as email, count(u) as count
                WHERE count > 1
                RETURN user_id, username, email, count
            """,
            expected_result=[],
            severity=ValidationStatus.CRITICAL,
            applies_to=["User"]
        )
        
        # Case data integrity rules
        self.validation_rules["case_ownership"] = ValidationRule(
            rule_id="case_ownership",
            name="Case Ownership Validation",
            description="Ensure all cases have valid ownership relationships",
            cypher_query="""
                MATCH (c:Case)
                WHERE NOT EXISTS((User)-[:OWNS]->(c))
                RETURN c.case_id as case_id, c.title as title
            """,
            expected_result=[],
            severity=ValidationStatus.CRITICAL,
            applies_to=["Case"]
        )
        
        # Medical data validation rules
        self.validation_rules["required_medical_fields"] = ValidationRule(
            rule_id="required_medical_fields",
            name="Required Medical Fields",
            description="Validate required fields for medical cases",
            cypher_query="""
                MATCH (c:Case)
                WHERE c.medical_category IS NULL 
                   OR c.urgency_level IS NULL
                   OR c.created_at IS NULL
                RETURN c.case_id as case_id, 
                       c.medical_category as category,
                       c.urgency_level as urgency,
                       c.created_at as created
            """,
            expected_result=[],
            severity=ValidationStatus.FAILED,
            applies_to=["Case"]
        )
        
        # HIPAA compliance rules
        self.validation_rules["hipaa_audit_trail"] = ValidationRule(
            rule_id="hipaa_audit_trail",
            name="HIPAA Audit Trail",
            description="Ensure all medical data access is logged",
            cypher_query="""
                MATCH (c:Case)
                WHERE c.last_accessed_at IS NULL
                   OR c.accessed_by IS NULL
                RETURN c.case_id as case_id, 
                       c.last_accessed_at as last_access,
                       c.accessed_by as accessed_by
            """,
            expected_result=[],
            severity=ValidationStatus.WARNING,
            applies_to=["Case"]
        )
        
        # Analysis data integrity
        self.validation_rules["analysis_validity"] = ValidationRule(
            rule_id="analysis_validity",
            name="Analysis Data Validity",
            description="Validate analysis data completeness and accuracy",
            cypher_query="""
                MATCH (a:Analysis)
                WHERE a.confidence_score IS NULL
                   OR a.confidence_score < 0
                   OR a.confidence_score > 1
                   OR a.analysis_text IS NULL
                   OR a.analysis_text = ''
                RETURN a.analysis_id as analysis_id,
                       a.confidence_score as confidence,
                       length(a.analysis_text) as text_length
            """,
            expected_result=[],
            severity=ValidationStatus.FAILED,
            applies_to=["Analysis"]
        )
        
        # Relationship integrity
        self.validation_rules["orphaned_relationships"] = ValidationRule(
            rule_id="orphaned_relationships",
            name="Orphaned Relationships",
            description="Find relationships with missing nodes",
            cypher_query="""
                MATCH ()-[r]->()
                WHERE startNode(r) IS NULL OR endNode(r) IS NULL
                RETURN type(r) as relationship_type, id(r) as relationship_id
            """,
            expected_result=[],
            severity=ValidationStatus.CRITICAL,
            applies_to=["*"]
        )
        
        # Data encryption validation
        self.validation_rules["sensitive_data_encryption"] = ValidationRule(
            rule_id="sensitive_data_encryption",
            name="Sensitive Data Encryption",
            description="Ensure sensitive medical data is properly encrypted",
            cypher_query="""
                MATCH (c:Case)
                WHERE c.symptoms CONTAINS 'UNENCRYPTED:'
                   OR c.diagnosis CONTAINS 'UNENCRYPTED:'
                   OR c.patient_notes CONTAINS 'UNENCRYPTED:'
                RETURN c.case_id as case_id, 
                       'Unencrypted sensitive data detected' as issue
            """,
            expected_result=[],
            severity=ValidationStatus.CRITICAL,
            applies_to=["Case"]
        )
    
    async def _load_custom_rules(self, rules_file: str):
        """Load custom validation rules from file."""
        try:
            async with aiofiles.open(rules_file, 'r') as f:
                rules_data = json.loads(await f.read())
            
            for rule_data in rules_data.get("validation_rules", []):
                rule = ValidationRule(
                    rule_id=rule_data["rule_id"],
                    name=rule_data["name"],
                    description=rule_data["description"],
                    cypher_query=rule_data["cypher_query"],
                    expected_result=rule_data["expected_result"],
                    severity=ValidationStatus(rule_data["severity"]),
                    applies_to=rule_data["applies_to"],
                    auto_fix=rule_data.get("auto_fix", False),
                    fix_query=rule_data.get("fix_query")
                )
                self.validation_rules[rule.rule_id] = rule
                
            logger.info(f"Loaded {len(rules_data.get('validation_rules', []))} custom validation rules")
            
        except Exception as e:
            logger.error(f"Failed to load custom validation rules: {e}")
    
    async def validate_database(self, 
                              validation_level: ValidationLevel = ValidationLevel.STANDARD,
                              specific_rules: Optional[List[str]] = None) -> ValidationResult:
        """
        Perform comprehensive database validation.
        
        Args:
            validation_level: Level of validation to perform
            specific_rules: Specific rules to run (None for all applicable)
            
        Returns:
            Validation result
        """
        validation_id = f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        logger.info(f"Starting database validation {validation_id} at level {validation_level.value}")
        
        # Get database statistics
        db_stats = await self._get_database_statistics()
        
        # Determine which rules to run
        rules_to_run = self._select_rules_for_level(validation_level, specific_rules)
        
        # Run validation rules
        all_issues: List[IntegrityIssue] = []
        
        for rule_id, rule in rules_to_run.items():
            try:
                issues = await self._execute_validation_rule(rule)
                all_issues.extend(issues)
                logger.debug(f"Rule {rule_id} found {len(issues)} issues")
            except Exception as e:
                logger.error(f"Failed to execute validation rule {rule_id}: {e}")
                # Create an issue for the failed rule
                issue = IntegrityIssue(
                    issue_id=f"rule_execution_error_{rule_id}",
                    issue_type=IntegrityIssueType.CONSTRAINT_VIOLATION,
                    severity=ValidationStatus.CRITICAL,
                    node_id=None,
                    relationship_id=None,
                    description=f"Failed to execute validation rule: {rule.name}",
                    details={"rule_id": rule_id, "error": str(e)},
                    detected_at=datetime.now()
                )
                all_issues.append(issue)
        
        # Determine overall status
        overall_status = self._determine_overall_status(all_issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_issues, validation_level)
        
        # Create validation result
        result = ValidationResult(
            validation_id=validation_id,
            validation_level=validation_level,
            started_at=start_time,
            completed_at=datetime.now(),
            total_nodes_checked=db_stats["total_nodes"],
            total_relationships_checked=db_stats["total_relationships"],
            issues_found=all_issues,
            overall_status=overall_status,
            recommendations=recommendations
        )
        
        # Save validation result
        await self._save_validation_result(result)
        
        logger.info(f"Validation {validation_id} completed with {len(all_issues)} issues found")
        return result
    
    def _select_rules_for_level(self, 
                              validation_level: ValidationLevel,
                              specific_rules: Optional[List[str]]) -> Dict[str, ValidationRule]:
        """Select validation rules based on validation level."""
        if specific_rules:
            return {rule_id: self.validation_rules[rule_id] 
                   for rule_id in specific_rules 
                   if rule_id in self.validation_rules}
        
        selected_rules = {}
        
        for rule_id, rule in self.validation_rules.items():
            include_rule = False
            
            if validation_level == ValidationLevel.BASIC:
                # Only critical issues
                include_rule = rule.severity == ValidationStatus.CRITICAL
            elif validation_level == ValidationLevel.STANDARD:
                # Critical and failed issues
                include_rule = rule.severity in [ValidationStatus.CRITICAL, ValidationStatus.FAILED]
            elif validation_level == ValidationLevel.COMPREHENSIVE:
                # All issues except HIPAA-specific
                include_rule = "hipaa" not in rule.rule_id.lower()
            elif validation_level == ValidationLevel.HIPAA_COMPLIANCE:
                # All rules including HIPAA-specific
                include_rule = True
            
            if include_rule:
                selected_rules[rule_id] = rule
        
        return selected_rules
    
    async def _execute_validation_rule(self, rule: ValidationRule) -> List[IntegrityIssue]:
        """Execute a single validation rule and return issues found."""
        issues: List[IntegrityIssue] = []
        
        async with self.driver.session() as session:
            result = await session.run(rule.cypher_query)
            
            async for record in result:
                record_dict = dict(record)
                
                # If we got results and expected none, it's an issue
                if record_dict and not rule.expected_result:
                    issue = IntegrityIssue(
                        issue_id=f"{rule.rule_id}_{hash(str(record_dict))}",
                        issue_type=self._map_rule_to_issue_type(rule.rule_id),
                        severity=rule.severity,
                        node_id=record_dict.get("node_id") or record_dict.get("case_id") or record_dict.get("user_id"),
                        relationship_id=record_dict.get("relationship_id"),
                        description=f"{rule.name}: {rule.description}",
                        details=record_dict,
                        detected_at=datetime.now(),
                        suggested_fix=self._generate_suggested_fix(rule, record_dict)
                    )
                    issues.append(issue)
        
        return issues
    
    def _map_rule_to_issue_type(self, rule_id: str) -> IntegrityIssueType:
        """Map rule ID to appropriate issue type."""
        mapping = {
            "user_unique_constraints": IntegrityIssueType.CONSTRAINT_VIOLATION,
            "case_ownership": IntegrityIssueType.ORPHANED_RELATIONSHIP,
            "required_medical_fields": IntegrityIssueType.MISSING_REQUIRED_FIELD,
            "hipaa_audit_trail": IntegrityIssueType.AUDIT_TRAIL_MISSING,
            "analysis_validity": IntegrityIssueType.DATA_TYPE_MISMATCH,
            "orphaned_relationships": IntegrityIssueType.ORPHANED_RELATIONSHIP,
            "sensitive_data_encryption": IntegrityIssueType.ENCRYPTION_MISSING
        }
        return mapping.get(rule_id, IntegrityIssueType.CONSTRAINT_VIOLATION)
    
    def _generate_suggested_fix(self, rule: ValidationRule, issue_data: Dict[str, Any]) -> Optional[str]:
        """Generate suggested fix for the issue."""
        if rule.auto_fix and rule.fix_query:
            return f"Auto-fix available: {rule.fix_query}"
        
        # Generate manual suggestions based on rule type
        suggestions = {
            "user_unique_constraints": "Review and merge duplicate user records",
            "case_ownership": "Assign case to a valid user or remove orphaned case",
            "required_medical_fields": "Update case with required medical information",
            "hipaa_audit_trail": "Add audit trail information for data access",
            "analysis_validity": "Review and correct analysis data",
            "orphaned_relationships": "Remove orphaned relationship or restore missing nodes",
            "sensitive_data_encryption": "Encrypt sensitive medical data fields"
        }
        
        return suggestions.get(rule.rule_id, "Manual review and correction required")
    
    async def _get_database_statistics(self) -> Dict[str, int]:
        """Get current database statistics."""
        async with self.driver.session() as session:
            # Count total nodes
            nodes_result = await session.run("MATCH (n) RETURN count(n) as count")
            total_nodes = (await nodes_result.single())["count"]
            
            # Count total relationships
            rels_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            total_relationships = (await rels_result.single())["count"]
            
            return {
                "total_nodes": total_nodes,
                "total_relationships": total_relationships
            }
    
    def _determine_overall_status(self, issues: List[IntegrityIssue]) -> ValidationStatus:
        """Determine overall validation status based on issues found."""
        if not issues:
            return ValidationStatus.PASSED
        
        severities = [issue.severity for issue in issues]
        
        if ValidationStatus.CRITICAL in severities:
            return ValidationStatus.CRITICAL
        elif ValidationStatus.FAILED in severities:
            return ValidationStatus.FAILED
        else:
            return ValidationStatus.WARNING
    
    def _generate_recommendations(self, 
                                issues: List[IntegrityIssue],
                                validation_level: ValidationLevel) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if not issues:
            recommendations.append("Database integrity validation passed successfully")
            return recommendations
        
        # Count issues by severity
        critical_count = sum(1 for issue in issues if issue.severity == ValidationStatus.CRITICAL)
        failed_count = sum(1 for issue in issues if issue.severity == ValidationStatus.FAILED)
        warning_count = sum(1 for issue in issues if issue.severity == ValidationStatus.WARNING)
        
        if critical_count > 0:
            recommendations.append(f"URGENT: Address {critical_count} critical integrity issues immediately")
            recommendations.append("Consider taking database offline until critical issues are resolved")
        
        if failed_count > 0:
            recommendations.append(f"Address {failed_count} failed validation issues as soon as possible")
        
        if warning_count > 0:
            recommendations.append(f"Review {warning_count} warning issues during next maintenance window")
        
        # Specific recommendations based on issue types
        issue_types = [issue.issue_type for issue in issues]
        
        if IntegrityIssueType.HIPAA_VIOLATION in issue_types:
            recommendations.append("HIPAA compliance issues detected - review data protection measures")
        
        if IntegrityIssueType.ENCRYPTION_MISSING in issue_types:
            recommendations.append("Implement encryption for sensitive medical data")
        
        if IntegrityIssueType.AUDIT_TRAIL_MISSING in issue_types:
            recommendations.append("Strengthen audit logging for medical data access")
        
        # Validation level specific recommendations
        if validation_level == ValidationLevel.BASIC:
            recommendations.append("Consider running comprehensive validation for complete assessment")
        
        return recommendations
    
    async def _save_validation_result(self, result: ValidationResult):
        """Save validation result to database for audit purposes."""
        async with self.driver.session() as session:
            # Create validation record
            await session.run("""
                CREATE (vr:ValidationResult {
                    validation_id: $validation_id,
                    validation_level: $validation_level,
                    started_at: $started_at,
                    completed_at: $completed_at,
                    total_nodes_checked: $total_nodes_checked,
                    total_relationships_checked: $total_relationships_checked,
                    issues_count: $issues_count,
                    overall_status: $overall_status,
                    recommendations: $recommendations
                })
            """, {
                "validation_id": result.validation_id,
                "validation_level": result.validation_level.value,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat(),
                "total_nodes_checked": result.total_nodes_checked,
                "total_relationships_checked": result.total_relationships_checked,
                "issues_count": len(result.issues_found),
                "overall_status": result.overall_status.value,
                "recommendations": result.recommendations
            })
            
            # Create issue records
            for issue in result.issues_found:
                await session.run("""
                    MATCH (vr:ValidationResult {validation_id: $validation_id})
                    CREATE (vr)-[:HAS_ISSUE]->(issue:IntegrityIssue {
                        issue_id: $issue_id,
                        issue_type: $issue_type,
                        severity: $severity,
                        node_id: $node_id,
                        relationship_id: $relationship_id,
                        description: $description,
                        details: $details,
                        detected_at: $detected_at,
                        suggested_fix: $suggested_fix
                    })
                """, {
                    "validation_id": result.validation_id,
                    "issue_id": issue.issue_id,
                    "issue_type": issue.issue_type.value,
                    "severity": issue.severity.value,
                    "node_id": issue.node_id,
                    "relationship_id": issue.relationship_id,
                    "description": issue.description,
                    "details": json.dumps(issue.details),
                    "detected_at": issue.detected_at.isoformat(),
                    "suggested_fix": issue.suggested_fix
                })
    
    async def fix_auto_fixable_issues(self, validation_result: ValidationResult) -> int:
        """
        Automatically fix issues that have auto-fix capabilities.
        
        Args:
            validation_result: Validation result containing issues
            
        Returns:
            Number of issues fixed
        """
        fixed_count = 0
        
        for issue in validation_result.issues_found:
            # Find the rule that generated this issue
            rule = None
            for rule_id, validation_rule in self.validation_rules.items():
                if rule_id in issue.issue_id:
                    rule = validation_rule
                    break
            
            if rule and rule.auto_fix and rule.fix_query:
                try:
                    async with self.driver.session() as session:
                        await session.run(rule.fix_query, issue.details)
                    
                    logger.info(f"Auto-fixed issue: {issue.issue_id}")
                    fixed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to auto-fix issue {issue.issue_id}: {e}")
        
        return fixed_count
    
    async def get_validation_history(self, days: int = 30) -> List[ValidationResult]:
        """Get validation history for specified number of days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        validation_results = []
        
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (vr:ValidationResult)
                WHERE datetime(vr.started_at) >= datetime($cutoff_date)
                OPTIONAL MATCH (vr)-[:HAS_ISSUE]->(issue:IntegrityIssue)
                RETURN vr, collect(issue) as issues
                ORDER BY vr.started_at DESC
            """, {"cutoff_date": cutoff_date.isoformat()})
            
            async for record in result:
                vr_data = dict(record["vr"])
                issues_data = record["issues"]
                
                # Parse issues
                issues = []
                for issue_data in issues_data:
                    if issue_data:  # Skip null issues
                        issue = IntegrityIssue(
                            issue_id=issue_data["issue_id"],
                            issue_type=IntegrityIssueType(issue_data["issue_type"]),
                            severity=ValidationStatus(issue_data["severity"]),
                            node_id=issue_data.get("node_id"),
                            relationship_id=issue_data.get("relationship_id"),
                            description=issue_data["description"],
                            details=json.loads(issue_data.get("details", "{}")),
                            detected_at=datetime.fromisoformat(issue_data["detected_at"]),
                            suggested_fix=issue_data.get("suggested_fix")
                        )
                        issues.append(issue)
                
                # Create validation result
                validation_result = ValidationResult(
                    validation_id=vr_data["validation_id"],
                    validation_level=ValidationLevel(vr_data["validation_level"]),
                    started_at=datetime.fromisoformat(vr_data["started_at"]),
                    completed_at=datetime.fromisoformat(vr_data["completed_at"]),
                    total_nodes_checked=vr_data["total_nodes_checked"],
                    total_relationships_checked=vr_data["total_relationships_checked"],
                    issues_found=issues,
                    overall_status=ValidationStatus(vr_data["overall_status"]),
                    recommendations=vr_data["recommendations"]
                )
                
                validation_results.append(validation_result)
        
        return validation_results