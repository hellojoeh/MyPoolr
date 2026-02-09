"""Callback query handlers for MyPoolr Telegram Bot."""

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from loguru import logger

from utils.button_manager import ButtonManager
from utils.state_manager import StateManager, ConversationState
from utils.feedback_system import VisualFeedbackManager, InteractionFeedback
from utils.formatters import MessageFormatter, EmojiHelper

# Import member management handlers
from .member_management import (
    handle_manage_members,
    handle_view_member_list,
    handle_invite_members,
    handle_security_status,
    handle_member_stats,
    handle_manage_invitations,
    handle_member_detail
)

# Import contribution confirmation handlers  
from .contribution_confirmation import (
    handle_contribution_dashboard,
    handle_pay_contribution,
    handle_confirm_payment,
    handle_recipient_confirmation,
    handle_payment_completed,
    handle_payment_schedule,
    handle_payment_history,
    handle_contribution_tracking,
    handle_upload_receipt
)

# Import tier upgrade handlers
from .tier_upgrade import (
    handle_tier_upgrade_main,
    handle_tier_selection,
    handle_payment_initiation,
    handle_payment_success,
    handle_tier_comparison,
    handle_upgrade_status_tracking,
    handle_feature_unlock_celebration
)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks with comprehensive navigation system."""
    query = update.callback_query
    await query.answer()
    
    # Get managers from context
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    
    if not button_manager or not state_manager:
        await query.edit_message_text("⚠️ Bot is initializing. Please try again.")
        return
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Button callback: {callback_data} from user {user_id}")
    
    # Handle navigation callbacks
    if callback_data == "main_menu":
        await handle_main_menu(update, context)
    elif callback_data == "my_groups":
        await handle_my_groups(update, context)
    elif callback_data == "create_mypoolr":
        await handle_create_mypoolr(update, context)
    elif callback_data == "join_via_link":
        await handle_join_via_link(update, context)
    elif callback_data == "upgrade_tier":
        await handle_upgrade_tier(update, context)
    elif callback_data == "help_main":
        await handle_help_main(update, context)
    elif callback_data == "settings":
        await handle_settings(update, context)
    elif callback_data.startswith("help_"):
        await handle_help_section(update, context, callback_data)
    elif callback_data == "contact_support":
        await handle_contact_support(update, context)
    elif callback_data == "pending_payments":
        await handle_pending_payments(update, context)
    elif callback_data == "my_schedule":
        await handle_my_schedule(update, context)
    elif callback_data.startswith("join_invitation:"):
        await handle_join_invitation(update, context, callback_data)
    # Member management callbacks
    elif callback_data == "manage_members":
        await handle_manage_members(update, context)
    elif callback_data == "view_member_list":
        await handle_view_member_list(update, context)
    elif callback_data == "invite_members":
        await handle_invite_members(update, context)
    elif callback_data == "security_status":
        await handle_security_status(update, context)
    elif callback_data == "member_stats":
        await handle_member_stats(update, context)
    elif callback_data == "manage_invitations":
        await handle_manage_invitations(update, context)
    elif callback_data.startswith("member_detail:"):
        await handle_member_detail(update, context)
    # Contribution confirmation callbacks
    elif callback_data == "contribution_dashboard" or callback_data == "pending_payments":
        await handle_contribution_dashboard(update, context)
    elif callback_data.startswith("pay_contribution:"):
        await handle_pay_contribution(update, context)
    elif callback_data.startswith("confirm_payment:"):
        await handle_confirm_payment(update, context)
    elif callback_data == "recipient_confirmation":
        await handle_recipient_confirmation(update, context)
    elif callback_data == "payment_completed":
        await handle_payment_completed(update, context)
    elif callback_data == "payment_schedule" or callback_data == "my_schedule":
        await handle_payment_schedule(update, context)
    elif callback_data == "payment_history":
        await handle_payment_history(update, context)
    elif callback_data == "contribution_tracking":
        await handle_contribution_tracking(update, context)
    elif callback_data.startswith("upload_receipt:"):
        await handle_upload_receipt(update, context)
    # Tier upgrade callbacks
    elif callback_data == "upgrade_tier":
        await handle_tier_upgrade_main(update, context)
    elif callback_data.startswith("select_tier:"):
        await handle_tier_selection(update, context)
    elif callback_data.startswith("initiate_payment:"):
        await handle_payment_initiation(update, context)
    elif callback_data == "payment_success":
        await handle_payment_success(update, context)
    elif callback_data == "compare_tiers":
        await handle_tier_comparison(update, context)
    elif callback_data == "upgrade_status":
        await handle_upgrade_status_tracking(update, context)
    elif callback_data == "feature_celebration":
        await handle_feature_unlock_celebration(update, context)
    else:
        # Check for registered callbacks
        callback_func = button_manager.get_callback(callback_data)
        if callback_func:
            await callback_func(update, context)
        else:
            # Default response for unhandled callbacks
            await query.edit_message_text(
                "🔧 This feature is coming soon!\n\n"
                f"Callback: `{callback_data}`",
                parse_mode="Markdown"
            )


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main menu navigation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    welcome_text = f"""
**MyPoolr**

