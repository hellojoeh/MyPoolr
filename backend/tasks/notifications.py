"""Notification processing tasks."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID

from celery_app import celery_app
from database import DatabaseManager
from ..services.notification_service import NotificationService
from ..models.notification import NotificationType, NotificationPriority
from ..models.mypoolr import MyPoolr
from ..models.member import Member
from ..models.transaction import Transaction
from ..monitoring import monitor_task_execution, exponential_backoff_retry


logger = logging.getLogger(__name__)
db_manager = DatabaseManager()
notification_service = NotificationService(db_manager)


@celery_app.task(bind=True, max_retries=3)
@monitor_task_execution
@exponential_backoff_retry(max_retries=3, base_delay=30)
def process_pending_notifications(self):
    """Process all pending notifications."""
    
    try:
        import asyncio
        
        # Get pending notifications
        pending_notifications = asyncio.run(notification_service.get_pending_notifications(limit=100))
        
        processed_count = 0
        failed_count = 0
        
        for notification in pending_notifications:
            try:
                success = asyncio.run(notification_service._deliver_notification(notification))
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process notification {notification.id}: {e}")
                failed_count += 1
        
        logger.info(f"Processed {processed_count} notifications, {failed_count} failed")
        
        return {
            "status": "completed",
            "processed": processed_count,
            "failed": failed_count,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to process pending notifications: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@monitor_task_execution
@exponential_backoff_retry(max_retries=3, base_delay=60)
def retry_failed_notifications(self):
    """Retry failed notifications that haven't exceeded max retries."""
    
    try:
        import asyncio
        retried_count = asyncio.run(notification_service.retry_failed_notifications())
        
        logger.info(f"Queued {retried_count} failed notifications for retry")
        
        return {
            "status": "completed",
            "retried_count": retried_count,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to retry notifications: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@monitor_task_execution
@exponential_backoff_retry(max_retries=3, base_delay=30)
def send_rotation_start_notifications(self, mypoolr_id: str, recipient_member_id: str):
    """Send notifications for rotation start."""
    
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
        if not mypoolr_result.data:
            raise ValueError(f"MyPoolr not found: {mypoolr_id}")
        
        mypoolr = MyPoolr(**mypoolr_result.data[0])
        
        # Get recipient member
        recipient_result = db_manager.client.table("members").select("*").eq("id", recipient_member_id).execute()
        if not recipient_result.data:
            raise ValueError(f"Recipient member not found: {recipient_member_id}")
        
        recipient = Member(**recipient_result.data[0])
        
        # Get all contributing members (excluding recipient)
        contributors_result = db_manager.client.table("members").select("*").eq(
            "mypoolr_id", mypoolr_id
        ).neq("id", recipient_member_id).eq("status", "active").execute()
        
        contributors = [Member(**data) for data in contributors_result.data]
        
        # Calculate expected amount
        expected_amount = mypoolr.contribution_amount * len(contributors)
        
        # Send notifications
        notifications = asyncio.run(notification_service.notify_rotation_start(
            mypoolr=mypoolr,
            recipient=recipient,
            contributors=contributors,
            expected_amount=expected_amount
        ))
        
        logger.info(f"Sent {len(notifications)} rotation start notifications for MyPoolr {mypoolr_id}")
        
        return {
            "status": "completed",
            "mypoolr_id": mypoolr_id,
            "recipient_id": recipient_member_id,
            "notifications_sent": len(notifications),
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to send rotation start notifications: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@monitor_task_execution
@exponential_backoff_retry(max_retries=3, base_delay=30)
def send_contribution_confirmed_notifications(self, transaction_id: str):
    """Send notifications for contribution confirmation."""
    
    try:
        # Get transaction details
        transaction_result = db_manager.client.table("transactions").select("*").eq("id", transaction_id).execute()
        if not transaction_result.data:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        transaction = Transaction(**transaction_result.data[0])
        
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq("id", str(transaction.mypoolr_id)).execute()
        if not mypoolr_result.data:
            raise ValueError(f"MyPoolr not found: {transaction.mypoolr_id}")
        
        mypoolr = MyPoolr(**mypoolr_result.data[0])
        
        # Get sender and recipient members
        sender_result = db_manager.client.table("members").select("*").eq("id", str(transaction.from_member_id)).execute()
        recipient_result = db_manager.client.table("members").select("*").eq("id", str(transaction.to_member_id)).execute()
        
        if not sender_result.data or not recipient_result.data:
            raise ValueError("Sender or recipient member not found")
        
        sender = Member(**sender_result.data[0])
        recipient = Member(**recipient_result.data[0])
        
        # Send notifications
        notifications = asyncio.run(notification_service.notify_contribution_confirmed(
            mypoolr=mypoolr,
            transaction=transaction,
            sender=sender,
            recipient=recipient
        ))
        
        logger.info(f"Sent {len(notifications)} contribution confirmed notifications for transaction {transaction_id}")
        
        return {
            "status": "completed",
            "transaction_id": transaction_id,
            "notifications_sent": len(notifications),
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to send contribution confirmed notifications: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@monitor_task_execution
@exponential_backoff_retry(max_retries=3, base_delay=30)
def send_default_warning_notifications(self, mypoolr_id: str, member_id: str, recipient_id: str, hours_remaining: int):
    """Send default warning notifications."""
    
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
        if not mypoolr_result.data:
            raise ValueError(f"MyPoolr not found: {mypoolr_id}")
        
        mypoolr = MyPoolr(**mypoolr_result.data[0])
        
        # Get member and recipient details
        member_result = db_manager.client.table("members").select("*").eq("id", member_id).execute()
        recipient_result = db_manager.client.table("members").select("*").eq("id", recipient_id).execute()
        
        if not member_result.data or not recipient_result.data:
            raise ValueError("Member or recipient not found")
        
        member = Member(**member_result.data[0])
        recipient = Member(**recipient_result.data[0])
        
        # Send warning notification
        notification = asyncio.run(notification_service.notify_default_warning(
            mypoolr=mypoolr,
            member=member,
            recipient=recipient,
            hours_remaining=hours_remaining
        ))
        
        logger.info(f"Sent default warning notification to member {member_id}")
        
        return {
            "status": "completed",
            "mypoolr_id": mypoolr_id,
            "member_id": member_id,
            "notification_sent": True,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to send default warning notification: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@monitor_task_execution
@exponential_backoff_retry(max_retries=3, base_delay=30)
def send_default_handled_notifications(self, mypoolr_id: str, defaulted_member_id: str, amount: float):
    """Send notifications for handled default."""
    
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
        if not mypoolr_result.data:
            raise ValueError(f"MyPoolr not found: {mypoolr_id}")
        
        mypoolr = MyPoolr(**mypoolr_result.data[0])
        
        # Get defaulted member details
        member_result = db_manager.client.table("members").select("*").eq("id", defaulted_member_id).execute()
        if not member_result.data:
            raise ValueError(f"Member not found: {defaulted_member_id}")
        
        defaulted_member = Member(**member_result.data[0])
        
        # Send notifications
        notifications = asyncio.run(notification_service.notify_default_handled(
            mypoolr=mypoolr,
            defaulted_member=defaulted_member,
            amount=amount
        ))
        
        logger.info(f"Sent {len(notifications)} default handled notifications for member {defaulted_member_id}")
        
        return {
            "status": "completed",
            "mypoolr_id": mypoolr_id,
            "defaulted_member_id": defaulted_member_id,
            "notifications_sent": len(notifications),
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to send default handled notifications: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@monitor_task_execution
@exponential_backoff_retry(max_retries=3, base_delay=30)
def send_member_joined_notifications(self, mypoolr_id: str, new_member_id: str):
    """Send notifications for new member joining."""
    
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
        if not mypoolr_result.data:
            raise ValueError(f"MyPoolr not found: {mypoolr_id}")
        
        mypoolr = MyPoolr(**mypoolr_result.data[0])
        
        # Get new member details
        member_result = db_manager.client.table("members").select("*").eq("id", new_member_id).execute()
        if not member_result.data:
            raise ValueError(f"Member not found: {new_member_id}")
        
        new_member = Member(**member_result.data[0])
        
        # Send notifications
        notifications = asyncio.run(notification_service.notify_member_joined(
            mypoolr=mypoolr,
            new_member=new_member
        ))
        
        logger.info(f"Sent {len(notifications)} member joined notifications for {new_member_id}")
        
        return {
            "status": "completed",
            "mypoolr_id": mypoolr_id,
            "new_member_id": new_member_id,
            "notifications_sent": len(notifications),
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to send member joined notifications: {exc}")
        raise exc


@celery_app.task(bind=True)
@monitor_task_execution
def cleanup_old_notifications(self, days_old: int = 30):
    """Clean up old notifications to prevent database bloat."""
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Delete old delivered notifications
        result = db_manager.client.table("notifications").delete().eq(
            "status", "delivered"
        ).lt("created_at", cutoff_date.isoformat()).execute()
        
        deleted_count = len(result.data) if result.data else 0
        
        logger.info(f"Cleaned up {deleted_count} old notifications older than {days_old} days")
        
        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to cleanup old notifications: {exc}")
        raise exc