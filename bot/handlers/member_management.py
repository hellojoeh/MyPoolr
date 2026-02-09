"""Member management interface handlers."""

from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from utils.button_manager import ButtonManager
from utils.state_manager import StateManager
from utils.ui_components import InteractiveCard, UIContext
from utils.formatters import MessageFormatter, EmojiHelper
from utils.feedback_system import VisualFeedbackManager


async def handle_manage_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle member management main interface."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    
    if query:
        await query.answer()
    
    # This would normally fetch from backend API
    # For now, showing mock data
    members_text = f"""
**Member Management**

*Group:* Office Savings
*Admin:* You
*Status:* Active • 7/10 members

━━━━━━━━━━━━━━━━━━━━

**Member Overview:**

**Active Members (5):**
• John Doe — Security paid, Position #1
• Mary Smith — Security paid, Position #2  
• Alice Johnson — Security paid, Position #3
• Bob Wilson — Security paid, Position #4
• Sarah Davis — Security paid, Position #5

**Pending Members (2):**
• Mike Brown — Security pending, Position #6
• Lisa White — Security pending, Position #7

**Invitation Status:**
• Active invitations: 3
• Invitation link: Active
• Spots remaining: 3
    """.strip()
    
    # Create member management buttons
    grid = button_manager.create_grid()
    
    # Member actions
    grid.add_row([
        button_manager.create_button("View Members", "view_member_list"),
        button_manager.create_button("Invite Members", "invite_members")
    ])
    
    # Admin actions
    grid.add_row([
        button_manager.create_button("Manage Invitations", "manage_invitations"),
        button_manager.create_button("Member Settings", "member_settings")
    ])
    
    # Security and status
    grid.add_row([
        button_manager.create_button("Security Status", "security_status"),
        button_manager.create_button("Member Stats", "member_stats")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("Main Menu", "main_menu")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    if query:
        await query.edit_message_text(
            text=members_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=members_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def handle_view_member_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle detailed member list view."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    member_list_text = f"""
👥 *Detailed Member List*

*Office Savings Group*

🟢 **John Doe** (Position #1)
├ Security: ✅ KES 15,000 paid
├ Status: Active, received payout
├ Phone: +254-XXX-XXXX
└ Joined: Jan 15, 2024

🟢 **Mary Smith** (Position #2)  
├ Security: ✅ KES 15,000 paid
├ Status: Active, awaiting turn
├ Phone: +254-XXX-XXXX
└ Joined: Jan 16, 2024

🟢 **Alice Johnson** (Position #3)
├ Security: ✅ KES 15,000 paid  
├ Status: Active, current recipient
├ Phone: +254-XXX-XXXX
└ Joined: Jan 17, 2024

🟡 **Mike Brown** (Position #6)
├ Security: ⏳ Pending payment
├ Status: Invited, not active
├ Phone: +254-XXX-XXXX
└ Invited: Jan 20, 2024

*Legend:*
🟢 Active • 🟡 Pending • 🔴 Issues
    """.strip()
    
    # Create member action buttons
    grid = button_manager.create_grid()
    
    # Individual member actions
    grid.add_row([
        button_manager.create_button("👤 John Doe", "member_detail:john", emoji="👤"),
        button_manager.create_button("👤 Mary Smith", "member_detail:mary", emoji="👤")
    ])
    
    grid.add_row([
        button_manager.create_button("👤 Alice Johnson", "member_detail:alice", emoji="👤"),
        button_manager.create_button("👤 Mike Brown", "member_detail:mike", emoji="👤")
    ])
    
    # Bulk actions
    grid.add_row([
        button_manager.create_button("📤 Export List", "export_members", emoji="📤"),
        button_manager.create_button("📧 Message All", "message_all_members", emoji="📧")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "manage_members", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=member_list_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_invite_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle member invitation interface."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    # Generate mock invitation details
    import random
    invitation_code = f"MYPOOLR-{random.randint(10000, 99999)}-{random.randint(10000, 99999)}"
    invitation_link = f"https://t.me/mypoolr_bot?start=invite_{invitation_code}"
    
    invite_text = f"""
📤 *Invite New Members*

*Current Group:* Office Savings
*Available Spots:* 3 remaining

🔗 *Invitation Link:*
{invitation_link}

📋 *Invitation Code:*
`{invitation_code}`

📱 *How to Share:*

1️⃣ **Direct Link**
   Copy and send the link above

2️⃣ **QR Code** 
   Generate QR code for easy scanning

3️⃣ **Manual Code**
   Share the invitation code

*What New Members Need:*
• Complete registration form
• Pay security deposit: KES 15,000
• Provide phone number for verification
• Accept group terms and conditions

⏰ *Invitation expires in 7 days*
    """.strip()
    
    # Create invitation action buttons
    grid = button_manager.create_grid()
    
    # Sharing options
    grid.add_row([
        button_manager.create_button("📋 Copy Link", f"copy_link:{invitation_code}", emoji="📋"),
        button_manager.create_button("📱 Generate QR", f"generate_qr:{invitation_code}", emoji="📱")
    ])
    
    # Social sharing
    grid.add_row([
        button_manager.create_button("💬 Share on WhatsApp", f"share_whatsapp:{invitation_code}", emoji="💬"),
        button_manager.create_button("📧 Send via Email", f"share_email:{invitation_code}", emoji="📧")
    ])
    
    # Management
    grid.add_row([
        button_manager.create_button("🔄 Generate New Link", "new_invitation_link", emoji="🔄"),
        button_manager.create_button("📊 Invitation Stats", "invitation_stats", emoji="📊")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "manage_members", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=invite_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_security_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle security deposit status tracking."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    security_text = f"""
🔒 *Security Deposit Status*

*Group:* Office Savings
*Required Deposit:* KES 15,000 per member

📊 *Payment Status:*

✅ **Paid (5 members):**
• John Doe - KES 15,000 ✅
• Mary Smith - KES 15,000 ✅  
• Alice Johnson - KES 15,000 ✅
• Bob Wilson - KES 15,000 ✅
• Sarah Davis - KES 15,000 ✅

⏳ **Pending (2 members):**
• Mike Brown - Not paid (3 days overdue)
• Lisa White - Not paid (1 day overdue)

💰 *Financial Summary:*
• Total collected: KES 75,000
• Total pending: KES 30,000
• Group protection: 100% for active members

🔐 *Security Features:*
• Deposits locked after payout received
• Auto-release when cycle completes
• Default protection: Fully covered
• No-loss guarantee: Active

⚠️ *Action Required:*
2 members need to pay security deposits
    """.strip()
    
    # Create security action buttons
    grid = button_manager.create_grid()
    
    # Pending actions
    grid.add_row([
        button_manager.create_button("📧 Remind Mike", "remind_member:mike", emoji="📧"),
        button_manager.create_button("📧 Remind Lisa", "remind_member:lisa", emoji="📧")
    ])
    
    # Management actions
    grid.add_row([
        button_manager.create_button("💰 Payment History", "payment_history", emoji="💰"),
        button_manager.create_button("🔄 Recalculate Deposits", "recalculate_deposits", emoji="🔄")
    ])
    
    # Admin actions
    grid.add_row([
        button_manager.create_button("⚠️ Remove Overdue", "remove_overdue_members", emoji="⚠️"),
        button_manager.create_button("📊 Security Report", "security_report", emoji="📊")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "manage_members", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=security_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def handle_member_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle individual member detail view."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    # Extract member ID from callback data
    member_id = query.data.replace("member_detail:", "")
    
    # Mock member data (would come from backend)
    member_data = {
        "john": {
            "name": "John Doe",
            "position": 1,
            "phone": "+254-XXX-XXXX",
            "security_paid": True,
            "security_amount": 15000,
            "has_received_payout": True,
            "payout_amount": 35000,
            "joined_date": "Jan 15, 2024",
            "status": "active",
            "contributions_made": 4,
            "contributions_pending": 0
        },
        "mike": {
            "name": "Mike Brown", 
            "position": 6,
            "phone": "+254-XXX-XXXX",
            "security_paid": False,
            "security_amount": 15000,
            "has_received_payout": False,
            "payout_amount": 0,
            "joined_date": "Jan 20, 2024",
            "status": "pending",
            "contributions_made": 0,
            "contributions_pending": 1
        }
    }
    
    member = member_data.get(member_id, member_data["john"])
    
    # Status indicators
    security_status = "✅ Paid" if member["security_paid"] else "⏳ Pending"
    payout_status = "✅ Received" if member["has_received_payout"] else "⏳ Waiting"
    status_emoji = {"active": "🟢", "pending": "🟡", "inactive": "🔴"}.get(member["status"], "⚪")
    
    member_detail_text = f"""
👤 *Member Details*

{status_emoji} **{MessageFormatter.escape_markdown(member['name'])}**

📋 *Basic Information:*
• Position: #{member['position']} in rotation
• Phone: {member['phone']}
• Joined: {member['joined_date']}
• Status: {member['status'].title()}

💰 *Financial Status:*
• Security Deposit: {security_status}
  Amount: {MessageFormatter.format_currency(member['security_amount'])}
• Payout Status: {payout_status}
  Amount: {MessageFormatter.format_currency(member['payout_amount'])}

📊 *Contribution History:*
• Completed: {member['contributions_made']} payments
• Pending: {member['contributions_pending']} payments
• Success Rate: {(member['contributions_made'] / max(member['contributions_made'] + member['contributions_pending'], 1) * 100):.0f}%

🔒 *Security Information:*
• Account locked: {"Yes" if member['has_received_payout'] else "No"}
• Can leave group: {"No" if member['has_received_payout'] else "Yes"}
• Default risk: {"Low" if member['security_paid'] else "High"}
    """.strip()
    
    # Create member action buttons
    grid = button_manager.create_grid()
    
    # Communication actions
    grid.add_row([
        button_manager.create_button("💬 Send Message", f"message_member:{member_id}", emoji="💬"),
        button_manager.create_button("📞 Call Member", f"call_member:{member_id}", emoji="📞")
    ])
    
    # Admin actions
    if not member["security_paid"]:
        grid.add_row([
            button_manager.create_button("📧 Remind Payment", f"remind_payment:{member_id}", emoji="📧"),
            button_manager.create_button("⚠️ Remove Member", f"remove_member:{member_id}", emoji="⚠️")
        ])
    else:
        grid.add_row([
            button_manager.create_button("📊 View History", f"member_history:{member_id}", emoji="📊"),
            button_manager.create_button("⚙️ Edit Details", f"edit_member:{member_id}", emoji="⚙️")
        ])
    
    # Position management
    grid.add_row([
        button_manager.create_button("🔄 Change Position", f"change_position:{member_id}", emoji="🔄"),
        button_manager.create_button("👑 Promote to Admin", f"promote_member:{member_id}", emoji="👑")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back to List", "view_member_list", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=member_detail_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_member_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle member statistics display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    stats_text = f"""
📊 *Member Statistics*

*Office Savings Group*

👥 *Membership Overview:*
• Total Members: 7
• Active Members: 5 (71%)
• Pending Members: 2 (29%)
• Available Spots: 3

💰 *Financial Metrics:*
• Security Deposits Collected: KES 75,000
• Security Deposits Pending: KES 30,000
• Collection Rate: 71%
• Average Deposit: KES 15,000

📈 *Performance Metrics:*
• On-time Payment Rate: 95%
• Member Retention: 100%
• Average Join Time: 2.3 days
• Group Completion Rate: 0% (ongoing)

🎯 *Rotation Progress:*
• Completed Rotations: 2/7 (29%)
• Current Recipient: Alice Johnson
• Next Recipient: Bob Wilson
• Estimated Completion: March 2024

⚠️ *Issues & Alerts:*
• 2 members with overdue security deposits
• 0 members with payment defaults
• 0 members requesting to leave

📅 *Timeline:*
• Group Created: January 10, 2024
• First Rotation: January 22, 2024
• Last Activity: Today
• Next Rotation: February 5, 2024
    """.strip()
    
    # Create stats action buttons
    grid = button_manager.create_grid()
    
    # Report actions
    grid.add_row([
        button_manager.create_button("📄 Export Report", "export_stats_report", emoji="📄"),
        button_manager.create_button("📊 Detailed Analytics", "detailed_analytics", emoji="📊")
    ])
    
    # Comparison and trends
    grid.add_row([
        button_manager.create_button("📈 Trends", "view_trends", emoji="📈"),
        button_manager.create_button("🔍 Compare Groups", "compare_groups", emoji="🔍")
    ])
    
    # Actions based on stats
    grid.add_row([
        button_manager.create_button("⚠️ Address Issues", "address_issues", emoji="⚠️"),
        button_manager.create_button("🎯 Optimize Group", "optimize_group", emoji="🎯")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "manage_members", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=stats_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_manage_invitations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle invitation management interface."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    invitations_text = f"""
🔗 *Invitation Management*

*Office Savings Group*

📤 *Active Invitations:*

🟢 **Primary Link** (Active)
├ Code: MYPOOLR-12345-67890
├ Created: Jan 20, 2024
├ Expires: Jan 27, 2024
├ Uses: 2/unlimited
└ Status: Active

🟡 **Backup Link** (Standby)
├ Code: MYPOOLR-98765-43210  
├ Created: Jan 18, 2024
├ Expires: Jan 25, 2024
├ Uses: 0/unlimited
└ Status: Standby

📊 *Invitation Statistics:*
• Total invitations sent: 15
• Successful joins: 7 (47%)
• Pending responses: 3
• Expired invitations: 5

⚙️ *Invitation Settings:*
• Auto-expire: 7 days
• Max uses per link: Unlimited
• Require admin approval: No
• Send welcome message: Yes

🔔 *Recent Activity:*
• Mike Brown joined via primary link (2 days ago)
• Lisa White clicked link but didn't join (1 day ago)
• 3 people viewed invitation but didn't click
    """.strip()
    
    # Create invitation management buttons
    grid = button_manager.create_grid()
    
    # Link management
    grid.add_row([
        button_manager.create_button("🔄 Generate New Link", "generate_new_invitation", emoji="🔄"),
        button_manager.create_button("🗑️ Deactivate Links", "deactivate_invitations", emoji="🗑️")
    ])
    
    # Settings and customization
    grid.add_row([
        button_manager.create_button("⚙️ Invitation Settings", "invitation_settings", emoji="⚙️"),
        button_manager.create_button("✏️ Custom Message", "custom_invitation_message", emoji="✏️")
    ])
    
    # Analytics and tracking
    grid.add_row([
        button_manager.create_button("📊 Invitation Analytics", "invitation_analytics", emoji="📊"),
        button_manager.create_button("👥 Track Responses", "track_invitation_responses", emoji="👥")
    ])
    
    # Bulk actions
    grid.add_row([
        button_manager.create_button("📧 Resend Invitations", "resend_invitations", emoji="📧"),
        button_manager.create_button("📱 Share via SMS", "share_via_sms", emoji="📱")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "manage_members", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=invitations_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# Register callback handlers for member management
def register_member_management_callbacks(button_manager: ButtonManager) -> None:
    """Register callback functions for member management."""
    
    # Main member management callbacks
    button_manager.register_callback("manage_members", handle_manage_members)
    button_manager.register_callback("view_member_list", handle_view_member_list)
    button_manager.register_callback("invite_members", handle_invite_members)
    button_manager.register_callback("security_status", handle_security_status)
    button_manager.register_callback("member_stats", handle_member_stats)
    button_manager.register_callback("manage_invitations", handle_manage_invitations)
    
    # Member detail callbacks (pattern-based, would need custom handling)
    # These would be handled in the main callback handler with pattern matching
    
    logger.info("Member management callbacks registered")