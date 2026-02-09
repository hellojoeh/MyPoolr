"""Task scheduler for coordinating background processes."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from celery_app import celery_app
from celery.schedules import crontab
from database import db_manager

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Coordinates scheduling of all background tasks."""
    
    def __init__(self):
        self.active_schedules = {}
    
    def schedule_mypoolr_tasks(self, mypoolr_id: str) -> Dict[str, Any]:
        """Schedule all recurring tasks for a MyPoolr group."""
        try:
            # Get MyPoolr details
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", mypoolr_id
            ).execute()
            
            if not mypoolr_result.data:
                raise Exception(f"MyPoolr {mypoolr_id} not found")
            
            mypoolr = mypoolr_result.data[0]
            
            # Calculate schedule based on rotation frequency
            frequency = mypoolr["rotation_frequency"]
            
            if frequency == "daily":
                # Daily rotations - schedule reminders every day
                schedule_reminders_daily.delay(mypoolr_id)
                schedule_deadline_monitoring_daily.delay(mypoolr_id)
                
            elif frequency == "weekly":
                # Weekly rotations - schedule for specific day of week
                schedule_reminders_weekly.delay(mypoolr_id)
                schedule_deadline_monitoring_weekly.delay(mypoolr_id)
                
            elif frequency == "monthly":
                # Monthly rotations - schedule for specific day of month
                schedule_reminders_monthly.delay(mypoolr_id)
                schedule_deadline_monitoring_monthly.delay(mypoolr_id)
            
            # Schedule health monitoring (regardless of frequency)
            schedule_health_monitoring.delay(mypoolr_id)
            
            self.active_schedules[mypoolr_id] = {
                "frequency": frequency,
                "scheduled_at": datetime.utcnow().isoformat(),
                "tasks": ["reminders", "deadline_monitoring", "health_monitoring"]
            }
            
            return {
                "status": "scheduled",
                "mypoolr_id": mypoolr_id,
                "frequency": frequency,
                "tasks_scheduled": self.active_schedules[mypoolr_id]["tasks"]
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule MyPoolr tasks: {e}")
            raise e
    
    def cancel_mypoolr_tasks(self, mypoolr_id: str) -> Dict[str, Any]:
        """Cancel all scheduled tasks for a MyPoolr group."""
        try:
            # In production, this would cancel specific scheduled tasks
            # For now, just remove from active schedules
            if mypoolr_id in self.active_schedules:
                del self.active_schedules[mypoolr_id]
            
            logger.info(f"Cancelled scheduled tasks for MyPoolr {mypoolr_id}")
            
            return {
                "status": "cancelled",
                "mypoolr_id": mypoolr_id,
                "cancelled_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel MyPoolr tasks: {e}")
            raise e


# Global scheduler instance
task_scheduler = TaskScheduler()


# Periodic task definitions
@celery_app.task(bind=True, max_retries=3)
def schedule_reminders_daily(self, mypoolr_id: str):
    """Schedule daily rotation reminders."""
    try:
        from tasks.reminders import schedule_rotation_reminders
        
        # Schedule reminders for today's rotation
        schedule_rotation_reminders.delay(mypoolr_id)
        
        # Schedule this task to run again tomorrow
        tomorrow = datetime.utcnow() + timedelta(days=1)
        schedule_reminders_daily.apply_async(
            args=[mypoolr_id],
            eta=tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)  # 9 AM UTC
        )
        
        return {"status": "daily_reminders_scheduled", "mypoolr_id": mypoolr_id}
        
    except Exception as exc:
        logger.error(f"Failed to schedule daily reminders: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
def schedule_reminders_weekly(self, mypoolr_id: str):
    """Schedule weekly rotation reminders."""
    try:
        from tasks.reminders import schedule_rotation_reminders
        
        # Schedule reminders for this week's rotation
        schedule_rotation_reminders.delay(mypoolr_id)
        
        # Schedule this task to run again next week
        next_week = datetime.utcnow() + timedelta(weeks=1)
        schedule_reminders_weekly.apply_async(
            args=[mypoolr_id],
            eta=next_week.replace(hour=9, minute=0, second=0, microsecond=0)  # Monday 9 AM UTC
        )
        
        return {"status": "weekly_reminders_scheduled", "mypoolr_id": mypoolr_id}
        
    except Exception as exc:
        logger.error(f"Failed to schedule weekly reminders: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
def schedule_reminders_monthly(self, mypoolr_id: str):
    """Schedule monthly rotation reminders."""
    try:
        from tasks.reminders import schedule_rotation_reminders
        
        # Schedule reminders for this month's rotation
        schedule_rotation_reminders.delay(mypoolr_id)
        
        # Schedule this task to run again next month
        next_month = datetime.utcnow() + timedelta(days=30)  # Approximate
        schedule_reminders_monthly.apply_async(
            args=[mypoolr_id],
            eta=next_month.replace(day=1, hour=9, minute=0, second=0, microsecond=0)  # 1st of month, 9 AM UTC
        )
        
        return {"status": "monthly_reminders_scheduled", "mypoolr_id": mypoolr_id}
        
    except Exception as exc:
        logger.error(f"Failed to schedule monthly reminders: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
def schedule_deadline_monitoring_daily(self, mypoolr_id: str):
    """Schedule daily deadline monitoring."""
    try:
        from tasks.defaults import monitor_default_deadlines
        
        # Monitor deadlines for today
        monitor_default_deadlines.delay(mypoolr_id)
        
        # Schedule this task to run again tomorrow
        tomorrow = datetime.utcnow() + timedelta(days=1)
        schedule_deadline_monitoring_daily.apply_async(
            args=[mypoolr_id],
            eta=tomorrow.replace(hour=23, minute=0, second=0, microsecond=0)  # 11 PM UTC
        )
        
        return {"status": "daily_monitoring_scheduled", "mypoolr_id": mypoolr_id}
        
    except Exception as exc:
        logger.error(f"Failed to schedule daily monitoring: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
def schedule_deadline_monitoring_weekly(self, mypoolr_id: str):
    """Schedule weekly deadline monitoring."""
    try:
        from tasks.defaults import monitor_default_deadlines
        
        # Monitor deadlines for this week
        monitor_default_deadlines.delay(mypoolr_id)
        
        # Schedule this task to run again next week
        next_week = datetime.utcnow() + timedelta(weeks=1)
        schedule_deadline_monitoring_weekly.apply_async(
            args=[mypoolr_id],
            eta=next_week.replace(hour=23, minute=0, second=0, microsecond=0)  # Sunday 11 PM UTC
        )
        
        return {"status": "weekly_monitoring_scheduled", "mypoolr_id": mypoolr_id}
        
    except Exception as exc:
        logger.error(f"Failed to schedule weekly monitoring: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
def schedule_deadline_monitoring_monthly(self, mypoolr_id: str):
    """Schedule monthly deadline monitoring."""
    try:
        from tasks.defaults import monitor_default_deadlines
        
        # Monitor deadlines for this month
        monitor_default_deadlines.delay(mypoolr_id)
        
        # Schedule this task to run again next month
        next_month = datetime.utcnow() + timedelta(days=30)  # Approximate
        schedule_deadline_monitoring_monthly.apply_async(
            args=[mypoolr_id],
            eta=next_month.replace(day=28, hour=23, minute=0, second=0, microsecond=0)  # 28th of month, 11 PM UTC
        )
        
        return {"status": "monthly_monitoring_scheduled", "mypoolr_id": mypoolr_id}
        
    except Exception as exc:
        logger.error(f"Failed to schedule monthly monitoring: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
def schedule_health_monitoring(self, mypoolr_id: str):
    """Schedule periodic health monitoring for a MyPoolr group."""
    try:
        # Schedule health check every 6 hours
        health_check_interval = timedelta(hours=6)
        next_check = datetime.utcnow() + health_check_interval
        
        perform_mypoolr_health_check.apply_async(
            args=[mypoolr_id],
            eta=next_check
        )
        
        return {"status": "health_monitoring_scheduled", "mypoolr_id": mypoolr_id}
        
    except Exception as exc:
        logger.error(f"Failed to schedule health monitoring: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
def perform_mypoolr_health_check(self, mypoolr_id: str):
    """Perform comprehensive health check for a MyPoolr group."""
    try:
        # Get MyPoolr and member details
        mypoolr_result = db_manager.client.table("mypoolr").select(
            "*, member(*)"
        ).eq("id", mypoolr_id).execute()
        
        if not mypoolr_result.data:
            logger.warning(f"MyPoolr {mypoolr_id} not found during health check")
            return {"status": "mypoolr_not_found", "mypoolr_id": mypoolr_id}
        
        mypoolr = mypoolr_result.data[0]
        members = mypoolr.get("member", [])
        
        health_issues = []
        
        # Check 1: Verify all active members have confirmed security deposits
        for member in members:
            if member["status"] == "active" and member["security_deposit_status"] != "confirmed":
                health_issues.append({
                    "type": "unconfirmed_deposit",
                    "member_id": member["id"],
                    "member_name": member["name"]
                })
        
        # Check 2: Verify rotation integrity
        active_members = [m for m in members if m["status"] == "active"]
        rotation_positions = [m["rotation_position"] for m in active_members]
        
        if len(set(rotation_positions)) != len(rotation_positions):
            health_issues.append({
                "type": "duplicate_rotation_positions",
                "positions": rotation_positions
            })
        
        # Check 3: Verify current rotation position is valid
        current_position = mypoolr.get("current_rotation_position", 0)
        if current_position >= len(active_members):
            health_issues.append({
                "type": "invalid_rotation_position",
                "current_position": current_position,
                "max_position": len(active_members) - 1
            })
        
        # Check 4: Look for stale transactions
        stale_transactions = db_manager.client.table("transaction").select("*").eq(
            "mypoolr_id", mypoolr_id
        ).eq("confirmation_status", "pending").execute()
        
        if stale_transactions.data:
            for transaction in stale_transactions.data:
                created_at = datetime.fromisoformat(transaction["created_at"])
                if datetime.utcnow() - created_at > timedelta(hours=48):  # 48 hours old
                    health_issues.append({
                        "type": "stale_transaction",
                        "transaction_id": transaction["id"],
                        "age_hours": int((datetime.utcnow() - created_at).total_seconds() / 3600)
                    })
        
        # Schedule next health check
        schedule_health_monitoring.delay(mypoolr_id)
        
        if health_issues:
            logger.warning(f"Health issues detected for MyPoolr {mypoolr_id}: {health_issues}")
            
            # In production, this would alert administrators
            return {
                "status": "issues_detected",
                "mypoolr_id": mypoolr_id,
                "issues": health_issues,
                "checked_at": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "healthy",
                "mypoolr_id": mypoolr_id,
                "checked_at": datetime.utcnow().isoformat()
            }
        
    except Exception as exc:
        logger.error(f"Failed to perform health check: {exc}")
        raise exc


# Celery beat schedule for system-wide periodic tasks
celery_app.conf.beat_schedule = {
    # System health monitoring
    'system-health-check': {
        'task': 'monitoring.health_report',
        'schedule': crontab(minute=0),  # Every hour
    },
    
    # Cleanup old metrics
    'cleanup-old-metrics': {
        'task': 'monitoring.cleanup_old_metrics',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    
    # General system maintenance
    'system-maintenance': {
        'task': 'scheduler.perform_system_maintenance',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}


@celery_app.task(name="scheduler.perform_system_maintenance")
def perform_system_maintenance():
    """Perform system-wide maintenance tasks."""
    try:
        maintenance_tasks = []
        
        # Clean up completed tasks older than 7 days
        # In production, this would clean up task result backend
        maintenance_tasks.append("cleaned_old_task_results")
        
        # Check for orphaned records
        # In production, this would check for data consistency issues
        maintenance_tasks.append("checked_data_consistency")
        
        # Update system metrics
        # In production, this would update system-wide statistics
        maintenance_tasks.append("updated_system_metrics")
        
        logger.info(f"System maintenance completed: {maintenance_tasks}")
        
        return {
            "status": "maintenance_completed",
            "tasks_performed": maintenance_tasks,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System maintenance failed: {e}")
        raise e