Welcome back, {MessageFormatter.escape_markdown(user.first_name)}.

*What would you like to do?*
    """.strip()
    
    # Create main menu buttons
    grid = button_manager.create_grid(max_buttons_per_row=2)
    grid.add_row([
        button_manager.create_button("Create MyPoolr", "create_mypoolr"),
        button_manager.create_button("My Groups", "my_groups")
    ])
    grid.add_row([
        button_manager.create_button("Join via Link", "join_via_link"),
        button_manager.create_button("Upgrade Tier", "upgrade_tier")
    ])
    grid.add_row([
        button_manager.create_button("Help", "help_main"),
        button_manager.create_button("Settings", "settings")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=welcome_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle my groups display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    # This would normally fetch from backend API
    groups_text = f"""
👥 *My MyPoolr Groups*

📊 *Active Groups (2):*

🎯 **Office Savings**
💰 KES 5,000 • 📅 Weekly • 👥 8/10
📍 Your turn: Next week

🎯 **Family Circle** 
💰 KES 2,000 • 📅 Monthly • 👥 5/6
📍 Your turn: Position #3

💡 *Quick Stats:*
• Total contributed this month: KES 14,000
• Next payment due: Tomorrow
• Security deposits: All paid ✅
    """.strip()
    
    # Create group action buttons
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🎯 Office Savings", "group:office_savings", emoji="🎯"),
        button_manager.create_button("🎯 Family Circle", "group:family_circle", emoji="🎯")
    ])
    grid.add_row([
        button_manager.create_button("➕ Create New", "create_mypoolr", emoji="➕"),
        button_manager.create_button("🔗 Join Another", "join_via_link", emoji="🔗")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=groups_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_create_mypoolr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle MyPoolr creation initiation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    # Start creation conversation
    if state_manager:
        state_manager.start_conversation(user_id, ConversationState.CREATING_MYPOOLR)
    
    create_text = f"""
🚀 *Create New MyPoolr*

Let's set up your savings group! This will take just a few minutes.

📋 *What we'll need:*
• Group name and description
• Contribution amount and frequency  
• Member limit and country
• Your tier selection

✨ *Benefits:*
• Bulletproof security with no-loss guarantee
• Automated rotation management
• Two-party confirmation system
• Real-time notifications

