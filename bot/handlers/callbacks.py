"""Callback query handlers for MyPoolr Telegram Bot."""

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from loguru import logger

from utils.button_manager import ButtonManager
from utils.state_manager import StateManager, ConversationState
from utils.feedback_system import VisualFeedbackManager, InteractionFeedback
from utils.formatters import MessageFormatter, EmojiHelper
from utils.backend_client import BackendClient

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
    
    # Handle conversation-related callbacks that fell through
    # (when user is not in active conversation state)
    conversation_callbacks = {
        'cancel_creation', 'confirm_create', 'edit_details',
        'start_mypoolr_creation'
    }
    conversation_prefixes = ('back_to_', 'country:', 'frequency:', 'tier:', 'members:')
    
    if callback_data in conversation_callbacks or callback_data.startswith(conversation_prefixes):
        logger.warning(f"Conversation callback fell through: {callback_data}")
        # Clear any stale state
        if state_manager:
            state_manager.end_conversation(user_id)
        # Return to main menu
        await handle_main_menu(update, context)
        return
    
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
    # MyPoolr management callbacks
    elif callback_data.startswith("share_link:"):
        await handle_share_link(update, context, callback_data)
    elif callback_data.startswith("manage_group:"):
        await handle_manage_group(update, context, callback_data)
    # Group selection callbacks
    elif callback_data.startswith("group:"):
        await handle_group_detail(update, context, callback_data)
    # Invitation handling callbacks
    elif callback_data == "paste_invitation":
        await handle_paste_invitation(update, context)
    elif callback_data.startswith("join_invitation:"):
        await handle_join_invitation(update, context, callback_data)
    elif callback_data.startswith("confirm_join:"):
        await handle_confirm_join(update, context, callback_data)
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
                "🔧 Feature not available!\n\n"
                "Please use the main menu to access available features.\n\n"
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
    backend_client: BackendClient = context.bot_data.get("backend_client")
    user_id = update.effective_user.id
    
    await update.callback_query.answer()
    
    try:
        # Fetch user's groups from backend
        result = await backend_client.get_member_groups(user_id)
        
        if not result.get('success'):
            await update.callback_query.edit_message_text(
                "❌ Unable to fetch your groups. Please try again.",
                parse_mode="Markdown"
            )
            return
        
        groups = result.get('groups', [])
        
        if not groups:
            # No groups yet
            groups_text = """
👥 *My MyPoolr Groups*

You haven't joined any groups yet!

*Get Started:*
• Create your own MyPoolr group
• Join an existing group with an invitation link

Ready to start saving together?
            """.strip()
            
            grid = button_manager.create_grid()
            grid.add_row([
                button_manager.create_button("➕ Create Group", "create_mypoolr", emoji="➕"),
                button_manager.create_button("🔗 Join Group", "join_via_link", emoji="🔗")
            ])
            grid.add_row([
                button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
            ])
        else:
            # Build groups list
            groups_list = []
            for group in groups:
                groups_list.append(
                    f"🎯 **{group['name']}**\n"
                    f"💰 KES {group['contribution_amount']:,} • "
                    f"📅 {group['rotation_frequency'].title()} • "
                    f"👥 {group['current_members']}/{group['member_limit']}\n"
                    f"📍 Your position: #{group['member_position']}"
                )
            
            groups_text = f"""
👥 *My MyPoolr Groups*

📊 *Active Groups ({len(groups)}):*

{chr(10).join(groups_list)}

💡 *Quick Stats:*
• Total groups: {len(groups)}
• Active contributions: {sum(1 for g in groups if g.get('is_active'))}
            """.strip()
            
            # Create group buttons
            grid = button_manager.create_grid()
            for group in groups[:4]:  # Show max 4 groups
                grid.add_row([
                    button_manager.create_button(
                        f"🎯 {group['name'][:20]}", 
                        f"group:{group['id']}", 
                        emoji="🎯"
                    )
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
    
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while fetching your groups. Please try again.",
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
        "content": "This help section is not available. Please contact support for assistance."
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
    invitation_code = callback_data.replace("join_invitation:", "")
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    
    await update.callback_query.answer()
    
    try:
        # Validate invitation code with backend
        result = await backend_client.validate_invitation(invitation_code)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Invalid invitation code')
            await update.callback_query.edit_message_text(
                f"❌ *Invalid Invitation*\n\n{error_msg}",
                parse_mode="Markdown"
            )
            return
        
        mypoolr = result.get('mypoolr')
        
        join_text = f"""
🎯 *Join MyPoolr Group*

*Invitation Details:*
Group: "{mypoolr['name']}"
Admin: {mypoolr['admin_name']}
Contribution: KES {mypoolr['contribution_amount']:,}
Frequency: {mypoolr['rotation_frequency'].title()}
Members: {mypoolr['current_members']}/{mypoolr['member_limit']}

*Security Deposit Required:*
Amount: KES {mypoolr['security_deposit']:,}
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
            button_manager.create_button("✅ Join Group", f"confirm_join:{invitation_code}", emoji="✅")
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
    
    except Exception as e:
        logger.error(f"Error validating invitation: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while validating the invitation. Please try again.",
            parse_mode="Markdown"
        )


async def handle_share_link(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle share invitation link."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    invitation_code = callback_data.split(":", 1)[1]
    
    # Get bot username for the link
    bot = context.bot
    bot_username = (await bot.get_me()).username
    
    share_text = f"""
📤 **Share Your MyPoolr Group**

Invitation Code: `{invitation_code}`

Share this link with people you want to invite:
https://t.me/{bot_username}?start={invitation_code}

Or share the code directly and they can use:
/join {invitation_code}

*Tips for inviting members:*
• Only invite people you trust
• Explain the commitment required
• Make sure they understand the security deposit
• Verify they can afford the contributions

Ready to invite more members?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("👥 Manage Group", f"manage_group:{invitation_code}", emoji="👥")
    ])
    grid.add_row([
        button_manager.create_button("📋 My Groups", "my_groups", emoji="📋"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=share_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_manage_group(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle group management."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    mypoolr_id = callback_data.split(":", 1)[1]
    
    # Fetch actual group details from backend
    try:
        group_result = await backend_client.get_mypoolr(mypoolr_id)
        if group_result.get('success'):
            group_data = group_result.get('mypoolr', {})
            group_name = group_data.get('name', 'Unknown Group')
            member_count = group_data.get('current_members', 0)
            member_limit = group_data.get('member_limit', 0)
            contribution_amount = group_data.get('contribution_amount', 0)
            
            manage_text = f"""
👥 **Manage "{group_name}"**

📊 *Group Status:*
• Members: {member_count}/{member_limit}
• Contribution: KES {contribution_amount:,}
• Status: {group_data.get('status', 'Active').title()}

*Management Options:*
            """.strip()
        else:
            manage_text = f"""
👥 **Manage Group**

Unable to load group details. Please try again later.

*Available Options:*
            """.strip()
    except Exception as e:
        logger.error(f"Error fetching group details: {e}")
        manage_text = f"""
👥 **Manage Group**

Unable to load group details. Please try again later.

*Available Options:*
        """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("👥 View Members", "view_member_list", emoji="👥"),
        button_manager.create_button("💰 Contributions", "contribution_tracking", emoji="💰")
    ])
    grid.add_row([
        button_manager.create_button("📅 Schedule", "my_schedule", emoji="📅"),
        button_manager.create_button("📤 Share Link", f"share_link:{mypoolr_id}", emoji="📤")
    ])
    grid.add_row([
        button_manager.create_button("📋 My Groups", "my_groups", emoji="📋"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=manage_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_group_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle viewing group details."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    group_id = callback_data.split(":", 1)[1]
    user_id = update.effective_user.id
    
    await update.callback_query.answer()
    
    try:
        # Fetch group details from backend
        result = await backend_client.get_mypoolr_details(group_id)
        
        if not result.get('success'):
            await update.callback_query.edit_message_text(
                "❌ Unable to fetch group details. Please try again.",
                parse_mode="Markdown"
            )
            return
        
        group = result.get('mypoolr')
        invitation_code = result.get('invitation_code')
        
        detail_text = f"""
🎯 **{group['name']}**

*Group Information:*
• Code: `{invitation_code}`
• Status: {group['status'].title()}
• Members: {group['current_members']}/{group['member_limit']}
• Contribution: KES {group['contribution_amount']:,}
• Frequency: {group['rotation_frequency'].title()}

*Next Rotation:*
• Recipient: {group.get('next_recipient', 'TBD')}
• Date: {group.get('next_rotation_date', 'TBD')}

*Quick Actions:*
        """.strip()
        
        grid = button_manager.create_grid()
        grid.add_row([
            button_manager.create_button("💰 Make Payment", "pending_payments", emoji="💰"),
            button_manager.create_button("📅 View Schedule", "my_schedule", emoji="📅")
        ])
        grid.add_row([
            button_manager.create_button("👥 View Members", "view_member_list", emoji="👥"),
            button_manager.create_button("📤 Share Link", f"share_link:{invitation_code}", emoji="📤")
        ])
        grid.add_row([
            button_manager.create_button("⚙️ Manage Group", f"manage_group:{group_id}", emoji="⚙️")
        ])
        grid.add_row([
            button_manager.create_button("📋 My Groups", "my_groups", emoji="📋"),
            button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
        ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await update.callback_query.edit_message_text(
            text=detail_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error fetching group details: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while fetching group details. Please try again.",
            parse_mode="Markdown"
        )


async def handle_paste_invitation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle paste invitation callback - prompt user to send invitation code."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📋 *Paste Invitation Code*\n\n"
        "Please send me the invitation code you received.\n\n"
        "*Format:* MYPOOLR-XXXXX-XXXXX\n\n"
        "Or send the full invitation link.",
        parse_mode="Markdown"
    )
    # Store state to expect invitation code
    state_manager: StateManager = context.bot_data.get("state_manager")
    if state_manager:
        state_manager.start_conversation(update.effective_user.id, "awaiting_invitation_code")


async def handle_confirm_join(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle confirming to join a MyPoolr group."""
    invitation_code = callback_data.replace("confirm_join:", "")
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    user_id = update.effective_user.id
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "⏳ *Joining Group...*\n\nPlease wait while we process your request.",
        parse_mode="Markdown"
    )
    
    try:
        # Call backend to join the group
        join_data = {
            "invitation_code": invitation_code,
            "telegram_id": user_id,
            "full_name": update.effective_user.full_name,
            "username": update.effective_user.username
        }
        
        result = await backend_client.join_mypoolr(join_data)
        
        if result.get('success'):
            mypoolr_name = result.get('mypoolr_name', 'MyPoolr')
            security_deposit = result.get('security_deposit', 0)
            
            success_text = f"""
✅ *Successfully Joined!*

Welcome to "{mypoolr_name}"!

🔒 *Next Step: Security Deposit*
Amount: KES {security_deposit:,}

*Payment Instructions:*
1. Pay via M-Pesa to the group admin
2. Upload payment receipt
3. Wait for admin confirmation
4. You'll be added to the rotation schedule

*What is the security deposit?*
• Protects all members from losses
• Returned when the cycle completes
• Required before you can participate

Ready to pay your security deposit?
            """.strip()
            
            grid = button_manager.create_grid()
            grid.add_row([
                button_manager.create_button("💰 Pay Deposit", "pay_security_deposit", emoji="💰")
            ])
            grid.add_row([
                button_manager.create_button("📖 Learn More", "learn_security", emoji="📖"),
                button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
            ])
            
            keyboard = button_manager.build_keyboard(grid)
            
            await update.callback_query.edit_message_text(
                text=success_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            error_msg = result.get('error', 'Unable to join group')
            await update.callback_query.edit_message_text(
                f"❌ *Join Failed*\n\n{error_msg}\n\nPlease contact the group admin or try again.",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error joining MyPoolr: {e}")
        await update.callback_query.edit_message_text(
            "❌ *Join Failed*\n\n"
            "An error occurred while joining the group. "
            "Please try again or contact support.\n\n"
            f"Error: {str(e)}",
            parse_mode="Markdown"
        )


def setup_callback_handlers(application) -> None:
    """Set up callback query handlers."""
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Callback handlers registered")