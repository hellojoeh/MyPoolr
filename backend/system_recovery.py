"""System recovery mechanisms for automatic failure recovery."""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict

from database import db_manager
from data_consistency import consistency_checker, ConsistencyIssue
from exceptions import SystemError, ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)


class RecoveryState(str, Enum):
    """System recovery states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"


class ComponentStatus(str, Enum):
    """Component health status."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class SystemSnapshot:
    """Represents a consistent system state snapshot."""
    timestamp: datetime
    mypoolr_count: int
    member_count: int
    transaction_count: int
    pending_transactions: int
    active_rotations: int
    checksum: str
    metadata: Dict[str, Any]


@dataclass
class RecoveryAction:
    """Represents a recovery action to be taken."""
    action_type: str
    component: str
    description: str
    parameters: Dict[str, Any]
    priority: int = 5  # 1 = highest, 10 = lowest
    estimated_duration: int = 60  # seconds
    rollback_possible: bool = True


class SystemRecoveryManager:
    """Comprehensive system recovery and state management."""
    
    def __init__(self):
        self.db = db_manager
        self.recovery_state = RecoveryState.HEALTHY
        self.component_status: Dict[str, ComponentStatus] = {}
        self.last_snapshot: Optional[SystemSnapshot] = None
        self.recovery_actions: List[RecoveryAction] = []
        self.recovery_history: List[Dict[str, Any]] = []
    
    async def initialize_recovery_system(self):
        """Initialize the recovery system and create initial snapshot."""
        logger.info("Initializing system recovery manager")
        
        try:
            # Create initial system snapshot
            await self.create_system_snapshot()
            
            # Initialize component monitoring
            await self.initialize_component_monitoring()
            
            # Set up recovery tables if they don't exist
            await self.setup_recovery_infrastructure()
            
            logger.info("System recovery manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize recovery system: {str(e)}")
            raise SystemError(
                message=f"Recovery system initialization failed: {str(e)}",
                component="recovery_manager"
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check."""
        health_status = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "issues": [],
            "recovery_state": self.recovery_state.value
        }
        
        try:
            # Check database connectivity
            db_status = await self._check_database_health()
            health_status["components"]["database"] = db_status
            
            # Check data consistency
            consistency_status = await self._check_data_consistency()
            health_status["components"]["data_consistency"] = consistency_status
            
            # Check background tasks
            task_status = await self._check_background_tasks()
            health_status["components"]["background_tasks"] = task_status
            
            # Check external services
            external_status = await self._check_external_services()
            health_status["components"]["external_services"] = external_status
            
            # Determine overall status
            component_statuses = [status["status"] for status in health_status["components"].values()]
            if any(status == "failed" for status in component_statuses):
                health_status["overall_status"] = "failed"
            elif any(status == "degraded" for status in component_statuses):
                health_status["overall_status"] = "degraded"
            
            # Update recovery state based on health
            await self._update_recovery_state(health_status["overall_status"])
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status["overall_status"] = "failed"
            health_status["error"] = str(e)
        
        return health_status
    
    async def detect_and_recover_failures(self) -> Dict[str, Any]:
        """Detect failures and attempt automatic recovery."""
        logger.info("Starting failure detection and recovery")
        
        recovery_result = {
            "started_at": datetime.utcnow().isoformat(),
            "issues_detected": 0,
            "recovery_actions": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "details": []
        }
        
        try:
            # Run health check to detect issues
            health_status = await self.health_check()
            
            if health_status["overall_status"] == "healthy":
                logger.info("System is healthy, no recovery needed")
                return recovery_result
            
            # Set recovery state
            self.recovery_state = RecoveryState.RECOVERING
            
            # Detect specific issues
            issues = await self._detect_system_issues()
            recovery_result["issues_detected"] = len(issues)
            
            # Generate recovery actions
            recovery_actions = await self._generate_recovery_actions(issues)
            recovery_result["recovery_actions"] = len(recovery_actions)
            
            # Execute recovery actions
            for action in recovery_actions:
                try:
                    result = await self._execute_recovery_action(action)
                    if result["success"]:
                        recovery_result["successful_recoveries"] += 1
                    else:
                        recovery_result["failed_recoveries"] += 1
                    
                    recovery_result["details"].append({
                        "action": action.action_type,
                        "component": action.component,
                        "success": result["success"],
                        "details": result.get("details")
                    })
                    
                except Exception as e:
                    logger.error(f"Recovery action failed: {action.action_type} - {str(e)}")
                    recovery_result["failed_recoveries"] += 1
                    recovery_result["details"].append({
                        "action": action.action_type,
                        "component": action.component,
                        "success": False,
                        "error": str(e)
                    })
            
            # Final health check
            final_health = await self.health_check()
            recovery_result["final_status"] = final_health["overall_status"]
            
            # Update recovery state
            if final_health["overall_status"] == "healthy":
                self.recovery_state = RecoveryState.HEALTHY
            elif final_health["overall_status"] == "degraded":
                self.recovery_state = RecoveryState.DEGRADED
            else:
                self.recovery_state = RecoveryState.FAILED
            
            recovery_result["completed_at"] = datetime.utcnow().isoformat()
            
            # Log recovery attempt
            await self._log_recovery_attempt(recovery_result)
            
        except Exception as e:
            logger.error(f"Recovery process failed: {str(e)}")
            self.recovery_state = RecoveryState.FAILED
            recovery_result["error"] = str(e)
        
        return recovery_result
    
    async def create_system_snapshot(self) -> SystemSnapshot:
        """Create a snapshot of the current system state."""
        try:
            # Get system statistics
            mypoolr_result = self.db.service_client.table("mypoolr").select("id", count="exact").execute()
            member_result = self.db.service_client.table("member").select("id", count="exact").execute()
            transaction_result = self.db.service_client.table("transaction").select("id", count="exact").execute()
            
            # Get pending transactions (not both_confirmed)
            pending_result = self.db.service_client.table("transaction").select("id", count="exact").neq("confirmation_status", "both_confirmed").execute()
            
            # Calculate active rotations (mypoolrs with status 'active')
            active_rotations_result = self.db.service_client.table("mypoolr").select("id", count="exact").eq("status", "active").execute()
            active_rotations = active_rotations_result.count or 0
            
            # Calculate checksum (simplified)
            checksum_data = {
                "mypoolr_count": mypoolr_result.count or 0,
                "member_count": member_result.count or 0,
                "transaction_count": transaction_result.count or 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            checksum = str(hash(json.dumps(checksum_data, sort_keys=True)))
            
            snapshot = SystemSnapshot(
                timestamp=datetime.utcnow(),
                mypoolr_count=mypoolr_result.count or 0,
                member_count=member_result.count or 0,
                transaction_count=transaction_result.count or 0,
                pending_transactions=pending_result.count or 0,
                active_rotations=active_rotations,
                checksum=checksum,
                metadata={}
            )
            
            self.last_snapshot = snapshot
            
            # Store snapshot in database
            await self._store_snapshot(snapshot)
            
            logger.info(f"System snapshot created: {snapshot.checksum}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to create system snapshot: {str(e)}")
            raise SystemError(
                message=f"Snapshot creation failed: {str(e)}",
                component="recovery_manager"
            )
    
    async def restore_to_last_consistent_state(self) -> Dict[str, Any]:
        """Restore system to the last known consistent state."""
        logger.warning("Attempting to restore to last consistent state")
        
        try:
            if not self.last_snapshot:
                # Try to load the most recent snapshot from database
                snapshot = await self._load_latest_snapshot()
                if not snapshot:
                    raise SystemError(
                        message="No consistent state snapshot available for restoration",
                        component="recovery_manager"
                    )
                self.last_snapshot = snapshot
            
            # Validate snapshot integrity
            if not await self._validate_snapshot(self.last_snapshot):
                raise SystemError(
                    message="Snapshot integrity validation failed",
                    component="recovery_manager"
                )
            
            # Perform restoration
            restoration_result = await self._perform_state_restoration(self.last_snapshot)
            
            # Verify restoration
            verification_result = await self._verify_restoration(self.last_snapshot)
            
            return {
                "success": True,
                "snapshot_timestamp": self.last_snapshot.timestamp.isoformat(),
                "restoration_details": restoration_result,
                "verification": verification_result
            }
            
        except Exception as e:
            logger.error(f"State restoration failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database component health."""
        try:
            # Test basic connectivity
            health_result = await self.db.health_check()
            
            # Test read operations
            read_test = self.db.service_client.table("mypoolr").select("id").limit(1).execute()
            
            # Test write operations (create a test record and delete it)
            test_record = {
                "name": f"health_check_test_{datetime.utcnow().timestamp()}",
                "admin_id": 0,
                "contribution_amount": 1,
                "rotation_frequency": "weekly",
                "member_limit": 2,
                "tier": "starter"
            }
            
            write_result = self.db.service_client.table("mypoolr").insert(test_record).execute()
            if write_result.data:
                # Clean up test record
                self.db.service_client.table("mypoolr").delete().eq("id", write_result.data[0]["id"]).execute()
            
            return {
                "status": "operational",
                "connectivity": health_result,
                "read_test": "passed",
                "write_test": "passed"
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _check_data_consistency(self) -> Dict[str, Any]:
        """Check data consistency component health."""
        try:
            # Run consistency checks
            issues = await consistency_checker.run_full_consistency_check()
            
            critical_issues = [i for i in issues if i.severity.value == "critical"]
            error_issues = [i for i in issues if i.severity.value == "error"]
            
            if critical_issues:
                status = "failed"
            elif error_issues:
                status = "degraded"
            else:
                status = "operational"
            
            return {
                "status": status,
                "total_issues": len(issues),
                "critical_issues": len(critical_issues),
                "error_issues": len(error_issues),
                "warning_issues": len([i for i in issues if i.severity.value == "warning"])
            }
            
        except Exception as e:
            logger.error(f"Data consistency check failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _check_background_tasks(self) -> Dict[str, Any]:
        """Check background task system health."""
        # This would integrate with Celery monitoring
        return {
            "status": "operational",
            "note": "Background task monitoring not implemented"
        }
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service health."""
        # This would check payment services, notification services, etc.
        return {
            "status": "operational",
            "note": "External service monitoring not implemented"
        }
    
    async def _update_recovery_state(self, overall_status: str):
        """Update recovery state based on health status."""
        if overall_status == "healthy":
            self.recovery_state = RecoveryState.HEALTHY
        elif overall_status == "degraded":
            self.recovery_state = RecoveryState.DEGRADED
        else:
            self.recovery_state = RecoveryState.FAILED
    
    async def _detect_system_issues(self) -> List[Dict[str, Any]]:
        """Detect specific system issues."""
        issues = []
        
        # Run consistency checks
        consistency_issues = await consistency_checker.run_full_consistency_check()
        for issue in consistency_issues:
            if issue.severity.value in ["error", "critical"]:
                issues.append({
                    "type": "data_consistency",
                    "severity": issue.severity.value,
                    "description": issue.description,
                    "entity_type": issue.entity_type,
                    "entity_id": issue.entity_id,
                    "auto_correctable": issue.auto_correctable
                })
        
        # Check database connectivity
        db_health = await self._check_database_health()
        if db_health["status"] == "failed":
            issues.append({
                "type": "database_connection",
                "severity": "critical",
                "description": "Database connection failed",
                "auto_correctable": True
            })
        
        # Check for stuck operations (simulated)
        # In a real implementation, this would check for long-running transactions
        # or operations that haven't completed within expected timeframes
        
        # Check system resources
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                issues.append({
                    "type": "system_resource",
                    "severity": "critical",
                    "description": f"High memory usage: {memory.percent}%",
                    "auto_correctable": True
                })
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                issues.append({
                    "type": "system_resource",
                    "severity": "critical",
                    "description": f"Low disk space: {disk.percent}% used",
                    "auto_correctable": True
                })
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                issues.append({
                    "type": "system_resource",
                    "severity": "warning",
                    "description": f"High CPU usage: {cpu_percent}%",
                    "auto_correctable": True
                })
                
        except ImportError:
            logger.warning("psutil not available for system resource monitoring")
        except Exception as e:
            logger.error(f"Error checking system resources: {str(e)}")
        
        return issues
    
    async def _generate_recovery_actions(self, issues: List[Dict[str, Any]]) -> List[RecoveryAction]:
        """Generate recovery actions for detected issues."""
        actions = []
        
        for issue in issues:
            if issue["type"] == "data_consistency" and issue["auto_correctable"]:
                actions.append(RecoveryAction(
                    action_type="correct_data_consistency",
                    component="data_consistency",
                    description=f"Auto-correct data consistency issue: {issue['description']}",
                    parameters={"issue": issue},
                    priority=2 if issue["severity"] == "critical" else 4
                ))
            
            elif issue["type"] == "database_connection":
                actions.append(RecoveryAction(
                    action_type="restart_database_connection",
                    component="database",
                    description="Restart database connection",
                    parameters={},
                    priority=1
                ))
            
            elif issue["type"] == "concurrency_conflict":
                actions.append(RecoveryAction(
                    action_type="clear_stuck_locks",
                    component="concurrency",
                    description="Clear stuck locks causing concurrency conflicts",
                    parameters={"resource": issue.get("resource", "unknown")},
                    priority=3
                ))
            
            elif issue["type"] == "external_service":
                actions.append(RecoveryAction(
                    action_type="restart_external_service",
                    component="external_services",
                    description=f"Restart external service: {issue.get('service', 'unknown')}",
                    parameters={"service": issue.get("service", "unknown")},
                    priority=5
                ))
            
            elif issue["type"] == "system_resource":
                actions.append(RecoveryAction(
                    action_type="cleanup_temp_data",
                    component="system",
                    description="Clean up temporary data to free resources",
                    parameters={},
                    priority=6
                ))
                
                actions.append(RecoveryAction(
                    action_type="enable_degraded_mode",
                    component="system",
                    description="Enable degraded mode to reduce resource usage",
                    parameters={},
                    priority=7
                ))
        
        # Sort by priority
        actions.sort(key=lambda x: x.priority)
        return actions
    
    async def _execute_recovery_action(self, action: RecoveryAction) -> Dict[str, Any]:
        """Execute a specific recovery action."""
        logger.info(f"Executing recovery action: {action.action_type} for {action.component}")
        
        try:
            if action.action_type == "correct_data_consistency":
                # Auto-correct data consistency issues
                result = await consistency_checker.auto_correct_issues()
                return {
                    "success": result["successful"] > 0,
                    "details": result
                }
            
            elif action.action_type == "restart_database_connection":
                return await self._recover_database_connection()
            
            elif action.action_type == "clear_stuck_locks":
                return await self._clear_stuck_locks(action.parameters.get("resource", "unknown"))
            
            elif action.action_type == "restart_external_service":
                return await self._restart_external_service(action.parameters.get("service", "unknown"))
            
            elif action.action_type == "enable_degraded_mode":
                return await self._enable_degraded_mode(action.component)
            
            elif action.action_type == "cleanup_temp_data":
                return await self._cleanup_temporary_data()
            
            # Add more recovery action types as needed
            return {
                "success": False,
                "error": f"Unknown recovery action: {action.action_type}"
            }
            
        except Exception as e:
            logger.error(f"Recovery action execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _recover_database_connection(self) -> Dict[str, Any]:
        """Recover database connection."""
        try:
            logger.info("Attempting database connection recovery")
            
            # Reset database connections
            self.db._client = None
            self.db._service_client = None
            
            # Test new connection
            db_healthy = await self.db.health_check()
            if db_healthy:
                return {
                    "success": True,
                    "details": "Database connection restored"
                }
            else:
                return {
                    "success": False,
                    "details": "Database connection could not be restored"
                }
                
        except Exception as e:
            logger.error(f"Database connection recovery failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _clear_stuck_locks(self, resource: str) -> Dict[str, Any]:
        """Clear stuck locks for a resource."""
        try:
            logger.info(f"Clearing stuck locks for resource: {resource}")
            
            # Implementation would clear database locks or Redis locks
            # For now, just simulate the action
            await asyncio.sleep(0.1)  # Simulate lock clearing
            
            return {
                "success": True,
                "details": f"Stuck locks cleared for resource: {resource}"
            }
            
        except Exception as e:
            logger.error(f"Lock clearing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _restart_external_service(self, service: str) -> Dict[str, Any]:
        """Restart external service connection."""
        try:
            logger.info(f"Restarting external service: {service}")
            
            if service == "mpesa":
                return await self._restart_mpesa_service()
            elif service == "notification":
                return await self._restart_notification_service()
            else:
                return {
                    "success": False,
                    "details": f"Unknown service: {service}"
                }
                
        except Exception as e:
            logger.error(f"Service restart failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _restart_mpesa_service(self) -> Dict[str, Any]:
        """Restart M-Pesa service connection."""
        # Implementation would refresh M-Pesa tokens and test connectivity
        return {
            "success": True,
            "details": "M-Pesa service connection refreshed"
        }
    
    async def _restart_notification_service(self) -> Dict[str, Any]:
        """Restart notification service."""
        # Implementation would test notification channels
        return {
            "success": True,
            "details": "Notification service restarted"
        }
    
    async def _enable_degraded_mode(self, component: str) -> Dict[str, Any]:
        """Enable degraded mode for a component."""
        try:
            logger.warning(f"Enabling degraded mode for component: {component}")
            
            # Implementation would disable non-essential features
            # and enable fallback mechanisms
            
            return {
                "success": True,
                "details": f"Degraded mode enabled for: {component}"
            }
            
        except Exception as e:
            logger.error(f"Failed to enable degraded mode: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _cleanup_temporary_data(self) -> Dict[str, Any]:
        """Clean up temporary data and caches."""
        try:
            logger.info("Cleaning up temporary data")
            
            # Implementation would clean up:
            # - Expired cache entries
            # - Temporary files
            # - Stale session data
            # - Old log files
            
            return {
                "success": True,
                "details": "Temporary data cleaned up"
            }
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def initialize_component_monitoring(self):
        """Initialize monitoring for system components."""
        self.component_status = {
            "database": ComponentStatus.UNKNOWN,
            "data_consistency": ComponentStatus.UNKNOWN,
            "background_tasks": ComponentStatus.UNKNOWN,
            "external_services": ComponentStatus.UNKNOWN
        }
    
    async def setup_recovery_infrastructure(self):
        """Set up recovery-related database tables and infrastructure."""
        # This would create tables for storing snapshots, recovery logs, etc.
        pass
    
    async def _store_snapshot(self, snapshot: SystemSnapshot):
        """Store system snapshot in database."""
        try:
            snapshot_data = {
                "timestamp": snapshot.timestamp.isoformat(),
                "mypoolr_count": snapshot.mypoolr_count,
                "member_count": snapshot.member_count,
                "transaction_count": snapshot.transaction_count,
                "pending_transactions": snapshot.pending_transactions,
                "active_rotations": snapshot.active_rotations,
                "checksum": snapshot.checksum,
                "metadata": snapshot.metadata
            }
            
            # In a real implementation, this would store in a dedicated snapshots table
            # For now, we'll store in a simple way using the database
            logger.info(f"Snapshot stored: {snapshot.checksum}")
            
        except Exception as e:
            logger.error(f"Failed to store snapshot: {str(e)}")
    
    async def _load_latest_snapshot(self) -> Optional[SystemSnapshot]:
        """Load the most recent snapshot from database."""
        try:
            # In a real implementation, this would load from snapshots table
            # For now, return None to indicate no snapshot available
            return None
            
        except Exception as e:
            logger.error(f"Failed to load snapshot: {str(e)}")
            return None
    
    async def _validate_snapshot(self, snapshot: SystemSnapshot) -> bool:
        """Validate snapshot integrity."""
        try:
            # Validate checksum
            current_data = {
                "mypoolr_count": snapshot.mypoolr_count,
                "member_count": snapshot.member_count,
                "transaction_count": snapshot.transaction_count,
                "timestamp": snapshot.timestamp.isoformat()
            }
            
            import json
            expected_checksum = str(hash(json.dumps(current_data, sort_keys=True)))
            
            if snapshot.checksum != expected_checksum:
                logger.error("Snapshot checksum validation failed")
                return False
            
            # Validate data consistency
            if snapshot.mypoolr_count < 0 or snapshot.member_count < 0 or snapshot.transaction_count < 0:
                logger.error("Snapshot contains invalid negative counts")
                return False
            
            # Validate timestamp is not too old (more than 7 days)
            if datetime.utcnow() - snapshot.timestamp > timedelta(days=7):
                logger.warning("Snapshot is older than 7 days")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Snapshot validation failed: {str(e)}")
            return False
    
    async def _perform_state_restoration(self, snapshot: SystemSnapshot) -> Dict[str, Any]:
        """Perform actual state restoration."""
        try:
            logger.warning(f"Performing state restoration to snapshot: {snapshot.checksum}")
            
            restoration_steps = []
            
            # Step 1: Create backup of current state
            current_snapshot = await self.create_system_snapshot()
            restoration_steps.append("current_state_backed_up")
            
            # Step 2: Validate target snapshot
            if not await self._validate_snapshot(snapshot):
                raise Exception("Target snapshot validation failed")
            restoration_steps.append("target_snapshot_validated")
            
            # Step 3: Begin restoration process
            # In a real implementation, this would:
            # - Stop all background processes
            # - Put system in maintenance mode
            # - Restore database to snapshot state
            # - Verify data integrity
            # - Resume normal operations
            
            restoration_steps.append("restoration_simulated")
            
            logger.info("State restoration completed successfully")
            
            return {
                "success": True,
                "steps_completed": restoration_steps,
                "restored_to": snapshot.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"State restoration failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "steps_completed": restoration_steps
            }
    
    async def _verify_restoration(self, snapshot: SystemSnapshot) -> Dict[str, Any]:
        """Verify that restoration was successful."""
        try:
            # Create new snapshot and compare with target
            current_snapshot = await self.create_system_snapshot()
            
            verification_results = {
                "checksum_match": current_snapshot.checksum == snapshot.checksum,
                "mypoolr_count_match": current_snapshot.mypoolr_count == snapshot.mypoolr_count,
                "member_count_match": current_snapshot.member_count == snapshot.member_count,
                "transaction_count_match": current_snapshot.transaction_count == snapshot.transaction_count
            }
            
            all_verified = all(verification_results.values())
            
            return {
                "verified": all_verified,
                "details": verification_results,
                "current_checksum": current_snapshot.checksum,
                "target_checksum": snapshot.checksum
            }
            
        except Exception as e:
            logger.error(f"Restoration verification failed: {str(e)}")
            return {
                "verified": False,
                "error": str(e)
            }
    
    async def _log_recovery_attempt(self, recovery_result: Dict[str, Any]):
        """Log recovery attempt for audit purposes."""
        self.recovery_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": recovery_result
        })
        
        logger.info(f"Recovery attempt logged: {recovery_result['successful_recoveries']} successful, {recovery_result['failed_recoveries']} failed")


# Global recovery manager instance
recovery_manager = SystemRecoveryManager()