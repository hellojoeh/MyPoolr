"""Failure isolation and administrator alerting system."""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from exceptions import MyPoolrException, ErrorSeverity, ErrorCategory
from audit_logger import audit_logger

logger = logging.getLogger(__name__)


class IsolationLevel(str, Enum):
    """Levels of failure isolation."""
    NONE = "none"
    COMPONENT = "component"
    SERVICE = "service"
    SYSTEM = "system"


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class FailurePattern:
    """Represents a failure pattern for detection."""
    name: str
    description: str
    error_codes: Set[str]
    error_categories: Set[ErrorCategory]
    frequency_threshold: int  # Number of occurrences
    time_window_minutes: int  # Time window for frequency check
    isolation_level: IsolationLevel
    auto_isolate: bool = True


@dataclass
class IsolationAction:
    """Represents an isolation action taken."""
    timestamp: datetime
    component: str
    isolation_level: IsolationLevel
    reason: str
    auto_triggered: bool
    details: Dict[str, Any]


@dataclass
class AdminAlert:
    """Represents an administrator alert."""
    id: str
    timestamp: datetime
    severity: ErrorSeverity
    title: str
    message: str
    component: str
    error_details: Dict[str, Any]
    channels: List[AlertChannel]
    acknowledged: bool = False
    resolved: bool = False


