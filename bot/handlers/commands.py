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
    backend_client: BackendClient = context.bot_data.get("backend_client")
    
    # Fetch user status from backend API
    try:
        user_groups = await backend_client.get_user_mypoolrs(user_id)
        pending_contributions = await backend_client.get_pending_contributions(user_id)
        tier_info = await backend_client.get_admin_tier_info(user_id)
        
        active_groups = len(user_groups.get('mypoolrs', [])) if user_groups.get('success') else 0
        pending_count = len(pending_contributions.get('contributions', [])) if pending_contributions.get('success') else 0
        current_tier = tier_info.get('tier', 'starter') if tier_info.get('success') else 'starter'
        
        status_text = f"""
📊 *Your MyPoolr Status*

👥 *Active Groups:* {active_groups}
� *Pending Contributions:* {pending_count}
💎 *Current Tier:* {current_tier.title()}

Use the menu below to manage your groups and contributions.
        """.strip()
        
    except Exception as e:
        logger.error(f"Error fetching user status: {e}")
        status_text = f"""
📊 *Your MyPoolr Status*

Unable to fetch current status. Please try again later or contact support.

Use the menu below to access available features.
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


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /link command to link a Telegram group to a MyPoolr."""
    # Check if command is used in a group
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "⚠️ This command can only be used in a Telegram group.\n\n"
            "Please:\n"
            "1. Create a Telegram group\n"
            "2. Add this bot to the group\n"
            "3. Make the bot an admin\n"
            "4. Use /link <mypoolr_id> in the group"
        )
        return
    
    # Check if bot is admin
    bot_member = await update.effective_chat.get_member(context.bot.id)
    if bot_member.status not in ['administrator', 'creator']:
        await update.message.reply_text(
            "⚠️ Please make me an admin in this group first.\n\n"
            "I need admin rights to:\n"
            "• Send notifications\n"
            "• Manage group settings\n"
            "• Pin important messages"
        )
        return
    
    # Check if MyPoolr ID is provided
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "⚠️ Please provide the MyPoolr ID.\n\n"
            "Usage: /link <mypoolr_id>\n\n"
            "Example: /link 123e4567-e89b-12d3-a456-426614174000"
        )
        return
    
    mypoolr_id = context.args[0]
    telegram_group_id = update.effective_chat.id
    telegram_group_name = update.effective_chat.title
    user_id = update.effective_user.id
    
    backend_client: BackendClient = context.bot_data.get("backend_client")
    
    try:
        # Call backend to link the group
        result = await backend_client.link_telegram_group(
            mypoolr_id=mypoolr_id,
            telegram_group_id=telegram_group_id,
            telegram_group_name=telegram_group_name,
            linked_by=user_id
        )
        
        if result.get('success'):
            mypoolr_name = result.get('mypoolr_name', 'MyPoolr')
            await update.message.reply_text(
                f"✅ *Group Linked Successfully!*\n\n"
                f"This Telegram group is now linked to:\n"
                f"📊 {MessageFormatter.escape_markdown(mypoolr_name)}\n\n"
                f"*What's next:*\n"
                f"• Members can join using invitation links\n"
                f"• Bot will send notifications here\n"
                f"• Use /status to see group details\n"
                f"• Use /help for available commands",
                parse_mode="Markdown"
            )
        else:
            error_msg = result.get('message', result.get('error', 'Unknown error'))
            await update.message.reply_text(
                f"❌ *Linking Failed*\n\n{error_msg}\n\n"
                f"Please check:\n"
                f"• MyPoolr ID is correct\n"
                f"• You are the admin of the MyPoolr\n"
                f"• MyPoolr is not already linked",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error linking Telegram group: {e}")
        await update.message.reply_text(
            "❌ An error occurred while linking the group.\n\n"
            "Please try again or contact support."
        )


def setup_command_handlers(application) -> None:
    """Set up command handlers."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("create", create_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("link", link_command))
    
    logger.info("Command handlers registered")