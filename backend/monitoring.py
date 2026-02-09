"""Enhanced monitoring system for comprehensive system observability."""

import asyncio
import logging
import psutil
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from database import db_manager
from audit_logger import audit_logger
from system_recovery import recovery_manager
from data_consistency import consistency_checker

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Represents a system metric."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    unit: str = ""


@dataclass
class Alert:
    """Represents a system alert."""
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float
    labels: Dict[str, str]


class SystemMonitor:
    """Comprehensive system monitoring and alerting."""
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = {}
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.collection_interval = 30  # seconds
        self.metric_retention_hours = 24
        
        # Initialize alert rules
        self._setup_default_alert_rules()
    
    async def start_monitoring(self):
        """Start the monitoring system."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        await audit_logger.log_system_action(
            action="monitoring_started",
            component="system_monitor"
        )
        
        logger.info("System monitoring started")
    
    async def stop_monitoring(self):
        """Stop the monitoring system."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        await audit_logger.log_system_action(
            action="monitoring_stopped",
            component="system_monitor"
        )
        
        logger.info("System monitoring stopped")
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect all system metrics."""
        timestamp = datetime.utcnow()
        collected_metrics = {}
        
        try:
            # System resource metrics
            system_metrics = await self._collect_system_metrics(timestamp)
            collected_metrics.update(system_metrics)
            
            # Database metrics
            db_metrics = await self._collect_database_metrics(timestamp)
            collected_metrics.update(db_metrics)
            
            # Application metrics
            app_metrics = await self._collect_application_metrics(timestamp)
            collected_metrics.update(app_metrics)
            
            # Business metrics
            business_metrics = await self._collect_business_metrics(timestamp)
            collected_metrics.update(business_metrics)
            
            # Store metrics
            for metric_name, metric_value in collected_metrics.items():
                await self._store_metric(metric_name, metric_value, timestamp)
            
            # Check alert rules
            await self._check_alert_rules(collected_metrics, timestamp)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            await audit_logger.log_error_event(e)
        
        return collected_metrics
    
    async def _collect_system_metrics(self, timestamp: datetime) -> Dict[str, float]:
        """Collect system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # Network metrics (if available)
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            return {
                "system_cpu_percent": cpu_percent,
                "system_cpu_count": cpu_count,
                "system_memory_percent": memory_percent,
                "system_memory_available_gb": memory_available_gb,
                "system_disk_percent": disk_percent,
                "system_disk_free_gb": disk_free_gb,
                "system_network_bytes_sent": network_bytes_sent,
                "system_network_bytes_recv": network_bytes_recv
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}
    
    async def _collect_database_metrics(self, timestamp: datetime) -> Dict[str, float]:
        """Collect database performance metrics."""
        try:
            metrics = {}
            
            # Connection test timing
            start_time = time.time()
            db_healthy = await db_manager.health_check()
            connection_time_ms = (time.time() - start_time) * 1000
            
            metrics["db_connection_time_ms"] = connection_time_ms
            metrics["db_connection_healthy"] = 1.0 if db_healthy else 0.0
            
            # Record counts
            try:
                mypoolr_result = db_manager.service_client.table("mypoolr").select("id", count="exact").execute()
                metrics["db_mypoolr_count"] = float(mypoolr_result.count or 0)
                
                member_result = db_manager.service_client.table("member").select("id", count="exact").execute()
                metrics["db_member_count"] = float(member_result.count or 0)
                
                transaction_result = db_manager.service_client.table("transaction").select("id", count="exact").execute()
                metrics["db_transaction_count"] = float(transaction_result.count or 0)
                
                # Pending transactions (not both_confirmed)
                pending_result = db_manager.service_client.table("transaction").select("id", count="exact").neq("confirmation_status", "both_confirmed").execute()
                metrics["db_pending_transactions"] = float(pending_result.count or 0)
                
            except Exception as e:
                logger.warning(f"Error collecting database record counts: {str(e)}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {str(e)}")
            return {}
    
    async def _collect_application_metrics(self, timestamp: datetime) -> Dict[str, float]:
        """Collect application-specific metrics."""
        try:
            metrics = {}
            
            # Recovery system status
            recovery_state_map = {
                "healthy": 1.0,
                "degraded": 0.5,
                "recovering": 0.3,
                "failed": 0.0
            }
            metrics["app_recovery_state"] = recovery_state_map.get(recovery_manager.recovery_state.value, 0.0)
            
            # Component status
            component_healthy_count = sum(
                1 for status in recovery_manager.component_status.values()
                if status.value == "operational"
            )
            total_components = len(recovery_manager.component_status)
            metrics["app_component_health_ratio"] = component_healthy_count / total_components if total_components > 0 else 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {str(e)}")
            return {}
    
    async def _collect_business_metrics(self, timestamp: datetime) -> Dict[str, float]:
        """Collect business logic metrics."""
        try:
            metrics = {}
            
            # Active MyPoolr groups
            try:
                active_result = db_manager.service_client.table("mypoolr").select("id", count="exact").eq("status", "active").execute()
                metrics["business_active_mypoolrs"] = float(active_result.count or 0)
            except:
                metrics["business_active_mypoolrs"] = 0.0
            
            # Recent transactions (last 24 hours)
            try:
                yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
                recent_transactions = db_manager.service_client.table("transaction").select("id", count="exact").gte("created_at", yesterday).execute()
                metrics["business_recent_transactions"] = float(recent_transactions.count or 0)
            except:
                metrics["business_recent_transactions"] = 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting business metrics: {str(e)}")
            return {}
    
    async def _store_metric(self, name: str, value: float, timestamp: datetime):
        """Store a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        metric = Metric(
            name=name,
            type=MetricType.GAUGE,  # Default to gauge
            value=value,
            timestamp=timestamp,
            labels={},
            unit=""
        )
        
        self.metrics[name].append(metric)
        
        # Clean up old metrics
        cutoff_time = timestamp - timedelta(hours=self.metric_retention_hours)
        self.metrics[name] = [
            m for m in self.metrics[name]
            if m.timestamp > cutoff_time
        ]
    
    def _setup_default_alert_rules(self):
        """Set up default alert rules."""
        self.alert_rules = {
            "system_cpu_percent": {
                "threshold": 80.0,
                "operator": ">",
                "severity": AlertSeverity.WARNING,
                "message": "High CPU usage detected"
            },
            "system_memory_percent": {
                "threshold": 85.0,
                "operator": ">",
                "severity": AlertSeverity.WARNING,
                "message": "High memory usage detected"
            },
            "system_disk_percent": {
                "threshold": 90.0,
                "operator": ">",
                "severity": AlertSeverity.CRITICAL,
                "message": "Low disk space detected"
            },
            "db_connection_time_ms": {
                "threshold": 5000.0,
                "operator": ">",
                "severity": AlertSeverity.WARNING,
                "message": "Slow database connection detected"
            },
            "db_connection_healthy": {
                "threshold": 1.0,
                "operator": "<",
                "severity": AlertSeverity.CRITICAL,
                "message": "Database connection failed"
            },
            "app_recovery_state": {
                "threshold": 0.5,
                "operator": "<",
                "severity": AlertSeverity.CRITICAL,
                "message": "System recovery state is degraded"
            }
        }
    
    async def _check_alert_rules(self, metrics: Dict[str, float], timestamp: datetime):
        """Check metrics against alert rules."""
        for metric_name, rule in self.alert_rules.items():
            if metric_name not in metrics:
                continue
            
            current_value = metrics[metric_name]
            threshold = rule["threshold"]
            operator = rule["operator"]
            
            # Check if alert condition is met
            alert_triggered = False
            if operator == ">" and current_value > threshold:
                alert_triggered = True
            elif operator == "<" and current_value < threshold:
                alert_triggered = True
            elif operator == "==" and current_value == threshold:
                alert_triggered = True
            
            if alert_triggered:
                alert = Alert(
                    name=f"{metric_name}_alert",
                    severity=rule["severity"],
                    message=rule["message"],
                    timestamp=timestamp,
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold=threshold,
                    labels={}
                )
                
                await self._handle_alert(alert)
    
    async def _handle_alert(self, alert: Alert):
        """Handle a triggered alert."""
        # Check if this is a duplicate alert (same alert in last 5 minutes)
        recent_alerts = [
            a for a in self.alerts
            if a.name == alert.name and a.timestamp > alert.timestamp - timedelta(minutes=5)
        ]
        
        if recent_alerts:
            return  # Skip duplicate alert
        
        # Store alert
        self.alerts.append(alert)
        
        # Log alert
        logger.warning(f"ALERT: {alert.message} - {alert.metric_name}={alert.current_value} (threshold: {alert.threshold})")
        
        # Send to audit logger
        await audit_logger.log_system_action(
            action="alert_triggered",
            component="monitoring",
            details={
                "alert_name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold
            },
            outcome="warning"
        )
        
        # For critical alerts, trigger recovery if appropriate
        if alert.severity == AlertSeverity.CRITICAL:
            await self._handle_critical_alert(alert)
    
    async def _handle_critical_alert(self, alert: Alert):
        """Handle critical alerts with potential recovery actions."""
        logger.critical(f"CRITICAL ALERT: {alert.message}")
        
        # Trigger system recovery for certain critical alerts
        recovery_triggers = [
            "db_connection_healthy",
            "app_recovery_state"
        ]
        
        if alert.metric_name in recovery_triggers:
            logger.info("Triggering automatic recovery due to critical alert")
            try:
                await recovery_manager.detect_and_recover_failures()
            except Exception as e:
                logger.error(f"Automatic recovery failed: {str(e)}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.collection_interval)
    
    def get_metric_history(self, metric_name: str, hours: int = 1) -> List[Metric]:
        """Get metric history for the specified time period."""
        if metric_name not in self.metrics:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            metric for metric in self.metrics[metric_name]
            if metric.timestamp > cutoff_time
        ]
    
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts
            if alert.timestamp > cutoff_time
        ]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        # Get latest metrics
        latest_metrics = {}
        for metric_name, metric_list in self.metrics.items():
            if metric_list:
                latest_metrics[metric_name] = metric_list[-1].value
        
        # Get recent alerts
        recent_alerts = self.get_recent_alerts(hours=1)
        
        # Determine overall status
        critical_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL]
        warning_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.WARNING]
        
        if critical_alerts:
            overall_status = "critical"
        elif warning_alerts:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": latest_metrics,
            "recent_alerts": len(recent_alerts),
            "critical_alerts": len(critical_alerts),
            "warning_alerts": len(warning_alerts),
            "monitoring_active": self.monitoring_active
        }


# Global monitor instance
system_monitor = SystemMonitor()

# Task monitoring functions for Celery integration
def monitor_task_execution(task_name: str, task_id: str, status: str, **kwargs):
    """Monitor Celery task execution for metrics and alerting."""
    try:
        # Log task execution
        logger.info(f"Task {task_name} [{task_id}] status: {status}")
        
        # Store task metrics
        timestamp = datetime.utcnow()
        
        # Update task counters
        if not hasattr(system_monitor, 'task_counters'):
            system_monitor.task_counters = {}
        
        counter_key = f"task_{status}_count"
        if counter_key not in system_monitor.task_counters:
            system_monitor.task_counters[counter_key] = 0
        system_monitor.task_counters[counter_key] += 1
        
        # Store task-specific metrics
        task_metric_name = f"task_{task_name.replace('.', '_')}_status"
        status_value = {
            "SUCCESS": 1.0,
            "FAILURE": 0.0,
            "RETRY": 0.5,
            "PENDING": 0.3,
            "STARTED": 0.7
        }.get(status, 0.0)
        
        asyncio.create_task(system_monitor._store_metric(
            task_metric_name, 
            status_value, 
            timestamp
        ))
        
        # Log to audit system
        asyncio.create_task(audit_logger.log_system_action(
            action="task_execution",
            component="celery",
            details={
                "task_name": task_name,
                "task_id": task_id,
                "status": status,
                **kwargs
            }
        ))
        
    except Exception as e:
        logger.error(f"Error monitoring task execution: {e}")

def task_monitor(func):
    """Decorator to monitor Celery task execution."""
    def wrapper(self, *args, **kwargs):
        task_name = func.__name__
        task_id = getattr(self.request, 'id', 'unknown')
        
        try:
            # Log task start
            monitor_task_execution(task_name, task_id, "STARTED")
            
            # Execute task
            result = func(self, *args, **kwargs)
            
            # Log task success
            monitor_task_execution(task_name, task_id, "SUCCESS")
            
            return result
            
        except Exception as exc:
            # Log task failure
            monitor_task_execution(task_name, task_id, "FAILURE", error=str(exc))
            raise exc
    
    return wrapper

def get_task_metrics() -> Dict[str, Any]:
    """Get task execution metrics."""
    try:
        if not hasattr(system_monitor, 'task_counters'):
            return {}
        
        return dict(system_monitor.task_counters)
        
    except Exception as e:
        logger.error(f"Error getting task metrics: {e}")
        return {}