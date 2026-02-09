"""Advanced UI components for trillion-dollar user experience."""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from .button_manager import ButtonManager, ButtonGrid, ButtonState
from .formatters import MessageFormatter, EmojiHelper


class UITheme(Enum):
    """UI themes for different contexts."""
    DEFAULT = "default"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PREMIUM = "premium"


@dataclass
class UIContext:
    """Context information for UI rendering."""
    user_id: int
    user_role: str = "member"
    theme: UITheme = UITheme.DEFAULT
    screen_size: str = "mobile"
    language: str = "en"
    timezone: str = "UTC"


class ProgressIndicator:
    """Visual progress indicators for multi-step workflows."""
    
    @staticmethod
    def create_step_indicator(current_step: int, total_steps: int, step_names: List[str]) -> str:
        """Create a visual step indicator."""
        if len(step_names) != total_steps:
            step_names = [f"Step {i+1}" for i in range(total_steps)]
        
        indicators = []
        for i, name in enumerate(step_names):
            if i < current_step:
                indicators.append(f"✅ {name}")
            elif i == current_step:
                indicators.append(f"🔄 {name}")
            else:
                indicators.append(f"⏳ {name}")
        
        progress_bar = MessageFormatter.format_progress_bar(current_step, total_steps)
        
        return f"""
📋 *Progress* ({current_step}/{total_steps})
{progress_bar}

{chr(10).join(indicators)}
        """.strip()
    
    @staticmethod
    def create_circular_progress(percentage: float) -> str:
        """Create a circular progress indicator."""
        if percentage >= 100:
            return "🟢 Complete"
        elif percentage >= 75:
            return "🔵 Almost there"
        elif percentage >= 50:
            return "🟡 Halfway"
        elif percentage >= 25:
            return "🟠 Getting started"
        else:
            return "⚪ Just started"


class NotificationBanner:
    """Rich notification banners for user feedback."""
    
    @staticmethod
    def create_success_banner(title: str, message: str) -> str:
        """Create success notification banner."""
        return f"""
🎉 *{title}*
{EmojiHelper.SUCCESS} {message}

━━━━━━━━━━━━━━━━━━━━
        """.strip()
    
    @staticmethod
    def create_warning_banner(title: str, message: str, action_required: bool = False) -> str:
        """Create warning notification banner."""
        action_text = "\n⚡ Action required!" if action_required else ""
        
        return f"""
⚠️ *{title}*
{EmojiHelper.WARNING} {message}{action_text}

━━━━━━━━━━━━━━━━━━━━
        """.strip()
    
    @staticmethod
    def create_error_banner(title: str, message: str, support_info: bool = True) -> str:
        """Create error notification banner."""
        support_text = "\n💬 Contact support if this persists." if support_info else ""
        
        return f"""
🚨 *{title}*
{EmojiHelper.ERROR} {message}{support_text}

━━━━━━━━━━━━━━━━━━━━
        """.strip()