Ready to start?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🎯 Start Setup", "start_mypoolr_creation", emoji="🎯")
    ])
    grid.add_row([
        button_manager.create_button("📖 Learn More", "learn_mypoolr", emoji="📖"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=create_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_join_via_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle joining via invitation link."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    join_text = f"""
🔗 *Join MyPoolr via Invitation*

To join a MyPoolr group, you'll need an invitation link from the group admin.

*Two ways to join:*

1️⃣ **Invitation Link**
   Tap the link shared by your admin
   
2️⃣ **Invitation Code**
   Enter code format: MYPOOLR-XXXXX-XXXXX

*What happens next:*
• Complete member registration
• Pay security deposit for protection
• Get added to rotation schedule
• Start contributing when it's time!

🔒 *Security Note:*
Security deposits protect all members and ensure no one loses money.
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📝 Enter Code", "enter_invitation_code", emoji="📝")
    ])
    grid.add_row([
        button_manager.create_button("❓ How it Works", "help_joining", emoji="❓"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=join_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_upgrade_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tier upgrade display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    tier_text = f"""
💎 *Upgrade Your Tier*

*Current Tier:* Starter (Free)

🌟 **Available Upgrades:**

⭐ **Essential - $2/month**
• 3 MyPoolr groups
• 25 members per group
• Priority support
• Advanced notifications

⭐⭐ **Advanced - $5/month**
• 10 MyPoolr groups  
• 50 members per group
• Custom rotation schedules
• Detailed analytics
• Export reports

⭐⭐⭐ **Extended - $10/month**
• Unlimited MyPoolr groups
• Unlimited members
• White-label branding
• API access
• Dedicated support

💳 *Payment via M-Pesa STK Push*
    """.strip()
    
    # Create tier selection buttons
    tiers = [
        {"id": "essential", "name": "Essential", "price": 2, "stars": 1},
        {"id": "advanced", "name": "Advanced", "price": 5, "stars": 2},
        {"id": "extended", "name": "Extended", "price": 10, "stars": 3}
    ]
    
    grid = button_manager.create_tier_selection_buttons(tiers)
    
    # Add navigation
    grid.add_row([
        button_manager.create_button("📊 Compare Features", "compare_tiers", emoji="📊"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=tier_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_help_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main help display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    help_text = f"""
❓ *MyPoolr Help Center*

Welcome to the help center! What do you need assistance with?

📚 *Popular Topics:*
• Getting started with MyPoolr
• Creating your first group
• Understanding security deposits
• Managing contributions
• Tier features and upgrades

💬 *Need Personal Help?*
Our support team is available 24/7 to assist you.
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🚀 Getting Started", "help_getting_started", emoji="🚀"),
        button_manager.create_button("🎯 Creating Groups", "help_creating", emoji="🎯")
    ])
    grid.add_row([
        button_manager.create_button("🔒 Security & Safety", "help_security", emoji="🔒"),
        button_manager.create_button("💰 Contributions", "help_contributions", emoji="💰")
    ])
    grid.add_row([
        button_manager.create_button("💎 Tiers & Features", "help_tiers", emoji="💎"),
        button_manager.create_button("🔧 Troubleshooting", "help_troubleshoot", emoji="🔧")
    ])
    grid.add_row([
        button_manager.create_button("💬 Contact Support", "contact_support", emoji="💬"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=help_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    settings_text = f"""
⚙️ *MyPoolr Settings*

*Account Information:*
• Name: {MessageFormatter.escape_markdown(update.effective_user.first_name)}
• Tier: Starter (Free)
• Member since: January 2024

*Preferences:*
• 🔔 Notifications: Enabled
• 🌍 Language: English
• 💱 Currency: KES (Kenyan Shilling)
• ⏰ Timezone: EAT (UTC+3)

*Privacy & Security:*
• 🔒 Two-factor authentication: Disabled
• 📱 Phone verification: Verified
• 🔐 Security deposits: Auto-calculated
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔔 Notifications", "settings_notifications", emoji="🔔"),
        button_manager.create_button("🌍 Language", "settings_language", emoji="🌍")
    ])
    grid.add_row([
        button_manager.create_button("🔒 Security", "settings_security", emoji="🔒"),
        button_manager.create_button("💱 Currency", "settings_currency", emoji="💱")
    ])
    grid.add_row([
        button_manager.create_button("📊 Export Data", "export_data", emoji="📊"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=settings_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_help_section(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle specific help sections."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    section = callback_data.replace("help_", "")
    
    help_content = {
        "getting_started": {
            "title": "🚀 Getting Started",
            "content": """
*Welcome to MyPoolr!*

MyPoolr is a digital platform for managing savings groups (chamas) with complete security and transparency.

*Quick Start Steps:*
1. Create or join a MyPoolr group
2. Pay security deposit for protection
3. Make contributions when it's your turn
4. Receive your payout when scheduled
5. Complete the cycle and get deposits back

*Key Benefits:*
• No-loss guarantee protects your money
• Automated rotation management
• Two-party confirmation prevents disputes
• Real-time notifications keep you updated

Ready to create your first group?
            """
        },
        "security": {
            "title": "🔒 Security & Safety",
            "content": """
*Your Money is 100% Protected*

MyPoolr uses a bulletproof security system:

*Security Deposits:*
• Everyone pays upfront to cover potential losses
• Calculated to protect all other members
• Returned when cycle completes successfully

*No-Loss Guarantee:*
• If someone defaults, their deposit covers it
• No member ever loses their own money
• Mathematical protection against all scenarios

*Account Lock-in:*
• After receiving payout, you can't leave early
• Ensures everyone completes their obligations
• Prevents hit-and-run scenarios

*Two-Party Confirmation:*
• Both sender and recipient must confirm payments
• Prevents disputes and misunderstandings
• Creates transparent audit trail
            """
        },
        "contributions": {
            "title": "💰 Contributions",
            "content": """
*How Contributions Work*

*Making Payments:*
1. Get notification when it's time to contribute
2. Send money directly to the recipient
3. Confirm payment in the bot
4. Recipient confirms receipt
5. Payment is recorded automatically

*Payment Methods:*
• M-Pesa (Kenya)
• Bank transfer
• Cash (confirm with recipient)
• Other mobile money services

*Deadlines & Reminders:*
• 24-hour deadline for contributions
• Automatic reminders sent
• Late payments trigger default process
• Security deposits cover missed payments

*Confirmation Process:*
Both parties must confirm to complete the transaction.
            """
        }
    }
    
    content = help_content.get(section, {
        "title": "❓ Help Topic",
        "content": "This help section is coming soon!"
    })
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("⬅️ Back to Help", "help_main", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=f"{content['title']}\n\n{content['content'].strip()}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle contact support."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    support_text = f"""
💬 *Contact MyPoolr Support*

Our support team is here to help you 24/7!

*Contact Methods:*

📧 **Email Support**
support@mypoolr.com
Response time: 2-4 hours

💬 **Telegram Support**
@mypoolr_support
Response time: 30 minutes

📞 **Phone Support** (Premium tiers)
+254-XXX-XXXXXX
Available: 9 AM - 6 PM EAT

*Before contacting support:*
• Check our help center first
• Have your user ID ready: `{update.effective_user.id}`
• Describe your issue clearly

We're committed to resolving your issues quickly!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📧 Email Support", "email_support", emoji="📧"),
        button_manager.create_button("💬 Telegram Support", "telegram_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("❓ Help Center", "help_main", emoji="❓"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=support_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pending payments display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    payments_text = f"""
💰 *Pending Payments*

*Urgent - Due Today:*

🔴 **Office Savings**
Amount: KES 5,000
Recipient: John Doe
Due: In 2 hours
Status: Not paid

*Upcoming This Week:*

🟡 **Family Circle**
Amount: KES 2,000  
Recipient: Mary Smith
Due: In 3 days
Status: Scheduled

*Payment Instructions:*
1. Send money to recipient via M-Pesa
2. Tap "Confirm Payment" below
3. Wait for recipient confirmation
4. Payment recorded automatically
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💳 Pay Office Savings", "pay_office_savings", emoji="💳")
    ])
    grid.add_row([
        button_manager.create_button("📅 View Schedule", "my_schedule", emoji="📅"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=payments_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_my_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle schedule display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    schedule_text = f"""
📅 *My Rotation Schedule*

*Office Savings (Weekly):*
• Week 1: ✅ John Doe (Completed)
• Week 2: ✅ Mary Smith (Completed)  
• Week 3: 🔄 **Your Turn** (Next week!)
• Week 4: ⏳ Alice Johnson
• Week 5: ⏳ Bob Wilson

*Family Circle (Monthly):*
• Jan: ✅ Mom (Completed)
• Feb: ✅ Dad (Completed)
• Mar: 🔄 Sister (Current)
• Apr: ⏳ **Your Turn**
• May: ⏳ Brother

*Summary:*
• Next payout: Office Savings (7 days)
• Next contribution: Family Circle (today)
• Total expected: KES 7,000 this month
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💰 Pending Payments", "pending_payments", emoji="💰"),
        button_manager.create_button("📊 Full Report", "full_report", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=schedule_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_join_invitation(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle joining via invitation link."""
    invitation_id = callback_data.replace("join_invitation:", "")
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    # This would normally fetch invitation details from backend
    join_text = f"""
🎯 *Join MyPoolr Group*

*Invitation Details:*
Group: "Office Savings"
Admin: John Doe
Contribution: KES 5,000
Frequency: Weekly
Members: 7/10

*Security Deposit Required:*
Amount: KES 15,000
Purpose: Protects all members from losses
Returned: When cycle completes

*What happens next:*
1. Complete member registration
2. Pay security deposit
3. Get added to rotation schedule
4. Start contributing when it's time!

Ready to join this group?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("✅ Join Group", f"confirm_join:{invitation_id}", emoji="✅")
    ])
    grid.add_row([
        button_manager.create_button("📖 Learn More", "learn_security", emoji="📖"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=join_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


def setup_callback_handlers(application) -> None:
    """Set up callback query handlers."""
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Callback handlers registered")