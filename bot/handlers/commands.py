"""Command handlers for MyPoolr Telegram Bot."""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from loguru import logger

from utils.button_manager import ButtonManager
from utils.state_manager import StateManager, ConversationState
from utils.ui_components import UIContext, InteractiveCard, NotificationBanner
from utils.feedback_system import VisualFeedbackManager
from utils.formatters import EmojiHelper, MessageFormatter
from utils.backend_client import BackendClient


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with beautiful welcome interface and deep linking."""
    user = update.effective_user
    user_id = user.id
    
    # Get managers from context
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    
    if not button_manager or not state_manager:
        await update.message.reply_text("⚠️ Bot is initializing. Please try again in a moment.")
        return
    
    # Check for deep linking (invitation links)
    deep_link_param = None
    if context.args:
        deep_link_param = context.args[0]
        logger.info(f"Deep link detected: {deep_link_param}")
    
    # Clear any existing conversation state
    state_manager.end_conversation(user_id)
    
    # Create welcome message
    welcome_text = f"""
**MyPoolr**

Welcome, {MessageFormatter.escape_markdown(user.first_name)}.

*Secure savings groups with bulletproof protection*

━━━━━━━━━━━━━━━━━━━━

**What you can do:**
• Create and manage savings groups
• Join groups via invitation links  
• Track contributions with dual confirmation
• Upgrade to premium tiers
• Enjoy complete financial security

Ready to begin?
    """.strip()
    
    # Create main menu buttons
    grid = button_manager.create_grid(max_buttons_per_row=2)
    
    # Handle deep linking for invitations
    if deep_link_param and deep_link_param.startswith("invite_"):
        invitation_id = deep_link_param.replace("invite_", "")
        grid.add_row([
            button_manager.create_button("Join MyPoolr", f"join_invitation:{invitation_id}")
        ])
        grid.add_row([
            button_manager.create_button("Create New Group", "create_mypoolr"),
            button_manager.create_button("My Groups", "my_groups")
        ])
    else:
        # Standard main menu
        grid.add_row([
            button_manager.create_button("Create MyPoolr", "create_mypoolr"),
            button_manager.create_button("My Groups", "my_groups")
        ])
        grid.add_row([
            button_manager.create_button("Join via Link", "join_via_link"),
            button_manager.create_button("Upgrade Tier", "upgrade_tier")
        ])
    
    # Add utility buttons
    grid.add_row([
        button_manager.create_button("Help", "help_main"),
        button_manager.create_button("Settings", "settings")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with contextual guidance."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    help_text = f"""
**MyPoolr Help**

*Available Commands:*
/start - Main menu
/help - Show this help
/status - Your dashboard
/create - Create new group
/join - Join via invitation

━━━━━━━━━━━━━━━━━━━━

**Quick Guide:**

**Creating a MyPoolr:**
1. Select "Create MyPoolr"
2. Follow setup steps
3. Invite members
4. Start rotations

**Joining a MyPoolr:**
1. Use invitation link
2. Complete registration
3. Pay security deposit
4. Wait for your turn

**Making Contributions:**
1. Get payment notification
2. Send money to recipient
3. Confirm payment
4. Wait for recipient confirmation

**Security Features:**
• Security deposits protect all members
• Dual confirmation prevents disputes
• No-loss guarantee ensures safety
• Account lock prevents early exits

**Premium Tiers:**
• Starter: Free (1 group, 10 members)
• Essential: $2/mo (3 groups, 25 members)
• Advanced: $5/mo (10 groups, 50 members)
• Extended: $10/mo (unlimited)

Need more help? Contact @mypoolr_support
    """.strip()
    
    # Create help navigation buttons
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("User Guide", "help_guide"),
        button_manager.create_button("Troubleshooting", "help_troubleshoot")
    ])
    grid.add_row([
        button_manager.create_button("Contact Support", "contact_support"),
        button_manager.create_button("Main Menu", "main_menu")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.message.reply_text(
        text=help_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command to show user's current status."""
    user_id = update.effective_user.id
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    # This would normally fetch from backend API
    # For now, showing placeholder status
    status_text = f"""
📊 *Your MyPoolr Status*

👥 *Active Groups:* 2
💰 *Pending Contributions:* 1
🎯 *Next Rotation:* Tomorrow
💎 *Current Tier:* Starter (Free)

⏳ *Recent Activity:*
• Confirmed payment to John - KES 5,000
• Joined "Office Savings" group
• Security deposit paid for "Family Circle"

🔔 *Notifications:*
• Payment due in 2 hours for "Office Savings"
• Your turn in "Family Circle" starts Monday
    """.strip()
    
    # Create status action buttons
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💰 Pending Payments", "pending_payments", emoji="💰"),
        button_manager.create_button("📅 My Schedule", "my_schedule", emoji="📅")
    ])
    grid.add_row([
        button_manager.create_button("📊 Full Report", "full_report", emoji="📊"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.message.reply_text(
        text=status_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create command for quick MyPoolr creation."""
    user_id = update.effective_user.id
    state_manager: StateManager = context.bot_data.get("state_manager")
    
    if state_manager:
        # Start MyPoolr creation conversation
        state_manager.start_conversation(user_id, ConversationState.CREATING_MYPOOLR)
    
    # Redirect to create MyPoolr flow (will be implemented in subtask 1.4)
    await update.message.reply_text(
        "🚀 Starting MyPoolr creation wizard...\n\n"
        "This feature will be fully implemented in the next phase!"
    )


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /join command for quick group joining."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    join_text = f"""
🔗 *Join a MyPoolr Group*

Enter your invitation code or use the link shared by your group admin.

*Format:* MYPOOLR-XXXXX-XXXXX

Or tap the button below to paste an invitation link:
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📋 Paste Invitation Link", "paste_invitation", emoji="📋")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.message.reply_text(
        text=join_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


def setup_command_handlers(application) -> None:
    """Set up command handlers."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("create", create_command))
    application.add_handler(CommandHandler("join", join_command))
    
    logger.info("Command handlers registered")