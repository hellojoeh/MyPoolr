"""Comprehensive audit logging and monitoring system."""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from database import db_manager
from exceptions import ErrorContext, MyPoolrException

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    USER_ACTION = "user_action"
    SYSTEM_ACTION = "system_action"
    DATA_CHANGE = "data_change"
    SECURITY_EVENT = "security_event"
    ERROR_EVENT = "error_event"
    RECOVERY_EVENT = "recovery_event"
    PERFORMANCE_EVENT = "performance_event"
    COMPLIANCE_EVENT = "compliance_event"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents an audit event."""
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    outcome: str = "success"
    error_code: Optional[str] = None
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary."""
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat()
        }


class AuditLogger:
    """Comprehensive audit logging system."""
    
    def __init__(self):
        self.db = db_manager
        self.event_buffer: List[AuditEvent] = []
        self.buffer_size = 100
        self.flush_interval = 30  # seconds
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the audit logger."""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("Audit logger started")
    
    async def stop(self):
        """Stop the audit logger."""
        if not self._running:
            return
        
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        await self.flush_events()
        logger.info("Audit logger stopped")
    
    async def log_user_action(
        self,
        action: str,
        user_id: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        outcome: str = "success",
        error_code: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """Log a user action."""
        event = AuditEvent(
            event_type=AuditEventType.USER_ACTION,
            severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.WARNING,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=request_context.get("session_id") if request_context else None,
            request_id=request_context.get("request_id") if request_context else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=request_context.get("ip_address") if request_context else None,
            user_agent=request_context.get("user_agent") if request_context else None,
            outcome=outcome,
            error_code=error_code,
            duration_ms=duration_ms
        )
        
        await self._add_event(event)
    
    async def log_system_action(
        self,
        action: str,
        component: str,
        details: Optional[Dict[str, Any]] = None,
        outcome: str = "success",
        error_code: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """Log a system action."""
        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_ACTION,
            severity=AuditSeverity.INFO if outcome == "success" else AuditSeverity.ERROR,
            timestamp=datetime.utcnow(),
            user_id=None,
            session_id=None,
            request_id=None,
            action=action,
            resource_type="system",
            resource_id=component,
            details=details or {},
            outcome=outcome,
            error_code=error_code,
            duration_ms=duration_ms
        )
        
        await self._add_event(event)
    
    async def log_data_change(
        self,
        action: str,
        table_name: str,
        record_id: str,
        user_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None
    ):
        """Log a data change event."""
        details = {}
        if old_values:
            details["old_values"] = old_values
        if new_values:
            details["new_values"] = new_values
        
        event = AuditEvent(
            event_type=AuditEventType.DATA_CHANGE,
            severity=AuditSeverity.INFO,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=request_context.get("session_id") if request_context else None,
            request_id=request_context.get("request_id") if request_context else None,
            action=action,
            resource_type=table_name,
            resource_id=record_id,
            details=details,
            ip_address=request_context.get("ip_address") if request_context else None,
            user_agent=request_context.get("user_agent") if request_context else None
        )
        
        await self._add_event(event)
    
    async def log_security_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.WARNING
    ):
        """Log a security event."""
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_EVENT,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=request_context.get("session_id") if request_context else None,
            request_id=request_context.get("request_id") if request_context else None,
            action=action,
            resource_type="security",
            resource_id=None,
            details=details or {},
            ip_address=request_context.get("ip_address") if request_context else None,
            user_agent=request_context.get("user_agent") if request_context else None
        )
        
        await self._add_event(event)
    
    async def log_error_event(
        self,
        error: Union[Exception, MyPoolrException],
        context: Optional[ErrorContext] = None,
        user_id: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ):
        """Log an error event."""
        details = {
            "error_message": str(error),
            "error_type": type(error).__name__
        }
        
        if isinstance(error, MyPoolrException):
            details.update({
                "error_code": error.error_code,
                "category": error.category.value,
                "recoverable": error.recoverable
            })
            if error.context:
                details["error_context"] = error.context.dict()
        
        if context:
            details["context"] = context.dict()
        
        event = AuditEvent(
            event_type=AuditEventType.ERROR_EVENT,
            severity=AuditSeverity.ERROR if not isinstance(error, MyPoolrException) 
                     else AuditSeverity.CRITICAL if error.severity.value == "critical" 
                     else AuditSeverity.ERROR,
            timestamp=datetime.utcnow(),
            user_id=user_id or (context.user_id if context else None),
            session_id=request_context.get("session_id") if request_context else None,
            request_id=request_context.get("request_id") if request_context else None,
            action="error_occurred",
            resource_type="error",
            resource_id=None,
            details=details,
            ip_address=request_context.get("ip_address") if request_context else None,
            user_agent=request_context.get("user_agent") if request_context else None,
            outcome="error",
            error_code=error.error_code if isinstance(error, MyPoolrException) else None
        )
        
        await self._add_event(event)
    
    async def log_recovery_event(
        self,
        action: str,
        component: str,
        details: Optional[Dict[str, Any]] = None,
        outcome: str = "success"
    ):
        """Log a recovery event."""
        event = AuditEvent(
            event_type=AuditEventType.RECOVERY_EVENT,
            severity=AuditSeverity.WARNING if outcome == "success" else AuditSeverity.ERROR,
            timestamp=datetime.utcnow(),
            user_id=None,
            session_id=None,
            request_id=None,
            action=action,
            resource_type="recovery",
            resource_id=component,
            details=details or {},
            outcome=outcome
        )
        
        await self._add_event(event)
    
    async def log_performance_event(
        self,
        action: str,
        duration_ms: int,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        threshold_ms: int = 1000
    ):
        """Log a performance event."""
        severity = AuditSeverity.WARNING if duration_ms > threshold_ms else AuditSeverity.INFO
        
        event = AuditEvent(
            event_type=AuditEventType.PERFORMANCE_EVENT,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=None,
            session_id=None,
            request_id=None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            duration_ms=duration_ms
        )
        
        await self._add_event(event)
    
    async def log_compliance_event(
        self,
        action: str,
        regulation: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None
    ):
        """Log a compliance-related event."""
        compliance_details = {
            "regulation": regulation,
            **(details or {})
        }
        
        event = AuditEvent(
            event_type=AuditEventType.COMPLIANCE_EVENT,
            severity=AuditSeverity.INFO,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=request_context.get("session_id") if request_context else None,
            request_id=request_context.get("request_id") if request_context else None,
            action=action,
            resource_type="compliance",
            resource_id=regulation,
            details=compliance_details,
            ip_address=request_context.get("ip_address") if request_context else None,
            user_agent=request_context.get("user_agent") if request_context else None
        )
        
        await self._add_event(event)
    
    @asynccontextmanager
    async def audit_context(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ):
        """Context manager for auditing operations with timing."""
        start_time = datetime.utcnow()
        outcome = "success"
        error_code = None
        
        try:
            yield
        except Exception as e:
            outcome = "error"
            error_code = getattr(e, 'error_code', type(e).__name__)
            raise
        finally:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            await self.log_user_action(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                request_context=request_context,
                outcome=outcome,
                error_code=error_code,
                duration_ms=duration_ms
            )
    
    async def query_audit_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query audit events with filters."""
        # This would query from the audit log storage
        # For now, return empty list as storage is not implemented
        return []
    
    async def generate_audit_report(
        self,
        start_time: datetime,
        end_time: datetime,
        report_type: str = "summary"
    ) -> Dict[str, Any]:
        """Generate audit report for a time period."""
        events = await self.query_audit_events(start_time=start_time, end_time=end_time)
        
        report = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_events": len(events),
            "event_types": {},
            "severity_breakdown": {},
            "user_activity": {},
            "error_summary": {},
            "performance_metrics": {}
        }
        
        # Analyze events
        for event in events:
            # Count by event type
            event_type = event.get("event_type", "unknown")
            report["event_types"][event_type] = report["event_types"].get(event_type, 0) + 1
            
            # Count by severity
            severity = event.get("severity", "unknown")
            report["severity_breakdown"][severity] = report["severity_breakdown"].get(severity, 0) + 1
            
            # User activity
            user_id = event.get("user_id")
            if user_id:
                if user_id not in report["user_activity"]:
                    report["user_activity"][user_id] = {"actions": 0, "errors": 0}
                report["user_activity"][user_id]["actions"] += 1
                if event.get("outcome") == "error":
                    report["user_activity"][user_id]["errors"] += 1
        
        return report
    
    async def _add_event(self, event: AuditEvent):
        """Add event to buffer."""
        self.event_buffer.append(event)
        
        # Flush if buffer is full
        if len(self.event_buffer) >= self.buffer_size:
            await self.flush_events()
    
    async def flush_events(self):
        """Flush buffered events to storage."""
        if not self.event_buffer:
            return
        
        try:
            # Convert events to dictionaries
            events_data = [event.to_dict() for event in self.event_buffer]
            
            # Store in database (would need audit_log table)
            # For now, just log to file/console
            for event_data in events_data:
                logger.info(f"AUDIT: {json.dumps(event_data)}")
            
            # Clear buffer
            self.event_buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush audit events: {str(e)}")
    
    async def _periodic_flush(self):
        """Periodically flush events."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {str(e)}")


# Global audit logger instance
audit_logger = AuditLogger()