class FailureIsolationManager:
    """Manages failure isolation and administrator alerting."""
    
    def __init__(self):
        self.failure_history: List[MyPoolrException] = []
        self.isolation_actions: List[IsolationAction] = []
        self.admin_alerts: List[AdminAlert] = []
        self.isolated_components: Dict[str, IsolationAction] = {}
        self.failure_patterns = self._initialize_failure_patterns()
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_minutes = 15  # Minimum time between similar alerts
    
    def _initialize_failure_patterns(self) -> List[FailurePattern]:
        """Initialize predefined failure patterns."""
        return [
            FailurePattern(
                name="database_connection_failures",
                description="Multiple database connection failures",
                error_codes={"DATABASE_ERROR", "CONNECTION_ERROR"},
                error_categories={ErrorCategory.DATABASE},
                frequency_threshold=3,
                time_window_minutes=5,
                isolation_level=IsolationLevel.COMPONENT,
                auto_isolate=True
            ),
            FailurePattern(
                name="security_violations",
                description="Security violation attempts",
                error_codes={"SECURITY_ERROR", "UNAUTHORIZED_ACCESS"},
                error_categories={ErrorCategory.SECURITY},
                frequency_threshold=2,
                time_window_minutes=10,
                isolation_level=IsolationLevel.SERVICE,
                auto_isolate=True
            ),
            FailurePattern(
                name="data_consistency_errors",
                description="Data consistency violations",
                error_codes={"DATA_CONSISTENCY_ERROR"},
                error_categories={ErrorCategory.DATA_CONSISTENCY},
                frequency_threshold=1,  # Even one is serious
                time_window_minutes=1,
                isolation_level=IsolationLevel.COMPONENT,
                auto_isolate=True
            ),
            FailurePattern(
                name="concurrent_operation_conflicts",
                description="Multiple concurrency conflicts",
                error_codes={"CONCURRENCY_ERROR"},
                error_categories={ErrorCategory.CONCURRENCY},
                frequency_threshold=5,
                time_window_minutes=10,
                isolation_level=IsolationLevel.COMPONENT,
                auto_isolate=False  # May be temporary
            ),
            FailurePattern(
                name="external_service_failures",
                description="External service unavailability",
                error_codes={"EXTERNAL_SERVICE_ERROR"},
                error_categories={ErrorCategory.EXTERNAL_SERVICE},
                frequency_threshold=3,
                time_window_minutes=15,
                isolation_level=IsolationLevel.SERVICE,
                auto_isolate=False  # May recover
            ),
            FailurePattern(
                name="system_resource_exhaustion",
                description="System resource exhaustion",
                error_codes={"SYSTEM_ERROR", "RESOURCE_EXHAUSTED"},
                error_categories={ErrorCategory.SYSTEM},
                frequency_threshold=2,
                time_window_minutes=5,
                isolation_level=IsolationLevel.SYSTEM,
                auto_isolate=True
            )
        ]
    
    async def handle_failure(self, error: MyPoolrException) -> Dict[str, Any]:
        """Handle a failure with potential isolation and alerting."""
        # Record the failure
        self.failure_history.append(error)
        
        # Clean up old failures (keep last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.failure_history = [
            f for f in self.failure_history
            if f.timestamp > cutoff_time
        ]
        
        result = {
            "failure_recorded": True,
            "patterns_detected": [],
            "isolation_triggered": False,
            "alerts_sent": []
        }
        
        try:
            # Check for failure patterns
            detected_patterns = await self._detect_failure_patterns(error)
            result["patterns_detected"] = [p.name for p in detected_patterns]
            
            # Handle each detected pattern
            for pattern in detected_patterns:
                # Trigger isolation if needed
                if pattern.auto_isolate and not self._is_component_isolated(pattern.name):
                    isolation_result = await self._trigger_isolation(pattern, error)
                    if isolation_result["success"]:
                        result["isolation_triggered"] = True
                
                # Send administrator alerts
                alert_result = await self._send_admin_alert(pattern, error)
                if alert_result["sent"]:
                    result["alerts_sent"].append(alert_result["alert_id"])
            
            # Log the handling result
            await audit_logger.log_system_action(
                action="failure_handled",
                component="failure_isolation",
                details={
                    "error_code": error.error_code,
                    "patterns_detected": len(detected_patterns),
                    "isolation_triggered": result["isolation_triggered"],
                    "alerts_sent": len(result["alerts_sent"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling failure: {str(e)}")
            result["error"] = str(e)
        
        return result
    
    async def _detect_failure_patterns(self, current_error: MyPoolrException) -> List[FailurePattern]:
        """Detect failure patterns based on recent history."""
        detected_patterns = []
        
        for pattern in self.failure_patterns:
            # Check if current error matches pattern criteria
            if not self._error_matches_pattern(current_error, pattern):
                continue
            
            # Count matching errors in time window
            time_window_start = datetime.utcnow() - timedelta(minutes=pattern.time_window_minutes)
            matching_errors = [
                error for error in self.failure_history
                if (error.timestamp >= time_window_start and 
                    self._error_matches_pattern(error, pattern))
            ]
            
            # Check if frequency threshold is met
            if len(matching_errors) >= pattern.frequency_threshold:
                detected_patterns.append(pattern)
                logger.warning(
                    f"Failure pattern detected: {pattern.name} "
                    f"({len(matching_errors)} occurrences in {pattern.time_window_minutes} minutes)"
                )
        
        return detected_patterns
    
    def _error_matches_pattern(self, error: MyPoolrException, pattern: FailurePattern) -> bool:
        """Check if an error matches a failure pattern."""
        # Check error code match
        if pattern.error_codes and error.error_code not in pattern.error_codes:
            return False
        
        # Check category match
        if pattern.error_categories and error.category not in pattern.error_categories:
            return False
        
        return True
    
    async def _trigger_isolation(self, pattern: FailurePattern, error: MyPoolrException) -> Dict[str, Any]:
        """Trigger isolation based on detected pattern."""
        component = self._determine_component_from_error(error)
        
        isolation_action = IsolationAction(
            timestamp=datetime.utcnow(),
            component=component,
            isolation_level=pattern.isolation_level,
            reason=f"Pattern detected: {pattern.name}",
            auto_triggered=True,
            details={
                "pattern_name": pattern.name,
                "error_code": error.error_code,
                "error_message": error.message
            }
        )
        
        try:
            # Apply isolation
            success = await self._apply_isolation(isolation_action)
            
            if success:
                self.isolation_actions.append(isolation_action)
                self.isolated_components[component] = isolation_action
                
                logger.warning(
                    f"Component isolated: {component} "
                    f"(Level: {pattern.isolation_level.value}, Reason: {pattern.name})"
                )
                
                # Log isolation action
                await audit_logger.log_system_action(
                    action="component_isolated",
                    component="failure_isolation",
                    details={
                        "isolated_component": component,
                        "isolation_level": pattern.isolation_level.value,
                        "reason": pattern.name,
                        "auto_triggered": True
                    }
                )
                
                return {"success": True, "component": component}
            else:
                return {"success": False, "reason": "Failed to apply isolation"}
                
        except Exception as e:
            logger.error(f"Failed to trigger isolation: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _apply_isolation(self, action: IsolationAction) -> bool:
        """Apply the actual isolation measures."""
        try:
            if action.isolation_level == IsolationLevel.COMPONENT:
                # Isolate specific component (e.g., disable certain endpoints)
                return await self._isolate_component(action.component)
            
            elif action.isolation_level == IsolationLevel.SERVICE:
                # Isolate entire service (e.g., disable external integrations)
                return await self._isolate_service(action.component)
            
            elif action.isolation_level == IsolationLevel.SYSTEM:
                # System-wide isolation (e.g., read-only mode)
                return await self._isolate_system(action.component)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to apply isolation: {str(e)}")
            return False
    
    async def _isolate_component(self, component: str) -> bool:
        """Isolate a specific component."""
        # Implementation would disable specific functionality
        logger.warning(f"Component isolation applied: {component}")
        return True
    
    async def _isolate_service(self, component: str) -> bool:
        """Isolate an entire service."""
        # Implementation would disable service integrations
        logger.warning(f"Service isolation applied: {component}")
        return True
    
    async def _isolate_system(self, component: str) -> bool:
        """Apply system-wide isolation."""
        # Implementation would enable read-only mode or similar
        logger.critical(f"System isolation applied: {component}")
        return True
    
    async def _send_admin_alert(self, pattern: FailurePattern, error: MyPoolrException) -> Dict[str, Any]:
        """Send administrator alert for detected pattern."""
        # Check cooldown
        cooldown_key = f"{pattern.name}_{error.error_code}"
        if cooldown_key in self.alert_cooldown:
            last_alert = self.alert_cooldown[cooldown_key]
            if datetime.utcnow() - last_alert < timedelta(minutes=self.cooldown_minutes):
                return {"sent": False, "reason": "cooldown_active"}
        
        # Create alert
        alert_id = f"alert_{datetime.utcnow().timestamp()}"
        alert = AdminAlert(
            id=alert_id,
            timestamp=datetime.utcnow(),
            severity=error.severity,
            title=f"Failure Pattern Detected: {pattern.name}",
            message=f"{pattern.description}\n\nError: {error.message}\nComponent: {self._determine_component_from_error(error)}",
            component=self._determine_component_from_error(error),
            error_details={
                "error_code": error.error_code,
                "category": error.category.value,
                "pattern_name": pattern.name,
                "isolation_level": pattern.isolation_level.value
            },
            channels=self._determine_alert_channels(error.severity)
        )
        
        try:
            # Send alert through configured channels
            sent_channels = await self._deliver_alert(alert)
            
            if sent_channels:
                self.admin_alerts.append(alert)
                self.alert_cooldown[cooldown_key] = datetime.utcnow()
                
                logger.info(f"Admin alert sent: {alert_id} via {sent_channels}")
                
                return {
                    "sent": True,
                    "alert_id": alert_id,
                    "channels": sent_channels
                }
            else:
                return {"sent": False, "reason": "no_channels_available"}
                
        except Exception as e:
            logger.error(f"Failed to send admin alert: {str(e)}")
            return {"sent": False, "error": str(e)}
    
    def _determine_component_from_error(self, error: MyPoolrException) -> str:
        """Determine the component from error context."""
        if error.context and error.context.endpoint:
            return error.context.endpoint.split('/')[1] if '/' in error.context.endpoint else "unknown"
        
        # Map error categories to components
        category_map = {
            ErrorCategory.DATABASE: "database",
            ErrorCategory.EXTERNAL_SERVICE: "external_services",
            ErrorCategory.SECURITY: "security",
            ErrorCategory.CONCURRENCY: "concurrency_manager",
            ErrorCategory.DATA_CONSISTENCY: "data_consistency",
            ErrorCategory.SYSTEM: "system"
        }
        
        return category_map.get(error.category, "unknown")
    
    def _determine_alert_channels(self, severity: ErrorSeverity) -> List[AlertChannel]:
        """Determine alert channels based on severity."""
        if severity == ErrorSeverity.CRITICAL:
            return [AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS]
        elif severity == ErrorSeverity.HIGH:
            return [AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.SLACK]
        elif severity == ErrorSeverity.MEDIUM:
            return [AlertChannel.LOG, AlertChannel.EMAIL]
        else:
            return [AlertChannel.LOG]
    
    async def _deliver_alert(self, alert: AdminAlert) -> List[str]:
        """Deliver alert through configured channels."""
        delivered_channels = []
        
        for channel in alert.channels:
            try:
                if channel == AlertChannel.LOG:
                    logger.critical(f"ADMIN ALERT: {alert.title} - {alert.message}")
                    delivered_channels.append("log")
                
                elif channel == AlertChannel.EMAIL:
                    # Implementation would send email
                    logger.info(f"Email alert would be sent: {alert.title}")
                    delivered_channels.append("email")
                
                elif channel == AlertChannel.SLACK:
                    # Implementation would send Slack message
                    logger.info(f"Slack alert would be sent: {alert.title}")
                    delivered_channels.append("slack")
                
                elif channel == AlertChannel.WEBHOOK:
                    # Implementation would call webhook
                    logger.info(f"Webhook alert would be sent: {alert.title}")
                    delivered_channels.append("webhook")
                
                elif channel == AlertChannel.SMS:
                    # Implementation would send SMS
                    logger.info(f"SMS alert would be sent: {alert.title}")
                    delivered_channels.append("sms")
                    
            except Exception as e:
                logger.error(f"Failed to deliver alert via {channel.value}: {str(e)}")
        
        return delivered_channels
    
    def _is_component_isolated(self, component: str) -> bool:
        """Check if a component is currently isolated."""
        return component in self.isolated_components
    
    async def remove_isolation(self, component: str, reason: str = "manual") -> Dict[str, Any]:
        """Remove isolation from a component."""
        if component not in self.isolated_components:
            return {"success": False, "reason": "component_not_isolated"}
        
        try:
            # Remove isolation measures
            success = await self._remove_isolation_measures(component)
            
            if success:
                isolation_action = self.isolated_components.pop(component)
                
                logger.info(f"Isolation removed from component: {component} (Reason: {reason})")
                
                # Log isolation removal
                await audit_logger.log_system_action(
                    action="isolation_removed",
                    component="failure_isolation",
                    details={
                        "component": component,
                        "reason": reason,
                        "isolation_duration_minutes": int(
                            (datetime.utcnow() - isolation_action.timestamp).total_seconds() / 60
                        )
                    }
                )
                
                return {"success": True, "component": component}
            else:
                return {"success": False, "reason": "failed_to_remove_measures"}
                
        except Exception as e:
            logger.error(f"Failed to remove isolation: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _remove_isolation_measures(self, component: str) -> bool:
        """Remove the actual isolation measures."""
        # Implementation would re-enable functionality
        logger.info(f"Isolation measures removed for: {component}")
        return True
    
    def get_isolation_status(self) -> Dict[str, Any]:
        """Get current isolation status."""
        return {
            "isolated_components": {
                component: {
                    "isolation_level": action.isolation_level.value,
                    "reason": action.reason,
                    "timestamp": action.timestamp.isoformat(),
                    "auto_triggered": action.auto_triggered
                }
                for component, action in self.isolated_components.items()
            },
            "recent_failures": len(self.failure_history),
            "recent_alerts": len([
                alert for alert in self.admin_alerts
                if alert.timestamp > datetime.utcnow() - timedelta(hours=24)
            ])
        }


# Global failure isolation manager
failure_isolation_manager = FailureIsolationManager()