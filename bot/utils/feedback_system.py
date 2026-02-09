"""Advanced feedback system for user interactions."""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from .button_manager import ButtonManager, ButtonState
from .formatters import EmojiHelper


class FeedbackType(Enum):
    """Types of user feedback."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    LOADING = "loading"
    PROGRESS = "progress"


@dataclass
class FeedbackConfig:
    """Configuration for feedback display."""
    type: FeedbackType
    title: str
    message: str
    duration: float = 3.0
    auto_dismiss: bool = True
    show_progress: bool = False
    progress_steps: Optional[List[str]] = None


class VisualFeedbackManager:
    """Manages visual feedback for user interactions."""
    
    def __init__(self):
        self.active_feedbacks: Dict[int, Dict[str, Any]] = {}
        self.feedback_templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[FeedbackType, Dict[str, str]]:
        """Initialize feedback templates."""
        return {
            FeedbackType.SUCCESS: {
                "emoji": "✅",
                "color": "🟢",
                "prefix": "Success!"
            },
            FeedbackType.ERROR: {
                "emoji": "❌",
                "color": "🔴",
                "prefix": "Error!"
            },
            FeedbackType.WARNING: {
                "emoji": "⚠️",
                "color": "🟡",
                "prefix": "Warning!"
            },
            FeedbackType.INFO: {
                "emoji": "ℹ️",
                "color": "🔵",
                "prefix": "Info"
            },
            FeedbackType.LOADING: {
                "emoji": "⏳",
                "color": "⚪",
                "prefix": "Loading..."
            },
            FeedbackType.PROGRESS: {
                "emoji": "📊",
                "color": "🟦",
                "prefix": "Progress"
            }
        }
    
    async def show_feedback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        config: FeedbackConfig
    ) -> None:
        """Show feedback to user."""
        user_id = update.effective_user.id
        template = self.feedback_templates[config.type]
        
        # Format feedback message
        feedback_text = self._format_feedback_message(config, template)
        
        try:
            # Send or update feedback message
            if config.type == FeedbackType.LOADING and config.show_progress:
                await self._show_progress_feedback(update, context, config)
            else:
                await self._show_simple_feedback(update, context, feedback_text, config)
            
            # Store active feedback
            self.active_feedbacks[user_id] = {
                "config": config,
                "timestamp": datetime.now()
            }
            
            # Auto-dismiss if configured
            if config.auto_dismiss and config.duration > 0:
                await asyncio.sleep(config.duration)
                await self._dismiss_feedback(update, context, user_id)
        
        except Exception as e:
            logger.error(f"Failed to show feedback: {e}")
    
    def _format_feedback_message(self, config: FeedbackConfig, template: Dict[str, str]) -> str:
        """Format feedback message with template."""
        emoji = template["emoji"]
        color = template["color"]
        prefix = template["prefix"]
        
        header = f"{color} *{prefix}*" if config.title == prefix else f"{color} *{config.title}*"
        
        return f"""
{header}
{emoji} {config.message}

━━━━━━━━━━━━━━━━━━━━
        """.strip()
    
    async def _show_simple_feedback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        config: FeedbackConfig
    ) -> None:
        """Show simple feedback message."""
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=text,
                parse_mode="Markdown"
            )
    
    async def _show_progress_feedback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        config: FeedbackConfig
    ) -> None:
        """Show progress feedback with steps."""
        if not config.progress_steps:
            return
        
        total_steps = len(config.progress_steps)
        
        for i, step in enumerate(config.progress_steps):
            progress_percentage = ((i + 1) / total_steps) * 100
            progress_bar = self._create_progress_bar(progress_percentage)
            
            progress_text = f"""
📊 *{config.title}*
{progress_bar} {progress_percentage:.0f}%

⏳ {step}...