class InteractiveCard:
    """Interactive card components for rich information display."""
    
    def __init__(self, button_manager: ButtonManager):
        self.button_manager = button_manager
    
    def create_mypoolr_card(self, mypoolr_data: Dict[str, Any], context: UIContext) -> Tuple[str, ButtonGrid]:
        """Create an interactive MyPoolr information card."""
        name = MessageFormatter.escape_markdown(mypoolr_data.get("name", "Unknown"))
        amount = MessageFormatter.format_currency(mypoolr_data.get("contribution_amount", 0))
        frequency = mypoolr_data.get("rotation_frequency", "unknown").title()
        member_count = mypoolr_data.get("member_count", 0)
        member_limit = mypoolr_data.get("member_limit", 0)
        status = mypoolr_data.get("status", "active")
        
        # Status indicator
        status_emoji = {
            "active": "🟢",
            "paused": "🟡",
            "completed": "✅",
            "cancelled": "🔴"
        }.get(status, "⚪")
        
        # Progress calculation
        total_rotations = member_count
        completed_rotations = mypoolr_data.get("completed_rotations", 0)
        progress_percentage = (completed_rotations / total_rotations * 100) if total_rotations > 0 else 0
        
        card_text = f"""
🎯 *{name}*
{status_emoji} Status: {status.title()}

💰 *Contribution:* {amount}
📅 *Frequency:* {frequency}
👥 *Members:* {member_count}/{member_limit}

📊 *Progress:*
{MessageFormatter.format_progress_bar(completed_rotations, total_rotations, 15)}
{completed_rotations}/{total_rotations} rotations ({progress_percentage:.1f}%)
        """.strip()
        
        # Create contextual buttons
        buttons = self.button_manager.create_contextual_menu("mypoolr_main", context.user_role)
        
        return card_text, buttons
    
    def create_member_card(self, member_data: Dict[str, Any]) -> Tuple[str, ButtonGrid]:
        """Create an interactive member information card."""
        name = MessageFormatter.escape_markdown(member_data.get("name", "Unknown"))
        position = member_data.get("rotation_position", 0)
        security_paid = member_data.get("security_deposit_paid", False)
        has_received = member_data.get("has_received_payout", False)
        
        # Status indicators
        security_status = "✅ Paid" if security_paid else "⏳ Pending"
        payout_status = "✅ Received" if has_received else "⏳ Waiting"
        
        card_text = f"""
👤 *{name}*
📍 Position: #{position}

🔒 Security Deposit: {security_status}
💰 Payout Status: {payout_status}
        """.strip()
        
        # Member action buttons
        grid = self.button_manager.create_grid()
        if not security_paid:
            grid.add_row([
                self.button_manager.create_button(
                    "💳 Pay Security Deposit",
                    f"pay_security:{member_data.get('id')}",
                    emoji="💳"
                )
            ])
        
        grid.add_row([
            self.button_manager.create_button("📊 View Details", f"member_details:{member_data.get('id')}", emoji="📊"),
            self.button_manager.create_button("💬 Contact", f"contact_member:{member_data.get('id')}", emoji="💬")
        ])
        
        return card_text, grid
    
    def create_contribution_card(self, contribution_data: Dict[str, Any]) -> Tuple[str, ButtonGrid]:
        """Create an interactive contribution request card."""
        amount = MessageFormatter.format_currency(contribution_data.get("amount", 0))
        recipient = MessageFormatter.escape_markdown(contribution_data.get("recipient_name", "Unknown"))
        due_date = contribution_data.get("due_date")
        status = contribution_data.get("status", "pending")
        
        # Time remaining calculation
        time_info = ""
        if due_date:
            due_dt = datetime.fromisoformat(due_date)
            time_info = f"\n{MessageFormatter.format_time_remaining(due_dt)}"
        
        # Status indicator
        status_emoji = {
            "pending": "⏳",
            "sender_confirmed": "🔄",
            "completed": "✅",
            "overdue": "🔴"
        }.get(status, "⚪")
        
        card_text = f"""
💸 *Contribution Request*
{status_emoji} Status: {status.title()}

💰 Amount: {amount}
👤 Recipient: {recipient}{time_info}

📋 Next: Confirm your payment
        """.strip()
        
        # Contribution action buttons
        grid = self.button_manager.create_grid()
        
        if status == "pending":
            grid.add_row([
                self.button_manager.create_button(
                    "✅ I've Paid",
                    f"confirm_payment:{contribution_data.get('id')}",
                    emoji="✅"
                ),
                self.button_manager.create_button(
                    "📸 Upload Receipt",
                    f"upload_receipt:{contribution_data.get('id')}",
                    emoji="📸"
                )
            ])
        
        grid.add_row([
            self.button_manager.create_button("💬 Contact Recipient", f"contact_recipient:{contribution_data.get('recipient_id')}", emoji="💬"),
            self.button_manager.create_button("❓ Need Help", "help_contribution", emoji="❓")
        ])
        
        return card_text, grid


class AnimationManager:
    """Manages smooth animations and transitions."""
    
    @staticmethod
    async def typing_animation(update: Update, context: ContextTypes.DEFAULT_TYPE, duration: float = 2.0) -> None:
        """Show typing animation."""
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            await asyncio.sleep(duration)
        except Exception as e:
            logger.warning(f"Typing animation failed: {e}")
    
    @staticmethod
    async def smooth_message_update(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        new_text: str,
        new_keyboard: Optional[InlineKeyboardMarkup] = None,
        delay: float = 0.5
    ) -> None:
        """Update message with smooth transition."""
        try:
            # Show typing indicator
            await AnimationManager.typing_animation(update, context, delay)
            
            # Update message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=new_text,
                    reply_markup=new_keyboard,
                    parse_mode="Markdown"
                )
            else:
                await update.message.edit_text(
                    text=new_text,
                    reply_markup=new_keyboard,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Message update failed: {e}")
    
    @staticmethod
    async def celebration_animation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show celebration animation for successful actions."""
        celebration_frames = [
            "🎉 Success!",
            "🎊 Awesome!",
            "✨ Perfect!",
            "🎯 Done!"
        ]
        
        try:
            for frame in celebration_frames:
                if update.callback_query:
                    await update.callback_query.edit_message_text(frame)
                else:
                    await update.message.edit_text(frame)
                await asyncio.sleep(0.8)
        except Exception as e:
            logger.warning(f"Celebration animation failed: {e}")


class ResponsiveLayout:
    """Responsive layout management for different screen sizes."""
    
    @staticmethod
    def detect_screen_size(user_agent: Optional[str] = None) -> str:
        """Detect screen size from user agent (placeholder implementation)."""
        # In a real implementation, this would parse user agent
        # For now, default to mobile-first approach
        return "mobile"
    
    @staticmethod
    def optimize_button_layout(buttons: List[Dict[str, Any]], screen_size: str) -> List[List[Dict[str, Any]]]:
        """Optimize button layout for screen size."""
        if screen_size == "desktop":
            max_per_row = 4
        elif screen_size == "tablet":
            max_per_row = 3
        else:  # mobile
            max_per_row = 2
        
        # Group buttons into rows
        rows = []
        for i in range(0, len(buttons), max_per_row):
            rows.append(buttons[i:i + max_per_row])
        
        return rows
    
    @staticmethod
    def format_text_for_screen(text: str, screen_size: str) -> str:
        """Format text content for different screen sizes."""
        if screen_size == "mobile":
            # Shorter lines for mobile
            max_line_length = 30
        else:
            max_line_length = 50
        
        # Simple line wrapping (in a real implementation, this would be more sophisticated)
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_line_length:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)