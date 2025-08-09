"""
Disaster Recovery Manager
Medical Case Management System

Comprehensive disaster recovery capabilities for medical data protection,
business continuity, and HIPAA compliance during emergency situations.
"""

import asyncio
import logging
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import subprocess

from neo4j import GraphDatabase
import aiofiles

logger = logging.getLogger(__name__)

class DisasterType(Enum):
    HARDWARE_FAILURE = "hardware_failure"
    DATA_CORRUPTION = "data_corruption"
    CYBER_ATTACK = "cyber_attack"
    NATURAL_DISASTER = "natural_disaster"
    HUMAN_ERROR = "human_error"
    NETWORK_OUTAGE = "network_outage"
    POWER_OUTAGE = "power_outage"

class RecoveryStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"
    FAILED = "failed"

class RecoveryPriority(Enum):
    CRITICAL = "critical"    # Life-critical medical data
    HIGH = "high"           # Patient care data
    MEDIUM = "medium"       # Administrative data
    LOW = "low"             # Archival data

@dataclass
class DisasterEvent:
    """Disaster event record."""
    event_id: str
    disaster_type: DisasterType
    occurred_at: datetime
    detected_at: datetime
    description: str
    affected_systems: List[str]
    impact_assessment: Dict[str, Any]
    recovery_initiated: bool = False
    recovery_completed: bool = False

@dataclass
class RecoveryPlan:
    """Disaster recovery plan definition."""
    plan_id: str
    disaster_types: List[DisasterType]
    priority: RecoveryPriority
    rto: int  # Recovery Time Objective (minutes)
    rpo: int  # Recovery Point Objective (minutes)
    steps: List[Dict[str, Any]]
    dependencies: List[str]
    validation_tests: List[Dict[str, Any]]

@dataclass
class SystemStatus:
    """System health status."""
    component: str
    status: RecoveryStatus
    last_check: datetime
    metrics: Dict[str, Any]
    issues: List[str]

