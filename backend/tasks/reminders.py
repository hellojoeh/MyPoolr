"""Reminder and notification tasks with tier-based scheduling."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from celery_app import celery_app, exponential_backoff_retry
from database import db_manager
from monitoring import task_monitor

logger = logging.getLogger(__name__)


# Tier-based reminder schedules (hours before deadline)
TIER_REMINDER_SCHEDULES = {
    "starter": [24, 6, 1],  # 24h, 6h, 1h before deadline
    "essential": [48, 24, 12, 3, 1],  # More frequent reminders
    "advanced": [72, 48, 24, 12, 6, 2, 1],  # Even more frequent
    "extended": [96, 72, 48, 24, 12, 6, 3, 1]  # Maximum reminder frequency
}

# Rotation frequency to hours mapping
ROTATION_FREQUENCY_HOURS = {
    "daily": 24,
    "weekly": 168,  # 7 * 24
    "monthly": 720  # 30 * 24 (approximate)
}


@celery_app.task(bind=True, max_retries=3)
@task_monitor
@exponential_backoff_retry(max_retries=3, base_delay=60)
def process_rotation_reminder(self, mypoolr_id: str, rotation_date: str):
    """Send rotation reminders to members based on tier-specific schedules."""
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select(
            "*, member(*)"
        ).eq("id", mypoolr_id).execute()
        
        if not mypoolr_result.data:
            raise Exception(f"MyPoolr {mypoolr_id} not found")
        
        mypoolr = mypoolr_result.data[0]
        members = mypoolr.get("member", [])
        
        if not members:
            logger.warning(f"No members found for MyPoolr {mypoolr_id}")
            return {"status": "no_members", "mypoolr_id": mypoolr_id}
        
        # Get current rotation recipient
        current_position = mypoolr.get("current_rotation_position", 0)
        recipient = None
        contributors = []
        
        for member in members:
            if member["rotation_position"] == current_position + 1:  # Next in rotation
                recipient = member
            elif member["status"] == "active":
                contributors.append(member)
        
        if not recipient:
            raise Exception(f"No recipient found for rotation position {current_position + 1}")
        
        # Send reminders based on tier
        tier = mypoolr.get("tier", "starter")
        reminder_schedule = TIER_REMINDER_SCHEDULES.get(tier, TIER_REMINDER_SCHEDULES["starter"])
        
        # Calculate deadline
        rotation_datetime = datetime.fromisoformat(rotation_date.replace('Z', '+00:00'))
        frequency_hours = ROTATION_FREQUENCY_HOURS.get(mypoolr["rotation_frequency"], 24)
        deadline = rotation_datetime + timedelta(hours=frequency_hours)
        
        # Send reminders to contributors
        reminders_sent = []
        for contributor in contributors:
            reminder_data = {
                "mypoolr_id": mypoolr_id,
                "mypoolr_name": mypoolr["name"],
                "contributor_id": contributor["id"],
                "contributor_name": contributor["name"],
                "recipient_id": recipient["id"],
                "recipient_name": recipient["name"],
                "amount": str(mypoolr["contribution_amount"]),
                "deadline": deadline.isoformat(),
                "tier": tier,
                "reminder_schedule": reminder_schedule
            }
            
            # Schedule tier-based reminders
            for hours_before in reminder_schedule:
                reminder_time = deadline - timedelta(hours=hours_before)
                
                # Only schedule future reminders
                if reminder_time > datetime.utcnow():
                    schedule_contribution_reminder.apply_async(
                        args=[reminder_data, hours_before],
                        eta=reminder_time
                    )
            
            reminders_sent.append({
                "contributor": contributor["name"],
                "reminders_scheduled": len([h for h in reminder_schedule 
                                          if deadline - timedelta(hours=h) > datetime.utcnow()])
            })
        
        # Send notification to recipient
        recipient_notification_data = {
            "mypoolr_id": mypoolr_id,
            "mypoolr_name": mypoolr["name"],
            "recipient_id": recipient["id"],
            "recipient_name": recipient["name"],
            "expected_amount": str(mypoolr["contribution_amount"] * len(contributors)),
            "contributor_count": len(contributors),
            "deadline": deadline.isoformat()
        }
        
        send_recipient_notification.delay(recipient_notification_data)
        
        return {
            "status": "success",
            "mypoolr_id": mypoolr_id,
            "recipient": recipient["name"],
            "contributors_count": len(contributors),
            "reminders_sent": reminders_sent,
            "deadline": deadline.isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to process rotation reminder for {mypoolr_id}: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=5)
@task_monitor
@exponential_backoff_retry(max_retries=5, base_delay=30)
def schedule_contribution_reminder(self, reminder_data: Dict[str, Any], hours_before: int):
    """Send individual contribution reminder to a member."""
    try:
        contributor_id = reminder_data["contributor_id"]
        mypoolr_name = reminder_data["mypoolr_name"]
        recipient_name = reminder_data["recipient_name"]
        amount = reminder_data["amount"]
        deadline = datetime.fromisoformat(reminder_data["deadline"])
        
        # Calculate time remaining
        time_remaining = deadline - datetime.utcnow()
        hours_remaining = int(time_remaining.total_seconds() / 3600)
        
        # Create reminder message based on urgency
        if hours_remaining <= 1:
            urgency = "URGENT"
            message = f"🚨 FINAL REMINDER: Your contribution of {amount} to {recipient_name} in {mypoolr_name} is due in {hours_remaining} hour(s)!"
        elif hours_remaining <= 6:
            urgency = "HIGH"
            message = f"⏰ REMINDER: Your contribution of {amount} to {recipient_name} in {mypoolr_name} is due in {hours_remaining} hours."
        else:
            urgency = "NORMAL"
            message = f"📅 Reminder: Your contribution of {amount} to {recipient_name} in {mypoolr_name} is due in {hours_remaining} hours."
        
        # Log reminder (in production, this would send to Telegram bot)
        logger.info(f"Sending {urgency} reminder to contributor {contributor_id}: {message}")
        
        # Store reminder in database for tracking
        reminder_record = {
            "mypoolr_id": reminder_data["mypoolr_id"],
            "member_id": contributor_id,
            "reminder_type": "contribution",
            "urgency": urgency,
            "message": message,
            "hours_before_deadline": hours_before,
            "sent_at": datetime.utcnow().isoformat(),
            "deadline": reminder_data["deadline"]
        }
        
        # In production, store in reminders table
        # db_manager.client.table("reminders").insert(reminder_record).execute()
        
        return {
            "status": "sent",
            "contributor_id": contributor_id,
            "urgency": urgency,
            "hours_before": hours_before,
            "message": message
        }
        
    except Exception as exc:
        logger.error(f"Failed to send contribution reminder: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
@exponential_backoff_retry(max_retries=3, base_delay=60)
def send_recipient_notification(self, notification_data: Dict[str, Any]):
    """Send notification to rotation recipient about expected contributions."""
    try:
        recipient_id = notification_data["recipient_id"]
        mypoolr_name = notification_data["mypoolr_name"]
        expected_amount = notification_data["expected_amount"]
        contributor_count = notification_data["contributor_count"]
        deadline = datetime.fromisoformat(notification_data["deadline"])
        
        message = (
            f"🎉 It's your turn in {mypoolr_name}! "
            f"You should receive {expected_amount} from {contributor_count} members by {deadline.strftime('%Y-%m-%d %H:%M')}. "
            f"Please confirm each contribution as you receive it."
        )
        
        # Log notification (in production, this would send to Telegram bot)
        logger.info(f"Sending recipient notification to {recipient_id}: {message}")
        
        # Store notification record
        notification_record = {
            "mypoolr_id": notification_data["mypoolr_id"],
            "member_id": recipient_id,
            "notification_type": "recipient_turn",
            "message": message,
            "sent_at": datetime.utcnow().isoformat(),
            "deadline": notification_data["deadline"]
        }
        
        return {
            "status": "sent",
            "recipient_id": recipient_id,
            "message": message
        }
        
    except Exception as exc:
        logger.error(f"Failed to send recipient notification: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=5)
@task_monitor
@exponential_backoff_retry(max_retries=5, base_delay=120)
def check_contribution_timeout(self, mypoolr_id: str, member_id: str, deadline: str):
    """Check for contribution timeout after 24 hours and trigger default handling."""
    try:
        deadline_dt = datetime.fromisoformat(deadline)
        current_time = datetime.utcnow()
        
        # Check if deadline has passed
        if current_time <= deadline_dt:
            logger.info(f"Deadline not yet reached for member {member_id} in MyPoolr {mypoolr_id}")
            return {"status": "deadline_not_reached", "deadline": deadline}
        
        # Get member and MyPoolr details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", member_id
        ).execute()
        
        if not member_result.data:
            raise Exception(f"Member {member_id} not found")
        
        member = member_result.data[0]
        
        # Check if contribution was made (look for confirmed transaction)
        transaction_result = db_manager.client.table("transaction").select("*").eq(
            "mypoolr_id", mypoolr_id
        ).eq("from_member_id", member_id).eq(
            "transaction_type", "contribution"
        ).eq("confirmation_status", "both_confirmed").execute()
        
        # Check if there's a recent confirmed contribution
        recent_contribution = False
        if transaction_result.data:
            for transaction in transaction_result.data:
                created_at = datetime.fromisoformat(transaction["created_at"])
                if created_at >= deadline_dt - timedelta(hours=24):  # Within contribution window
                    recent_contribution = True
                    break
        
        if recent_contribution:
            logger.info(f"Contribution found for member {member_id}, no timeout action needed")
            return {"status": "contribution_found", "member_id": member_id}
        
        # No contribution found - trigger default handling
        logger.warning(f"Contribution timeout detected for member {member_id} in MyPoolr {mypoolr_id}")
        
        # Import here to avoid circular imports
        from tasks.defaults import handle_contribution_default
        
        # Trigger default handling
        handle_contribution_default.delay(mypoolr_id, member_id, "timeout")
        
        # Send timeout notification
        timeout_notification = {
            "mypoolr_id": mypoolr_id,
            "member_id": member_id,
            "member_name": member["name"],
            "deadline": deadline,
            "timeout_detected_at": current_time.isoformat()
        }
        
        send_timeout_notification.delay(timeout_notification)
        
        return {
            "status": "timeout_detected",
            "member_id": member_id,
            "deadline": deadline,
            "default_handling_triggered": True
        }
        
    except Exception as exc:
        logger.error(f"Failed to check contribution timeout: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
@exponential_backoff_retry(max_retries=3, base_delay=60)
def send_timeout_notification(self, timeout_data: Dict[str, Any]):
    """Send notification about contribution timeout."""
    try:
        member_name = timeout_data["member_name"]
        deadline = timeout_data["deadline"]
        
        # Get MyPoolr details for admin notification
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", timeout_data["mypoolr_id"]
        ).execute()
        
        if mypoolr_result.data:
            mypoolr = mypoolr_result.data[0]
            admin_id = mypoolr["admin_id"]
            
            admin_message = (
                f"⚠️ TIMEOUT ALERT: {member_name} missed their contribution deadline "
                f"({deadline}). Default handling has been triggered automatically."
            )
            
            member_message = (
                f"❌ You missed your contribution deadline in {mypoolr['name']}. "
                f"Your security deposit is being used to cover the contribution. "
                f"Please contact the admin to resolve this situation."
            )
            
            # Log notifications (in production, send to Telegram)
            logger.warning(f"Timeout notification to admin {admin_id}: {admin_message}")
            logger.warning(f"Timeout notification to member {timeout_data['member_id']}: {member_message}")
        
        return {
            "status": "notifications_sent",
            "member_id": timeout_data["member_id"],
            "timeout_detected_at": timeout_data["timeout_detected_at"]
        }
        
    except Exception as exc:
        logger.error(f"Failed to send timeout notification: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
def schedule_rotation_reminders(self, mypoolr_id: str):
    """Schedule all reminders for a rotation cycle."""
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", mypoolr_id
        ).execute()
        
        if not mypoolr_result.data:
            raise Exception(f"MyPoolr {mypoolr_id} not found")
        
        mypoolr = mypoolr_result.data[0]
        
        # Calculate rotation start time (now)
        rotation_start = datetime.utcnow()
        
        # Schedule initial rotation reminder
        process_rotation_reminder.delay(mypoolr_id, rotation_start.isoformat())
        
        # Schedule timeout check
        frequency_hours = ROTATION_FREQUENCY_HOURS.get(mypoolr["rotation_frequency"], 24)
        timeout_check_time = rotation_start + timedelta(hours=frequency_hours + 1)  # 1 hour after deadline
        
        # Get all active members for timeout checks
        members_result = db_manager.client.table("member").select("*").eq(
            "mypoolr_id", mypoolr_id
        ).eq("status", "active").execute()
        
        for member in members_result.data:
            if member["rotation_position"] != mypoolr["current_rotation_position"] + 1:  # Not the recipient
                check_contribution_timeout.apply_async(
                    args=[mypoolr_id, member["id"], timeout_check_time.isoformat()],
                    eta=timeout_check_time
                )
        
        return {
            "status": "scheduled",
            "mypoolr_id": mypoolr_id,
            "rotation_start": rotation_start.isoformat(),
            "timeout_checks_scheduled": len(members_result.data) - 1  # Exclude recipient
        }
        
    except Exception as exc:
        logger.error(f"Failed to schedule rotation reminders: {exc}")
        raise exc