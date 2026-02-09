"""Webhook handler for receiving notifications from backend."""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

from config import config


logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles webhooks from backend for sending notifications."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.notification_queue = asyncio.Queue()
        self._processing = False
    
    async def start_processing(self):
        """Start processing notification queue."""
        if self._processing:
            return
        
        self._processing = True
        logger.info("Started webhook notification processing")
        
        # Start background task to process notifications
        asyncio.create_task(self._process_notifications())
    
    async def stop_processing(self):
        """Stop processing notification queue."""
        self._processing = False
        logger.info("Stopped webhook notification processing")
    
    async def handle_notification_webhook(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming notification webhook from backend."""
        try:
            # Validate notification data
            if not self._validate_notification_data(notification_data):
                return {
                    "success": False,
                    "error": "invalid_notification_data",
                    "message": "Notification data validation failed"
                }
            
            # Add to processing queue
            await self.notification_queue.put(notification_data)
            
            logger.info(f"Queued notification for user {notification_data['recipient_id']}")
            
            return {
                "success": True,
                "message": "Notification queued for processing",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle notification webhook: {e}")
            return {
                "success": False,
                "error": "webhook_processing_failed",
                "message": str(e)
            }
    
    async def handle_system_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system webhooks (rotation updates, defaults, etc.)."""
        try:
            webhook_type = webhook_data.get("type")
            
            if webhook_type == "rotation_started":
                return await self._handle_rotation_started(webhook_data)
            elif webhook_type == "contribution_confirmed":
                return await self._handle_contribution_confirmed(webhook_data)
            elif webhook_type == "default_handled":
                return await self._handle_default_handled(webhook_data)
            elif webhook_type == "tier_upgraded":
                return await self._handle_tier_upgraded(webhook_data)
            else:
                logger.warning(f"Unknown webhook type: {webhook_type}")
                return {
                    "success": False,
                    "error": "unknown_webhook_type",
                    "message": f"Unknown webhook type: {webhook_type}"
                }
            
        except Exception as e:
            logger.error(f"Failed to handle system webhook: {e}")
            return {
                "success": False,
                "error": "system_webhook_failed",
                "message": str(e)
            }
    
    async def _process_notifications(self):
        """Background task to process notification queue."""
        while self._processing:
            try:
                # Wait for notification with timeout
                notification = await asyncio.wait_for(
                    self.notification_queue.get(),
                    timeout=5.0
                )
                
                # Send notification
                await self._send_telegram_notification(notification)
                
                # Mark task as done
                self.notification_queue.task_done()
                
            except asyncio.TimeoutError:
                # No notifications to process, continue
                continue
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                # Continue processing other notifications
                continue
    
    async def _send_telegram_notification(self, notification: Dict[str, Any]):
        """Send notification via Telegram."""
        try:
            recipient_id = notification["recipient_id"]
            title = notification["title"]
            message = notification["message"]
            notification_type = notification.get("notification_type", "general")
            
            # Format message with title
            full_message = f"*{title}*\n\n{message}"
            
            # Add appropriate emoji based on notification type
            emoji_map = {
                "rotation_start": "🎯",
                "contribution_reminder": "💰",
                "contribution_confirmed": "✅",
                "default_warning": "⚠️",
                "default_handled": "🚨",
                "member_joined": "👋",
                "tier_upgraded": "🚀",
                "general": "📢"
            }
            
            emoji = emoji_map.get(notification_type, "📢")
            full_message = f"{emoji} {full_message}"
            
            # Send message
            await self.bot.send_message(
                chat_id=recipient_id,
                text=full_message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Sent notification to user {recipient_id}: {notification_type}")
            
        except TelegramError as e:
            logger.error(f"Telegram error sending notification to {recipient_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending notification to {recipient_id}: {e}")
    
    async def _handle_rotation_started(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rotation started webhook."""
        try:
            mypoolr_id = webhook_data["mypoolr_id"]
            recipient_id = webhook_data["recipient_id"]
            mypoolr_name = webhook_data["mypoolr_name"]
            expected_amount = webhook_data["expected_amount"]
            
            # Send special rotation start message
            message = (
                f"🎯 *Your Turn in {mypoolr_name}*\n\n"
                f"It's your turn to receive contributions!\n"
                f"Expected amount: *{expected_amount:,.2f}*\n\n"
                f"Members will start contributing now. "
                f"You'll receive confirmation notifications as contributions are made."
            )
            
            await self.bot.send_message(
                chat_id=recipient_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Sent rotation start notification for MyPoolr {mypoolr_id}")
            
            return {"success": True, "message": "Rotation start notification sent"}
            
        except Exception as e:
            logger.error(f"Failed to handle rotation started webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_contribution_confirmed(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contribution confirmed webhook."""
        try:
            transaction_id = webhook_data["transaction_id"]
            mypoolr_name = webhook_data["mypoolr_name"]
            amount = webhook_data["amount"]
            sender_name = webhook_data["sender_name"]
            recipient_id = webhook_data["recipient_id"]
            
            # Send confirmation message
            message = (
                f"✅ *Contribution Confirmed*\n\n"
                f"Received *{amount:,.2f}* from {sender_name}\n"
                f"Group: {mypoolr_name}\n\n"
                f"Transaction ID: `{transaction_id}`"
            )
            
            await self.bot.send_message(
                chat_id=recipient_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Sent contribution confirmation for transaction {transaction_id}")
            
            return {"success": True, "message": "Contribution confirmation sent"}
            
        except Exception as e:
            logger.error(f"Failed to handle contribution confirmed webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_default_handled(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle default handled webhook."""
        try:
            mypoolr_id = webhook_data["mypoolr_id"]
            member_name = webhook_data["member_name"]
            amount = webhook_data["amount"]
            admin_id = webhook_data["admin_id"]
            
            # Send alert to admin
            message = (
                f"🚨 *Default Handled*\n\n"
                f"A missed contribution has been automatically covered:\n\n"
                f"• Member: {member_name}\n"
                f"• Amount: *{amount:,.2f}*\n"
                f"• Source: Security deposit\n\n"
                f"The member has been removed from future rotations until "
                f"they replenish their security deposit."
            )
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Sent default handled notification for MyPoolr {mypoolr_id}")
            
            return {"success": True, "message": "Default handled notification sent"}
            
        except Exception as e:
            logger.error(f"Failed to handle default handled webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_tier_upgraded(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tier upgraded webhook."""
        try:
            admin_id = webhook_data["admin_id"]
            new_tier = webhook_data["new_tier"]
            features = webhook_data.get("features", {})
            
            # Send upgrade confirmation
            message = (
                f"🚀 *Tier Upgrade Successful!*\n\n"
                f"You've been upgraded to *{new_tier}* tier!\n\n"
                f"New features unlocked:\n"
                f"• Max groups: {features.get('max_groups', 'N/A')}\n"
                f"• Max members per group: {features.get('max_members_per_group', 'N/A')}\n"
                f"• Reminder frequency: Every {features.get('reminder_frequency_hours', 'N/A')} hours\n"
            )
            
            if features.get("advanced_analytics"):
                message += "• Advanced analytics ✅\n"
            if features.get("export_data"):
                message += "• Data export ✅\n"
            if features.get("bulk_member_management"):
                message += "• Bulk member management ✅\n"
            if features.get("priority_support"):
                message += "• Priority support ✅\n"
            
            message += "\nEnjoy your enhanced MyPoolr experience!"
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Sent tier upgrade notification for admin {admin_id}")
            
            return {"success": True, "message": "Tier upgrade notification sent"}
            
        except Exception as e:
            logger.error(f"Failed to handle tier upgraded webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_notification_data(self, data: Dict[str, Any]) -> bool:
        """Validate notification data structure."""
        required_fields = ["recipient_id", "title", "message"]
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field in notification: {field}")
                return False
        
        # Validate recipient_id is integer
        try:
            int(data["recipient_id"])
        except (ValueError, TypeError):
            logger.error(f"Invalid recipient_id: {data['recipient_id']}")
            return False
        
        return True


# Global webhook handler instance
webhook_handler: Optional[WebhookHandler] = None


def initialize_webhook_handler(bot: Bot) -> WebhookHandler:
    """Initialize global webhook handler."""
    global webhook_handler
    webhook_handler = WebhookHandler(bot)
    return webhook_handler


def get_webhook_handler() -> Optional[WebhookHandler]:
    """Get global webhook handler instance."""
    return webhook_handler