class DisasterRecoveryManager:
    """
    Comprehensive disaster recovery manager for medical case management system.
    
    Features:
    - Multi-site backup and recovery
    - Automated failover capabilities
    - Business continuity planning
    - HIPAA-compliant recovery procedures
    - Real-time system monitoring
    - Recovery testing and validation
    """
    
    def __init__(self,
                 primary_neo4j_uri: str,
                 neo4j_user: str,
                 neo4j_password: str,
                 backup_sites: List[str],
                 recovery_plans_dir: Path):
        """
        Initialize disaster recovery manager.
        
        Args:
            primary_neo4j_uri: Primary Neo4j URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            backup_sites: List of backup site URIs
            recovery_plans_dir: Directory containing recovery plans
        """
        self.primary_neo4j_uri = primary_neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.backup_sites = backup_sites
        self.recovery_plans_dir = recovery_plans_dir
        
        self.driver = None
        self.recovery_plans: Dict[str, RecoveryPlan] = {}
        self.system_status: Dict[str, SystemStatus] = {}
        self.active_disasters: List[DisasterEvent] = []
        
        # Ensure recovery plans directory exists
        self.recovery_plans_dir.mkdir(parents=True, exist_ok=True)
        
        # Load recovery plans
        asyncio.create_task(self._load_recovery_plans())
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def connect(self):
        """Connect to primary Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.primary_neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Connected to primary Neo4j for disaster recovery")
        except Exception as e:
            logger.error(f"Failed to connect to primary Neo4j: {e}")
            # Try backup sites
            await self._try_backup_sites()
    
    async def _try_backup_sites(self):
        """Try connecting to backup sites."""
        for backup_uri in self.backup_sites:
            try:
                self.driver = GraphDatabase.driver(
                    backup_uri,
                    auth=(self.neo4j_user, self.neo4j_password)
                )
                async with self.driver.session() as session:
                    await session.run("RETURN 1")
                logger.info(f"Connected to backup site: {backup_uri}")
                return
            except Exception as e:
                logger.warning(f"Failed to connect to backup site {backup_uri}: {e}")
        
        raise RuntimeError("Failed to connect to any database sites")
    
    async def close(self):
        """Close database connection."""
        if self.driver:
            await self.driver.close()
            logger.info("Closed database connection")
    
    async def _load_recovery_plans(self):
        """Load disaster recovery plans from configuration files."""
        plan_files = list(self.recovery_plans_dir.glob("*.json"))
        
        for plan_file in plan_files:
            try:
                async with aiofiles.open(plan_file, 'r') as f:
                    plan_data = json.loads(await f.read())
                
                recovery_plan = RecoveryPlan(
                    plan_id=plan_data["plan_id"],
                    disaster_types=[DisasterType(dt) for dt in plan_data["disaster_types"]],
                    priority=RecoveryPriority(plan_data["priority"]),
                    rto=plan_data["rto"],
                    rpo=plan_data["rpo"],
                    steps=plan_data["steps"],
                    dependencies=plan_data.get("dependencies", []),
                    validation_tests=plan_data.get("validation_tests", [])
                )
                
                self.recovery_plans[recovery_plan.plan_id] = recovery_plan
                
            except Exception as e:
                logger.error(f"Failed to load recovery plan {plan_file}: {e}")
        
        logger.info(f"Loaded {len(self.recovery_plans)} disaster recovery plans")
    
    async def monitor_system_health(self) -> Dict[str, SystemStatus]:
        """
        Monitor system health and detect potential issues.
        
        Returns:
            Current system status
        """
        current_time = datetime.now()
        
        # Monitor Neo4j database
        db_status = await self._check_database_health()
        self.system_status["database"] = SystemStatus(
            component="database",
            status=db_status["status"],
            last_check=current_time,
            metrics=db_status["metrics"],
            issues=db_status["issues"]
        )
        
        # Monitor backup systems
        backup_status = await self._check_backup_health()
        self.system_status["backup"] = SystemStatus(
            component="backup",
            status=backup_status["status"],
            last_check=current_time,
            metrics=backup_status["metrics"],
            issues=backup_status["issues"]
        )
        
        # Monitor network connectivity
        network_status = await self._check_network_health()
        self.system_status["network"] = SystemStatus(
            component="network",
            status=network_status["status"],
            last_check=current_time,
            metrics=network_status["metrics"],
            issues=network_status["issues"]
        )
        
        # Monitor disk space
        storage_status = await self._check_storage_health()
        self.system_status["storage"] = SystemStatus(
            component="storage",
            status=storage_status["status"],
            last_check=current_time,
            metrics=storage_status["metrics"],
            issues=storage_status["issues"]
        )
        
        return self.system_status
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check Neo4j database health."""
        status = {
            "status": RecoveryStatus.HEALTHY,
            "metrics": {},
            "issues": []
        }
        
        try:
            async with self.driver.session() as session:
                # Check connectivity
                await session.run("RETURN 1")
                
                # Check database statistics
                result = await session.run("CALL dbms.queryJmx('org.neo4j:*')")
                metrics = {}
                
                async for record in result:
                    jmx_data = dict(record)
                    if "DatabaseSize" in str(jmx_data):
                        metrics["database_size"] = jmx_data.get("value", 0)
                
                # Check transaction status
                tx_result = await session.run("SHOW TRANSACTIONS")
                running_transactions = len([record async for record in tx_result])
                metrics["running_transactions"] = running_transactions
                
                # Check constraints and indexes
                constraints_result = await session.run("SHOW CONSTRAINTS")
                constraints_count = len([record async for record in constraints_result])
                metrics["constraints_count"] = constraints_count
                
                status["metrics"] = metrics
                
                # Determine status based on metrics
                if running_transactions > 100:
                    status["status"] = RecoveryStatus.DEGRADED
                    status["issues"].append("High number of running transactions")
                
                if constraints_count == 0:
                    status["status"] = RecoveryStatus.CRITICAL
                    status["issues"].append("No database constraints found")
                
        except Exception as e:
            status["status"] = RecoveryStatus.FAILED
            status["issues"].append(f"Database connection failed: {e}")
        
        return status
    
    async def _check_backup_health(self) -> Dict[str, Any]:
        """Check backup system health."""
        status = {
            "status": RecoveryStatus.HEALTHY,
            "metrics": {},
            "issues": []
        }
        
        # This would integrate with BackupManager
        # For now, simulate backup health check
        status["metrics"] = {
            "last_backup_age_hours": 2,
            "backup_success_rate": 0.98,
            "backup_storage_used": 0.65
        }
        
        if status["metrics"]["last_backup_age_hours"] > 24:
            status["status"] = RecoveryStatus.DEGRADED
            status["issues"].append("Last backup is older than 24 hours")
        
        if status["metrics"]["backup_success_rate"] < 0.95:
            status["status"] = RecoveryStatus.CRITICAL
            status["issues"].append("Backup success rate below threshold")
        
        return status
    
    async def _check_network_health(self) -> Dict[str, Any]:
        """Check network connectivity health."""
        status = {
            "status": RecoveryStatus.HEALTHY,
            "metrics": {},
            "issues": []
        }
        
        # Check connectivity to backup sites
        reachable_sites = 0
        total_sites = len(self.backup_sites)
        
        for backup_uri in self.backup_sites:
            try:
                # Simplified connectivity check
                # In production, use proper network monitoring
                test_driver = GraphDatabase.driver(
                    backup_uri,
                    auth=(self.neo4j_user, self.neo4j_password)
                )
                async with test_driver.session() as session:
                    await session.run("RETURN 1")
                reachable_sites += 1
                await test_driver.close()
            except Exception:
                pass
        
        status["metrics"] = {
            "reachable_backup_sites": reachable_sites,
            "total_backup_sites": total_sites,
            "backup_site_availability": reachable_sites / total_sites if total_sites > 0 else 0
        }
        
        if reachable_sites == 0:
            status["status"] = RecoveryStatus.CRITICAL
            status["issues"].append("No backup sites reachable")
        elif reachable_sites < total_sites * 0.5:
            status["status"] = RecoveryStatus.DEGRADED
            status["issues"].append("More than 50% of backup sites unreachable")
        
        return status
    
    async def _check_storage_health(self) -> Dict[str, Any]:
        """Check storage health."""
        status = {
            "status": RecoveryStatus.HEALTHY,
            "metrics": {},
            "issues": []
        }
        
        try:
            # Check disk usage
            disk_usage = shutil.disk_usage("/")
            total_space = disk_usage.total
            free_space = disk_usage.free
            used_percent = (total_space - free_space) / total_space
            
            status["metrics"] = {
                "total_space_gb": total_space / (1024**3),
                "free_space_gb": free_space / (1024**3),
                "used_percent": used_percent
            }
            
            if used_percent > 0.95:
                status["status"] = RecoveryStatus.CRITICAL
                status["issues"].append("Disk space critically low (<5% free)")
            elif used_percent > 0.85:
                status["status"] = RecoveryStatus.DEGRADED
                status["issues"].append("Disk space low (<15% free)")
            
        except Exception as e:
            status["status"] = RecoveryStatus.FAILED
            status["issues"].append(f"Storage check failed: {e}")
        
        return status
    
    async def declare_disaster(self,
                             disaster_type: DisasterType,
                             description: str,
                             affected_systems: List[str]) -> str:
        """
        Declare a disaster event and initiate response.
        
        Args:
            disaster_type: Type of disaster
            description: Description of the disaster
            affected_systems: List of affected systems
            
        Returns:
            Disaster event ID
        """
        event_id = f"disaster_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        disaster_event = DisasterEvent(
            event_id=event_id,
            disaster_type=disaster_type,
            occurred_at=datetime.now(),
            detected_at=datetime.now(),
            description=description,
            affected_systems=affected_systems,
            impact_assessment=await self._assess_impact(affected_systems)
        )
        
        self.active_disasters.append(disaster_event)
        
        logger.critical(f"DISASTER DECLARED: {event_id} - {disaster_type.value}")
        logger.critical(f"Description: {description}")
        logger.critical(f"Affected systems: {affected_systems}")
        
        # Save disaster record
        await self._save_disaster_record(disaster_event)
        
        # Initiate automated response
        await self._initiate_disaster_response(disaster_event)
        
        return event_id
    
    async def _assess_impact(self, affected_systems: List[str]) -> Dict[str, Any]:
        """Assess impact of disaster on systems."""
        impact = {
            "severity": "high",
            "estimated_downtime_minutes": 0,
            "data_loss_risk": "low",
            "patient_care_impact": "minimal",
            "compliance_risk": "low"
        }
        
        # Assess based on affected systems
        if "database" in affected_systems:
            impact["severity"] = "critical"
            impact["estimated_downtime_minutes"] = 120
            impact["data_loss_risk"] = "high"
            impact["patient_care_impact"] = "severe"
            impact["compliance_risk"] = "high"
        elif "backup" in affected_systems:
            impact["severity"] = "high"
            impact["estimated_downtime_minutes"] = 60
            impact["data_loss_risk"] = "medium"
            impact["compliance_risk"] = "medium"
        elif "network" in affected_systems:
            impact["severity"] = "medium"
            impact["estimated_downtime_minutes"] = 30
            impact["patient_care_impact"] = "moderate"
        
        return impact
    
    async def _initiate_disaster_response(self, disaster_event: DisasterEvent):
        """Initiate automated disaster response."""
        # Find applicable recovery plans
        applicable_plans = []
        
        for plan_id, plan in self.recovery_plans.items():
            if disaster_event.disaster_type in plan.disaster_types:
                applicable_plans.append(plan)
        
        if not applicable_plans:
            logger.error(f"No recovery plans found for disaster type: {disaster_event.disaster_type}")
            return
        
        # Sort by priority (critical first)
        applicable_plans.sort(key=lambda p: p.priority.value, reverse=True)
        
        # Execute recovery plans
        for plan in applicable_plans:
            try:
                await self._execute_recovery_plan(plan, disaster_event)
                disaster_event.recovery_initiated = True
            except Exception as e:
                logger.error(f"Failed to execute recovery plan {plan.plan_id}: {e}")
    
    async def _execute_recovery_plan(self, plan: RecoveryPlan, disaster_event: DisasterEvent):
        """
        Execute a disaster recovery plan.
        
        Args:
            plan: Recovery plan to execute
            disaster_event: Associated disaster event
        """
        logger.info(f"Executing recovery plan {plan.plan_id} for disaster {disaster_event.event_id}")
        
        # Check dependencies
        for dep_plan_id in plan.dependencies:
            # In production, verify dependent plans completed successfully
            pass
        
        # Execute recovery steps
        for step_index, step in enumerate(plan.steps):
            try:
                await self._execute_recovery_step(step, disaster_event)
                logger.info(f"Completed recovery step {step_index + 1}/{len(plan.steps)}: {step.get('name', 'Unnamed step')}")
            except Exception as e:
                logger.error(f"Recovery step {step_index + 1} failed: {e}")
                raise
        
        # Run validation tests
        for test in plan.validation_tests:
            try:
                test_result = await self._run_validation_test(test)
                if not test_result:
                    raise RuntimeError(f"Validation test failed: {test.get('name', 'Unnamed test')}")
            except Exception as e:
                logger.error(f"Validation test failed: {e}")
                raise
        
        logger.info(f"Recovery plan {plan.plan_id} completed successfully")
    
    async def _execute_recovery_step(self, step: Dict[str, Any], disaster_event: DisasterEvent):
        """Execute individual recovery step."""
        step_type = step.get("type", "manual")
        
        if step_type == "failover_database":
            await self._failover_to_backup_site()
        elif step_type == "restore_from_backup":
            await self._restore_from_backup(step.get("backup_id"))
        elif step_type == "notify_stakeholders":
            await self._notify_stakeholders(step.get("message", ""), disaster_event)
        elif step_type == "manual":
            logger.warning(f"Manual step required: {step.get('description', 'No description')}")
        else:
            logger.warning(f"Unknown recovery step type: {step_type}")
    
    async def _failover_to_backup_site(self):
        """Failover to backup database site."""
        if not self.backup_sites:
            raise RuntimeError("No backup sites configured")
        
        # Close current connection
        if self.driver:
            await self.driver.close()
        
        # Try backup sites in order
        for backup_uri in self.backup_sites:
            try:
                self.driver = GraphDatabase.driver(
                    backup_uri,
                    auth=(self.neo4j_user, self.neo4j_password)
                )
                async with self.driver.session() as session:
                    await session.run("RETURN 1")
                
                logger.info(f"Successfully failed over to backup site: {backup_uri}")
                return
                
            except Exception as e:
                logger.warning(f"Failover to {backup_uri} failed: {e}")
        
        raise RuntimeError("All backup sites unavailable")
    
    async def _restore_from_backup(self, backup_id: Optional[str] = None):
        """Restore from backup."""
        # This would integrate with BackupManager
        if backup_id:
            logger.info(f"Restoring from specific backup: {backup_id}")
        else:
            logger.info("Restoring from latest backup")
        
        # Placeholder for backup restoration logic
        # In production, this would call BackupManager.restore_backup()
    
    async def _notify_stakeholders(self, message: str, disaster_event: DisasterEvent):
        """Notify stakeholders of disaster and recovery status."""
        notification = {
            "event_id": disaster_event.event_id,
            "disaster_type": disaster_event.disaster_type.value,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "severity": "critical"
        }
        
        # In production, integrate with notification systems (email, SMS, Slack, etc.)
        logger.critical(f"STAKEHOLDER NOTIFICATION: {json.dumps(notification, indent=2)}")
    
    async def _run_validation_test(self, test: Dict[str, Any]) -> bool:
        """Run validation test."""
        test_type = test.get("type", "connectivity")
        
        if test_type == "connectivity":
            try:
                async with self.driver.session() as session:
                    await session.run("RETURN 1")
                return True
            except Exception:
                return False
        elif test_type == "data_integrity":
            try:
                async with self.driver.session() as session:
                    # Basic data integrity check
                    result = await session.run("MATCH (n) RETURN count(n) as count")
                    count = (await result.single())["count"]
                    return count > 0
            except Exception:
                return False
        else:
            logger.warning(f"Unknown test type: {test_type}")
            return True
    
    async def _save_disaster_record(self, disaster_event: DisasterEvent):
        """Save disaster record to database."""
        try:
            async with self.driver.session() as session:
                await session.run("""
                    CREATE (d:DisasterEvent {
                        event_id: $event_id,
                        disaster_type: $disaster_type,
                        occurred_at: $occurred_at,
                        detected_at: $detected_at,
                        description: $description,
                        affected_systems: $affected_systems,
                        impact_assessment: $impact_assessment,
                        recovery_initiated: $recovery_initiated,
                        recovery_completed: $recovery_completed
                    })
                """, {
                    "event_id": disaster_event.event_id,
                    "disaster_type": disaster_event.disaster_type.value,
                    "occurred_at": disaster_event.occurred_at.isoformat(),
                    "detected_at": disaster_event.detected_at.isoformat(),
                    "description": disaster_event.description,
                    "affected_systems": disaster_event.affected_systems,
                    "impact_assessment": json.dumps(disaster_event.impact_assessment),
                    "recovery_initiated": disaster_event.recovery_initiated,
                    "recovery_completed": disaster_event.recovery_completed
                })
        except Exception as e:
            logger.error(f"Failed to save disaster record: {e}")
    
    async def test_recovery_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Test disaster recovery plan in non-production environment.
        
        Args:
            plan_id: Recovery plan to test
            
        Returns:
            Test results
        """
        if plan_id not in self.recovery_plans:
            raise ValueError(f"Recovery plan not found: {plan_id}")
        
        plan = self.recovery_plans[plan_id]
        test_start = datetime.now()
        
        test_results = {
            "plan_id": plan_id,
            "test_started": test_start.isoformat(),
            "test_completed": None,
            "duration_minutes": 0,
            "steps_tested": 0,
            "steps_passed": 0,
            "steps_failed": 0,
            "validation_tests_passed": 0,
            "validation_tests_failed": 0,
            "overall_result": "PENDING",
            "issues": []
        }
        
        try:
            # Test each recovery step (in test mode)
            for step_index, step in enumerate(plan.steps):
                test_results["steps_tested"] += 1
                
                try:
                    # Simulate step execution
                    await self._simulate_recovery_step(step)
                    test_results["steps_passed"] += 1
                except Exception as e:
                    test_results["steps_failed"] += 1
                    test_results["issues"].append(f"Step {step_index + 1} failed: {e}")
            
            # Test validation tests
            for test in plan.validation_tests:
                try:
                    test_result = await self._run_validation_test(test)
                    if test_result:
                        test_results["validation_tests_passed"] += 1
                    else:
                        test_results["validation_tests_failed"] += 1
                        test_results["issues"].append(f"Validation test failed: {test.get('name', 'Unnamed')}")
                except Exception as e:
                    test_results["validation_tests_failed"] += 1
                    test_results["issues"].append(f"Validation test error: {e}")
            
            # Determine overall result
            if test_results["steps_failed"] == 0 and test_results["validation_tests_failed"] == 0:
                test_results["overall_result"] = "PASSED"
            elif test_results["steps_failed"] > 0:
                test_results["overall_result"] = "FAILED"
            else:
                test_results["overall_result"] = "PARTIAL"
            
        except Exception as e:
            test_results["overall_result"] = "ERROR"
            test_results["issues"].append(f"Test execution error: {e}")
        
        finally:
            test_end = datetime.now()
            test_results["test_completed"] = test_end.isoformat()
            test_results["duration_minutes"] = (test_end - test_start).total_seconds() / 60
        
        return test_results
    
    async def _simulate_recovery_step(self, step: Dict[str, Any]):
        """Simulate recovery step execution for testing."""
        step_type = step.get("type", "manual")
        
        # Simulate different step types
        if step_type == "failover_database":
            # Test connectivity to backup sites
            for backup_uri in self.backup_sites:
                test_driver = GraphDatabase.driver(
                    backup_uri,
                    auth=(self.neo4j_user, self.neo4j_password)
                )
                try:
                    async with test_driver.session() as session:
                        await session.run("RETURN 1")
                finally:
                    await test_driver.close()
        elif step_type == "restore_from_backup":
            # Simulate backup restoration test
            pass
        elif step_type == "notify_stakeholders":
            # Simulate notification
            pass
        
        # Add small delay to simulate execution time
        await asyncio.sleep(0.1)
    
    async def get_disaster_history(self, days: int = 90) -> List[DisasterEvent]:
        """Get disaster event history."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        disaster_events = []
        
        try:
            async with self.driver.session() as session:
                result = await session.run("""
                    MATCH (d:DisasterEvent)
                    WHERE datetime(d.occurred_at) >= datetime($cutoff_date)
                    RETURN d
                    ORDER BY d.occurred_at DESC
                """, {"cutoff_date": cutoff_date.isoformat()})
                
                async for record in result:
                    event_data = dict(record["d"])
                    
                    disaster_event = DisasterEvent(
                        event_id=event_data["event_id"],
                        disaster_type=DisasterType(event_data["disaster_type"]),
                        occurred_at=datetime.fromisoformat(event_data["occurred_at"]),
                        detected_at=datetime.fromisoformat(event_data["detected_at"]),
                        description=event_data["description"],
                        affected_systems=event_data["affected_systems"],
                        impact_assessment=json.loads(event_data["impact_assessment"]),
                        recovery_initiated=event_data["recovery_initiated"],
                        recovery_completed=event_data["recovery_completed"]
                    )
                    
                    disaster_events.append(disaster_event)
        
        except Exception as e:
            logger.error(f"Failed to get disaster history: {e}")
        
        return disaster_events
    
    async def generate_readiness_report(self) -> Dict[str, Any]:
        """Generate disaster readiness assessment report."""
        system_status = await self.monitor_system_health()
        
        report = {
            "assessment_date": datetime.now().isoformat(),
            "overall_readiness": "READY",
            "system_health": {},
            "recovery_plans": {
                "total_plans": len(self.recovery_plans),
                "plans_by_priority": {},
                "coverage_gaps": []
            },
            "backup_status": {},
            "recommendations": []
        }
        
        # Assess system health
        critical_issues = 0
        for component, status in system_status.items():
            report["system_health"][component] = {
                "status": status.status.value,
                "issues_count": len(status.issues),
                "last_check": status.last_check.isoformat()
            }
            
            if status.status in [RecoveryStatus.CRITICAL, RecoveryStatus.FAILED]:
                critical_issues += 1
        
        if critical_issues > 0:
            report["overall_readiness"] = "NOT_READY"
            report["recommendations"].append(f"Address {critical_issues} critical system issues")
        
        # Assess recovery plan coverage
        covered_disasters = set()
        for plan in self.recovery_plans.values():
            for disaster_type in plan.disaster_types:
                covered_disasters.add(disaster_type)
            
            priority = plan.priority.value
            if priority not in report["recovery_plans"]["plans_by_priority"]:
                report["recovery_plans"]["plans_by_priority"][priority] = 0
            report["recovery_plans"]["plans_by_priority"][priority] += 1
        
        # Check for coverage gaps
        all_disasters = set(DisasterType)
        uncovered_disasters = all_disasters - covered_disasters
        
        if uncovered_disasters:
            report["recovery_plans"]["coverage_gaps"] = [dt.value for dt in uncovered_disasters]
            report["recommendations"].append("Create recovery plans for uncovered disaster types")
        
        # Generate recommendations
        if not self.backup_sites:
            report["recommendations"].append("Configure backup sites for failover capability")
        
        if len(self.recovery_plans) == 0:
            report["overall_readiness"] = "NOT_READY"
            report["recommendations"].append("Create disaster recovery plans")
        
        return report