━━━━━━━━━━━━━━━━━━━━
            """.strip()
            
            try:
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        text=progress_text,
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.edit_text(
                        text=progress_text,
                        parse_mode="Markdown"
                    )
                
                # Simulate step processing time
                await asyncio.sleep(config.duration / total_steps)
            
            except Exception as e:
                logger.warning(f"Progress update failed: {e}")
    
    def _create_progress_bar(self, percentage: float, width: int = 15) -> str:
        """Create visual progress bar."""
        filled = int((percentage / 100) * width)
        empty = width - filled
        return "▰" * filled + "▱" * empty
    
    async def _dismiss_feedback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
    ) -> None:
        """Dismiss active feedback."""
        if user_id in self.active_feedbacks:
            del self.active_feedbacks[user_id]
        
        # Could implement fade-out animation here
        logger.debug(f"Dismissed feedback for user {user_id}")
    
    async def show_success(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: str,
        title: str = "Success!",
        duration: float = 2.0
    ) -> None:
        """Show success feedback."""
        config = FeedbackConfig(
            type=FeedbackType.SUCCESS,
            title=title,
            message=message,
            duration=duration
        )
        await self.show_feedback(update, context, config)
    
    async def show_error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: str,
        title: str = "Error!",
        duration: float = 4.0
    ) -> None:
        """Show error feedback."""
        config = FeedbackConfig(
            type=FeedbackType.ERROR,
            title=title,
            message=message,
            duration=duration
        )
        await self.show_feedback(update, context, config)
    
    async def show_loading(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: str = "Processing your request...",
        title: str = "Loading...",
        steps: Optional[List[str]] = None
    ) -> None:
        """Show loading feedback with optional progress steps."""
        config = FeedbackConfig(
            type=FeedbackType.LOADING,
            title=title,
            message=message,
            duration=0,  # Manual dismissal
            auto_dismiss=False,
            show_progress=bool(steps),
            progress_steps=steps
        )
        await self.show_feedback(update, context, config)
    
    async def show_warning(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: str,
        title: str = "Warning!",
        duration: float = 3.0
    ) -> None:
        """Show warning feedback."""
        config = FeedbackConfig(
            type=FeedbackType.WARNING,
            title=title,
            message=message,
            duration=duration
        )
        await self.show_feedback(update, context, config)


class InteractionFeedback:
    """Provides immediate feedback for user interactions."""
    
    def __init__(self, button_manager: ButtonManager, feedback_manager: VisualFeedbackManager):
        self.button_manager = button_manager
        self.feedback_manager = feedback_manager
    
    async def handle_button_press(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Provide immediate feedback for button press."""
        # Update button to loading state
        self.button_manager.update_button_state(callback_data, ButtonState.LOADING)
        
        # Show brief loading feedback
        query = update.callback_query
        if query:
            await query.answer("Processing...")
    
    async def handle_successful_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str,
        success_message: str
    ) -> None:
        """Handle successful action completion."""
        # Update button to success state
        self.button_manager.update_button_state(callback_data, ButtonState.SUCCESS)
        
        # Show success feedback
        await self.feedback_manager.show_success(update, context, success_message)
    
    async def handle_failed_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str,
        error_message: str
    ) -> None:
        """Handle failed action."""
        # Update button to error state
        self.button_manager.update_button_state(callback_data, ButtonState.ERROR)
        
        # Show error feedback
        await self.feedback_manager.show_error(update, context, error_message)
    
    async def show_confirmation_dialog(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        title: str,
        message: str,
        confirm_callback: str,
        cancel_callback: str = "cancel"
    ) -> None:
        """Show confirmation dialog with custom buttons."""
        dialog_text = f"""
❓ *{title}*

{message}

Are you sure you want to continue?
        """.strip()
        
        # Create confirmation buttons
        grid = self.button_manager.create_confirmation_buttons(confirm_callback, cancel_callback)
        keyboard = self.button_manager.build_keyboard(grid)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=dialog_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=dialog_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )


class HapticFeedback:
    """Simulates haptic feedback through visual and textual cues."""
    
    @staticmethod
    async def vibrate_light(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Simulate light vibration feedback."""
        if update.callback_query:
            await update.callback_query.answer("✨")
    
    @staticmethod
    async def vibrate_medium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Simulate medium vibration feedback."""
        if update.callback_query:
            await update.callback_query.answer("⚡")
    
    @staticmethod
    async def vibrate_heavy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Simulate heavy vibration feedback."""
        if update.callback_query:
            await update.callback_query.answer("💥")
    
    @staticmethod
    async def success_haptic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Success haptic feedback."""
        if update.callback_query:
            await update.callback_query.answer("🎉 Success!")
    
    @staticmethod
    async def error_haptic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Error haptic feedback."""
        if update.callback_query:
            await update.callback_query.answer("❌ Error")