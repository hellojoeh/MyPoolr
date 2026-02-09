"""Comprehensive notification service for MyPoolr system."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal

from models.notification import (
    Notification, NotificationTemplate, NotificationType, 
    NotificationPriority, NotificationStatus, NotificationChannel
)
from models.mypoolr import MyPoolr, TierLevel
from models.member import Member
from models.transaction import Transaction
from database import DatabaseManager


logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing all system notifications."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load notification templates from database."""
        try:
            result = self.db.client.table("notification_templates").select("*").eq("is_active", True).execute()
            for template_data in result.data:
                template = NotificationTemplate(**template_data)
                key = f"{template.notification_type}_{template.language_code}_{template.country_code}"
                self.templates[key] = template
        except Exception as e:
            logger.error(f"Failed to load notification templates: {e}")
    
    async def send_notification(
        self, 
        recipient_id: int,
        notification_type: NotificationType,
        template_data: Dict[str, Any],
        mypoolr_id: Optional[UUID] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        language_code: str = "en",
        country_code: str = "US"
    ) -> Notification:
        """Send a notification to a recipient."""
        
        # Get template
        template = self._get_template(notification_type, language_code, country_code)
        
        # Render message from template
        title, message = self._render_template(template, template_data)
        
        # Create notification record
        notification = Notification(
            mypoolr_id=mypoolr_id,
            recipient_id=recipient_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            scheduled_at=scheduled_at or datetime.utcnow(),
            template_data=template_data,
            language_code=language_code,
            country_code=country_code
        )
        
        # Store notification
        await self._store_notification(notification)
        
        # Send immediately if not scheduled
        if scheduled_at is None or scheduled_at <= datetime.utcnow():
            await self._deliver_notification(notification)
        
        return notification
    
    def _get_template(self, notification_type: NotificationType, language_code: str, country_code: str) -> NotificationTemplate:
        """Get notification template for type and locale."""
        
        # Try exact match first
        key = f"{notification_type}_{language_code}_{country_code}"
        if key in self.templates:
            return self.templates[key]
        
        # Try language fallback
        key = f"{notification_type}_{language_code}_US"
        if key in self.templates:
            return self.templates[key]
        
        # Try default fallback
        key = f"{notification_type}_en_US"
        if key in self.templates:
            return self.templates[key]
        
        # Return default template
        return self._get_default_template(notification_type)
    
    def _get_default_template(self, notification_type: NotificationType) -> NotificationTemplate:
        """Get default template for notification type."""
        
        templates = {
            NotificationType.ROTATION_START: NotificationTemplate(
                template_key="rotation_start_default",
                notification_type=notification_type,
                language_code="en",
                country_code="US",
                title_template="🎯 Your Turn in {mypoolr_name}",
                message_template="It's your turn to receive contributions in {mypoolr_name}! Expected amount: {expected_amount}. {contributor_count} members will contribute."
            ),
            NotificationType.CONTRIBUTION_REMINDER: NotificationTemplate(
                template_key="contribution_reminder_default",
                notification_type=notification_type,
                language_code="en",
                country_code="US",
                title_template="💰 Contribution Due in {mypoolr_name}",
                message_template="Please contribute {amount} to {recipient_name} in {mypoolr_name}. Deadline: {deadline}"
            ),
            NotificationType.CONTRIBUTION_CONFIRMED: NotificationTemplate(
                template_key="contribution_confirmed_default",
                notification_type=notification_type,
                language_code="en",
                country_code="US",
                title_template="✅ Contribution Confirmed",
                message_template="Contribution of {amount} from {sender_name} has been confirmed in {mypoolr_name}."
            ),
            NotificationType.DEFAULT_WARNING: NotificationTemplate(
                template_key="default_warning_default",
                notification_type=notification_type,
                language_code="en",
                country_code="US",
                title_template="⚠️ Contribution Deadline Approaching",
                message_template="Your contribution of {amount} to {recipient_name} in {mypoolr_name} is due in {hours_remaining} hours!"
            ),
            NotificationType.DEFAULT_HANDLED: NotificationTemplate(
                template_key="default_handled_default",
                notification_type=notification_type,
                language_code="en",
                country_code="US",
                title_template="🚨 Default Handled",
                message_template="A missed contribution in {mypoolr_name} has been covered using security deposit. Member: {member_name}, Amount: {amount}"
            )
        }
        
        return templates.get(notification_type, NotificationTemplate(
            template_key="generic_default",
            notification_type=notification_type,
            language_code="en",
            country_code="US",
            title_template="MyPoolr Notification",
            message_template="You have a new notification from MyPoolr."
        ))
    
    def _render_template(self, template: NotificationTemplate, data: Dict[str, Any]) -> tuple[str, str]:
        """Render notification template with data."""
        
        try:
            title = template.title_template.format(**data)
            message = template.message_template.format(**data)
            return title, message
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template.title_template, template.message_template
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return "MyPoolr Notification", "You have a new notification."
    
    async def _store_notification(self, notification: Notification) -> None:
        """Store notification in database."""
        
        try:
            notification_data = notification.dict()
            # Convert UUID to string for database storage
            if notification_data.get('mypoolr_id'):
                notification_data['mypoolr_id'] = str(notification_data['mypoolr_id'])
            notification_data['id'] = str(notification_data['id'])
            
            self.db.client.table("notifications").insert(notification_data).execute()
            logger.info(f"Stored notification {notification.id} for recipient {notification.recipient_id}")
            
        except Exception as e:
            logger.error(f"Failed to store notification: {e}")
            raise
    
    async def _deliver_notification(self, notification: Notification) -> bool:
        """Deliver notification via appropriate channel."""
        
        try:
            if notification.channel == NotificationChannel.TELEGRAM:
                return await self._send_telegram_notification(notification)
            else:
                logger.warning(f"Unsupported notification channel: {notification.channel}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to deliver notification {notification.id}: {e}")
            await self._mark_notification_failed(notification)
            return False
    
    async def _send_telegram_notification(self, notification: Notification) -> bool:
        """Send notification via Telegram bot."""
        
        # In production, this would integrate with the Telegram bot
        # For now, we'll log the notification
        logger.info(
            f"TELEGRAM NOTIFICATION to {notification.recipient_id}: "
            f"{notification.title} - {notification.message}"
        )
        
        # Mark as sent
        await self._mark_notification_sent(notification)
        return True
    
    async def _mark_notification_sent(self, notification: Notification) -> None:
        """Mark notification as sent."""
        
        try:
            self.db.client.table("notifications").update({
                "status": NotificationStatus.SENT,
                "sent_at": datetime.utcnow().isoformat()
            }).eq("id", str(notification.id)).execute()
            
        except Exception as e:
            logger.error(f"Failed to mark notification as sent: {e}")
    
    async def _mark_notification_failed(self, notification: Notification) -> None:
        """Mark notification as failed."""
        
        try:
            self.db.client.table("notifications").update({
                "status": NotificationStatus.FAILED,
                "retry_count": notification.retry_count + 1
            }).eq("id", str(notification.id)).execute()
            
        except Exception as e:
            logger.error(f"Failed to mark notification as failed: {e}")
    
    # Rotation Event Notifications
    
    async def notify_rotation_start(
        self, 
        mypoolr: MyPoolr, 
        recipient: Member, 
        contributors: List[Member],
        expected_amount: Decimal
    ) -> List[Notification]:
        """Notify about rotation start."""
        
        notifications = []
        
        # Notify recipient
        recipient_notification = await self.send_notification(
            recipient_id=recipient.telegram_id,
            notification_type=NotificationType.ROTATION_START,
            template_data={
                "mypoolr_name": mypoolr.name,
                "expected_amount": f"{expected_amount:,.2f}",
                "contributor_count": len(contributors)
            },
            mypoolr_id=mypoolr.id,
            priority=NotificationPriority.HIGH
        )
        notifications.append(recipient_notification)
        
        # Notify contributors
        for contributor in contributors:
            contributor_notification = await self.send_notification(
                recipient_id=contributor.telegram_id,
                notification_type=NotificationType.CONTRIBUTION_REMINDER,
                template_data={
                    "mypoolr_name": mypoolr.name,
                    "amount": f"{mypoolr.contribution_amount:,.2f}",
                    "recipient_name": recipient.name,
                    "deadline": (datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
                },
                mypoolr_id=mypoolr.id,
                priority=NotificationPriority.NORMAL
            )
            notifications.append(contributor_notification)
        
        # Notify admin
        admin_notification = await self.send_notification(
            recipient_id=mypoolr.admin_id,
            notification_type=NotificationType.ROTATION_START,
            template_data={
                "mypoolr_name": mypoolr.name,
                "recipient_name": recipient.name,
                "expected_amount": f"{expected_amount:,.2f}",
                "contributor_count": len(contributors)
            },
            mypoolr_id=mypoolr.id,
            priority=NotificationPriority.NORMAL
        )
        notifications.append(admin_notification)
        
        return notifications
    
    async def notify_contribution_confirmed(
        self, 
        mypoolr: MyPoolr, 
        transaction: Transaction,
        sender: Member,
        recipient: Member
    ) -> List[Notification]:
        """Notify about contribution confirmation."""
        
        notifications = []
        
        # Notify recipient
        recipient_notification = await self.send_notification(
            recipient_id=recipient.telegram_id,
            notification_type=NotificationType.CONTRIBUTION_CONFIRMED,
            template_data={
                "mypoolr_name": mypoolr.name,
                "amount": f"{transaction.amount:,.2f}",
                "sender_name": sender.name
            },
            mypoolr_id=mypoolr.id
        )
        notifications.append(recipient_notification)
        
        # Notify admin
        admin_notification = await self.send_notification(
            recipient_id=mypoolr.admin_id,
            notification_type=NotificationType.CONTRIBUTION_CONFIRMED,
            template_data={
                "mypoolr_name": mypoolr.name,
                "amount": f"{transaction.amount:,.2f}",
                "sender_name": sender.name,
                "recipient_name": recipient.name
            },
            mypoolr_id=mypoolr.id
        )
        notifications.append(admin_notification)
        
        return notifications
    
    async def notify_default_warning(
        self, 
        mypoolr: MyPoolr, 
        member: Member,
        recipient: Member,
        hours_remaining: int
    ) -> Notification:
        """Send default warning notification."""
        
        return await self.send_notification(
            recipient_id=member.telegram_id,
            notification_type=NotificationType.DEFAULT_WARNING,
            template_data={
                "mypoolr_name": mypoolr.name,
                "amount": f"{mypoolr.contribution_amount:,.2f}",
                "recipient_name": recipient.name,
                "hours_remaining": hours_remaining
            },
            mypoolr_id=mypoolr.id,
            priority=NotificationPriority.HIGH
        )
    
    async def notify_default_handled(
        self, 
        mypoolr: MyPoolr, 
        defaulted_member: Member,
        amount: Decimal
    ) -> List[Notification]:
        """Notify about handled default."""
        
        notifications = []
        
        # Notify admin
        admin_notification = await self.send_notification(
            recipient_id=mypoolr.admin_id,
            notification_type=NotificationType.DEFAULT_HANDLED,
            template_data={
                "mypoolr_name": mypoolr.name,
                "member_name": defaulted_member.name,
                "amount": f"{amount:,.2f}"
            },
            mypoolr_id=mypoolr.id,
            priority=NotificationPriority.URGENT
        )
        notifications.append(admin_notification)
        
        # Notify defaulted member
        member_notification = await self.send_notification(
            recipient_id=defaulted_member.telegram_id,
            notification_type=NotificationType.DEFAULT_HANDLED,
            template_data={
                "mypoolr_name": mypoolr.name,
                "member_name": defaulted_member.name,
                "amount": f"{amount:,.2f}"
            },
            mypoolr_id=mypoolr.id,
            priority=NotificationPriority.URGENT
        )
        notifications.append(member_notification)
        
        return notifications
    
    async def notify_member_joined(
        self, 
        mypoolr: MyPoolr, 
        new_member: Member
    ) -> List[Notification]:
        """Notify about new member joining."""
        
        notifications = []
        
        # Get all existing members
        members_result = self.db.client.table("members").select("*").eq("mypoolr_id", str(mypoolr.id)).execute()
        
        # Notify admin
        admin_notification = await self.send_notification(
            recipient_id=mypoolr.admin_id,
            notification_type=NotificationType.MEMBER_JOINED,
            template_data={
                "mypoolr_name": mypoolr.name,
                "member_name": new_member.name,
                "total_members": len(members_result.data)
            },
            mypoolr_id=mypoolr.id
        )
        notifications.append(admin_notification)
        
        return notifications
    
    async def get_pending_notifications(self, limit: int = 100) -> List[Notification]:
        """Get pending notifications for processing."""
        
        try:
            result = self.db.client.table("notifications").select("*").eq(
                "status", NotificationStatus.PENDING
            ).lte(
                "scheduled_at", datetime.utcnow().isoformat()
            ).limit(limit).execute()
            
            return [Notification(**data) for data in result.data]
            
        except Exception as e:
            logger.error(f"Failed to get pending notifications: {e}")
            return []
    
    async def retry_failed_notifications(self) -> int:
        """Retry failed notifications that haven't exceeded max retries."""
        
        try:
            # Get failed notifications that can be retried
            result = self.db.client.table("notifications").select("*").eq(
                "status", NotificationStatus.FAILED
            ).lt("retry_count", "max_retries").execute()
            
            retried_count = 0
            for notification_data in result.data:
                notification = Notification(**notification_data)
                
                # Reset status to pending for retry
                self.db.client.table("notifications").update({
                    "status": NotificationStatus.PENDING,
                    "scheduled_at": datetime.utcnow().isoformat()
                }).eq("id", str(notification.id)).execute()
                
                retried_count += 1
            
            logger.info(f"Queued {retried_count} notifications for retry")
            return retried_count
            
        except Exception as e:
            logger.error(f"Failed to retry notifications: {e}")
            return 0