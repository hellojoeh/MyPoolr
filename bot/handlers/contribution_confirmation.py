"""Contribution confirmation interface handlers."""

from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger
from datetime import datetime, timedelta

from utils.button_manager import ButtonManager
from utils.state_manager import StateManager, ConversationState
from utils.ui_components import InteractiveCard, UIContext, ProgressIndicator
from utils.formatters import MessageFormatter, EmojiHelper
from utils.feedback_system import VisualFeedbackManager


async def handle_contribution_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main contribution dashboard."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    
    if query:
        await query.answer()
    
    # Mock contribution data (would come from backend)
    dashboard_text = f"""
**Contribution Dashboard**

*Your Active Groups*

━━━━━━━━━━━━━━━━━━━━

**URGENT — Due Today**
Office Savings
• Amount: KES 5,000
• Recipient: Alice Johnson
• Due: In 2 hours
• Status: Not confirmed

**Due This Week**
Family Circle  
• Amount: KES 2,000
• Recipient: Mary Smith
• Due: In 3 days
• Status: Scheduled

**Recently Completed**
Office Savings
• Amount: KES 5,000  
• Recipient: John Doe
• Completed: 2 days ago
• Status: Confirmed by both parties

━━━━━━━━━━━━━━━━━━━━

**Quick Stats:**
• Pending payments: 2
• This month contributed: KES 14,000
• Success rate: 100%
• Average confirmation: 4 hours
    """.strip()
    
    # Create dashboard action buttons
    grid = button_manager.create_grid()
    
    # Urgent actions
    grid.add_row([
        button_manager.create_button("Pay Now (Office)", "pay_contribution:office_urgent")
    ])
    
    # Main actions
    grid.add_row([
        button_manager.create_button("All Contributions", "view_all_contributions"),
        button_manager.create_button("Payment Schedule", "payment_schedule")
    ])
    
    # History and tracking
    grid.add_row([
        button_manager.create_button("Payment History", "payment_history"),
        button_manager.create_button("Notification Settings", "notification_settings")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("Main Menu", "main_menu")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    if query:
        await query.edit_message_text(
            text=dashboard_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=dashboard_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def handle_pay_contribution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle contribution payment initiation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    # Extract contribution ID from callback data
    contribution_id = query.data.replace("pay_contribution:", "")
    
    # Mock contribution details
    contribution_data = {
        "office_urgent": {
            "group": "Office Savings",
            "amount": 5000,
            "currency": "KES",
            "recipient": "Alice Johnson",
            "recipient_phone": "+254-XXX-XXXX",
            "due_time": datetime.now() + timedelta(hours=2),
            "rotation_position": 3,
            "payment_methods": ["M-Pesa", "Bank Transfer", "Cash"]
        }
    }
    
    contrib = contribution_data.get(contribution_id, contribution_data["office_urgent"])
    
    # Calculate time remaining
    time_remaining = MessageFormatter.format_time_remaining(contrib["due_time"])
    
    payment_text = f"""
💸 *Make Contribution Payment*

*Group:* {contrib['group']}
*Rotation:* Position #{contrib['rotation_position']}

👤 *Recipient Details:*
• Name: {MessageFormatter.escape_markdown(contrib['recipient'])}
• Phone: {contrib['recipient_phone']}
• Amount: {MessageFormatter.format_currency(contrib['amount'], contrib['currency'])}

⏰ *Deadline:* {time_remaining}

📱 *Payment Methods:*

1️⃣ **M-Pesa (Recommended)**
   • Send to: {contrib['recipient_phone']}
   • Amount: {contrib['amount']}
   • Reference: Office Savings

2️⃣ **Bank Transfer**
   • Get bank details from recipient
   • Include reference: Office Savings

3️⃣ **Cash Payment**
   • Meet recipient in person
   • Get written receipt

🔄 *Next Steps:*
1. Make payment using preferred method
2. Tap "I've Paid" below
3. Wait for recipient confirmation
4. Payment recorded automatically

⚠️ *Important:* Both you and recipient must confirm for payment to be recorded.
    """.strip()
    
    # Create payment action buttons
    grid = button_manager.create_grid()
    
    # Payment confirmation
    grid.add_row([
        button_manager.create_button("✅ I've Paid", f"confirm_payment:{contribution_id}", emoji="✅")
    ])
    
    # Payment methods
    grid.add_row([
        button_manager.create_button("📱 M-Pesa Guide", f"mpesa_guide:{contribution_id}", emoji="📱"),
        button_manager.create_button("🏦 Bank Details", f"bank_details:{contribution_id}", emoji="🏦")
    ])
    
    # Communication
    grid.add_row([
        button_manager.create_button("💬 Contact Recipient", f"contact_recipient:{contribution_id}", emoji="💬"),
        button_manager.create_button("📸 Upload Receipt", f"upload_receipt:{contribution_id}", emoji="📸")
    ])
    
    # Help and navigation
    grid.add_row([
        button_manager.create_button("❓ Need Help", "contribution_help", emoji="❓"),
        button_manager.create_button("⬅️ Back", "contribution_dashboard", emoji="⬅️")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=payment_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment confirmation from sender."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    contribution_id = query.data.replace("confirm_payment:", "")
    
    confirmation_text = f"""
✅ *Payment Confirmation*

*Status:* Sender confirmed ✅

You've confirmed that you sent KES 5,000 to Alice Johnson for Office Savings.

🔄 *Waiting for Recipient Confirmation*

Alice Johnson will receive a notification to confirm receipt of your payment.

⏱️ *What happens next:*
1. Alice gets notification to confirm receipt
2. She has 24 hours to confirm
3. Once confirmed, payment is recorded
4. You'll get confirmation notification

📊 *Current Status:*
• Your confirmation: ✅ Completed
• Recipient confirmation: ⏳ Pending
• Payment recorded: ⏳ Waiting

💬 *If there are issues:*
• Contact Alice directly
• Use "Report Issue" if no response
• Admin can help resolve disputes

⏰ *Confirmation deadline:* 24 hours from now
    """.strip()
    
    # Create post-confirmation buttons
    grid = button_manager.create_grid()
    
    # Communication and tracking
    grid.add_row([
        button_manager.create_button("💬 Message Alice", "message_recipient:alice", emoji="💬"),
        button_manager.create_button("🔔 Remind Alice", "remind_recipient:alice", emoji="🔔")
    ])
    
    # Issue reporting
    grid.add_row([
        button_manager.create_button("⚠️ Report Issue", f"report_issue:{contribution_id}", emoji="⚠️"),
        button_manager.create_button("📞 Contact Admin", "contact_admin", emoji="📞")
    ])
    
    # Status and history
    grid.add_row([
        button_manager.create_button("📊 Track Status", f"track_payment:{contribution_id}", emoji="📊"),
        button_manager.create_button("📄 Payment Receipt", f"payment_receipt:{contribution_id}", emoji="📄")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("💰 My Contributions", "contribution_dashboard", emoji="💰"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=confirmation_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_recipient_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment confirmation from recipient side."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    # This would be called when recipient gets notification
    recipient_text = f"""
💰 *Confirm Payment Receipt*

*Group:* Office Savings
*From:* John Doe

You've received a payment confirmation request:

💸 *Payment Details:*
• Amount: KES 5,000
• Method: M-Pesa
• Reference: Office Savings
• Time: 30 minutes ago

✅ *Sender Status:* John confirmed he sent payment

🔍 *Please Verify:*
• Check your M-Pesa messages
• Confirm you received KES 5,000
• Verify sender is John Doe

⚠️ *Important:*
Only confirm if you actually received the money. False confirmations can cause disputes.

Did you receive this payment?
    """.strip()
    
    # Create recipient confirmation buttons
    grid = button_manager.create_grid()
    
    # Confirmation options
    grid.add_row([
        button_manager.create_button("✅ Yes, I Received It", "recipient_confirm_yes", emoji="✅"),
        button_manager.create_button("❌ No, Not Received", "recipient_confirm_no", emoji="❌")
    ])
    
    # Verification help
    grid.add_row([
        button_manager.create_button("📱 Check M-Pesa", "check_mpesa_messages", emoji="📱"),
        button_manager.create_button("💬 Contact Sender", "contact_sender", emoji="💬")
    ])
    
    # Issue reporting
    grid.add_row([
        button_manager.create_button("⚠️ Report Problem", "report_payment_problem", emoji="⚠️"),
        button_manager.create_button("❓ Need Help", "recipient_help", emoji="❓")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=recipient_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_payment_completed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle completed payment confirmation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    completion_text = f"""
🎉 *Payment Completed Successfully!*

*Group:* Office Savings
*Amount:* KES 5,000
*From:* John Doe → Alice Johnson

✅ *Confirmation Status:*
• Sender confirmed: ✅ John Doe
• Recipient confirmed: ✅ Alice Johnson
• Payment recorded: ✅ Completed
• Transaction ID: TXN-2024-001234

📊 *Transaction Summary:*
• Payment method: M-Pesa
• Confirmation time: 2 hours
• Success rate: 100%
• Group progress: 3/7 rotations complete

🔄 *Next Rotation:*
• Next recipient: Bob Wilson
• Your next payment: February 12, 2024
• Amount: KES 5,000

🏆 *Achievement Unlocked:*
• Perfect Payment Record
• Fast Confirmation (under 4 hours)
• Group Contributor Badge

Thank you for keeping Office Savings running smoothly!
    """.strip()
    
    # Create celebration and next action buttons
    grid = button_manager.create_grid()
    
    # Receipt and records
    grid.add_row([
        button_manager.create_button("📄 Download Receipt", "download_receipt", emoji="📄"),
        button_manager.create_button("📊 View Transaction", "view_transaction", emoji="📊")
    ])
    
    # Next actions
    grid.add_row([
        button_manager.create_button("📅 Next Payment", "next_payment_schedule", emoji="📅"),
        button_manager.create_button("🎯 Group Progress", "group_progress", emoji="🎯")
    ])
    
    # Social and sharing
    grid.add_row([
        button_manager.create_button("🎉 Share Success", "share_success", emoji="🎉"),
        button_manager.create_button("⭐ Rate Experience", "rate_experience", emoji="⭐")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("💰 My Contributions", "contribution_dashboard", emoji="💰"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=completion_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
async def handle_payment_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment schedule display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    schedule_text = f"""
📅 *Payment Schedule*

*Office Savings Group (Weekly)*

📊 *Rotation Progress:* 3/7 completed (43%)

✅ **Completed Rotations:**
• Week 1: John Doe (Jan 22) - ✅ All paid
• Week 2: Mary Smith (Jan 29) - ✅ All paid  
• Week 3: Alice Johnson (Feb 5) - 🔄 Current

⏳ **Upcoming Rotations:**
• Week 4: Bob Wilson (Feb 12) - Your payment due
• Week 5: Sarah Davis (Feb 19)
• Week 6: Mike Brown (Feb 26) - If security paid
• Week 7: Lisa White (Mar 5) - If security paid

💰 *Your Payment Schedule:*
• Next payment: February 12, 2024
• Amount: KES 5,000
• Recipient: Bob Wilson
• Days remaining: 7 days

🔔 *Reminder Settings:*
• 3 days before: ✅ Enabled
• 1 day before: ✅ Enabled  
• 6 hours before: ✅ Enabled
• Payment overdue: ✅ Enabled

📈 *Payment History:*
• Total contributed: KES 10,000
• Payments made: 2/2 (100%)
• Average confirmation time: 3.5 hours
• Perfect record: ✅ No missed payments
    """.strip()
    
    # Create schedule action buttons
    grid = button_manager.create_grid()
    
    # Schedule management
    grid.add_row([
        button_manager.create_button("🔔 Set Reminders", "set_payment_reminders", emoji="🔔"),
        button_manager.create_button("📅 Add to Calendar", "add_to_calendar", emoji="📅")
    ])
    
    # Payment preparation
    grid.add_row([
        button_manager.create_button("💰 Prepare Next Payment", "prepare_next_payment", emoji="💰"),
        button_manager.create_button("📱 Get Bob's Details", "get_recipient_details", emoji="📱")
    ])
    
    # Analysis and optimization
    grid.add_row([
        button_manager.create_button("📊 Payment Analytics", "payment_analytics", emoji="📊"),
        button_manager.create_button("🎯 Optimize Schedule", "optimize_schedule", emoji="🎯")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "contribution_dashboard", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=schedule_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_payment_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment history display with rich formatting."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    history_text = f"""
📊 *Payment History*

*All Your Contributions Across Groups*

🎯 **Office Savings (2 payments)**

💰 **Payment #2** - February 5, 2024
├ Recipient: Alice Johnson
├ Amount: KES 5,000
├ Method: M-Pesa
├ Confirmed: 2 hours (Fast ⚡)
├ Status: ✅ Completed
└ Transaction: TXN-2024-001234

💰 **Payment #1** - January 29, 2024  
├ Recipient: Mary Smith
├ Amount: KES 5,000
├ Method: M-Pesa
├ Confirmed: 4 hours
├ Status: ✅ Completed
└ Transaction: TXN-2024-001123

🎯 **Family Circle (1 payment)**

💰 **Payment #1** - January 15, 2024
├ Recipient: Mom
├ Amount: KES 2,000
├ Method: Cash
├ Confirmed: 1 hour (Fast ⚡)
├ Status: ✅ Completed
└ Transaction: TXN-2024-000987

📈 *Performance Summary:*
• Total payments: 3
• Total amount: KES 12,000
• Success rate: 100%
• Average confirmation: 2.3 hours
• Fastest confirmation: 1 hour
• Payment methods: M-Pesa (67%), Cash (33%)

🏆 *Achievements:*
• Perfect Payment Record ⭐
• Fast Confirmer Badge ⚡
• Multi-Group Contributor 🎯
    """.strip()
    
    # Create history action buttons
    grid = button_manager.create_grid()
    
    # Filtering and search
    grid.add_row([
        button_manager.create_button("🔍 Filter by Group", "filter_by_group", emoji="🔍"),
        button_manager.create_button("📅 Filter by Date", "filter_by_date", emoji="📅")
    ])
    
    # Export and analysis
    grid.add_row([
        button_manager.create_button("📄 Export History", "export_payment_history", emoji="📄"),
        button_manager.create_button("📊 Detailed Analytics", "detailed_payment_analytics", emoji="📊")
    ])
    
    # Transaction details
    grid.add_row([
        button_manager.create_button("🔍 View Transaction", "view_transaction_details", emoji="🔍"),
        button_manager.create_button("📱 Download Receipts", "download_all_receipts", emoji="📱")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "contribution_dashboard", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=history_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_contribution_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle real-time contribution tracking."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    tracking_text = f"""
📍 *Real-Time Contribution Tracking*

*Office Savings - Current Rotation*

👤 **Recipient:** Alice Johnson (Position #3)
💰 **Amount:** KES 5,000 per member
📅 **Started:** February 5, 2024
⏰ **Deadline:** February 12, 2024 (7 days)

📊 *Payment Progress:* 4/6 members paid (67%)

✅ **Confirmed Payments:**
• John Doe → Alice: ✅ Completed (2 hours)
• Mary Smith → Alice: ✅ Completed (1 hour)  
• Bob Wilson → Alice: ✅ Completed (4 hours)
• Sarah Davis → Alice: ✅ Completed (3 hours)

⏳ **Pending Payments:**
• Mike Brown → Alice: ⏳ Not started (3 days overdue)
• Lisa White → Alice: ⏳ Not started (1 day overdue)

🔔 *Recent Activity:*
• 2 hours ago: Sarah confirmed payment
• 4 hours ago: Bob confirmed payment
• 6 hours ago: Reminder sent to Mike & Lisa
• 1 day ago: Alice confirmed receipt from Mary

⚠️ *Issues & Alerts:*
• 2 members overdue on payments
• Mike Brown: 3 days overdue (security deposit at risk)
• Lisa White: 1 day overdue (reminder sent)

🎯 *Completion Estimate:*
• Current pace: 67% complete
• Estimated completion: February 10, 2024
• Risk level: Medium (2 overdue payments)
    """.strip()
    
    # Create tracking action buttons
    grid = button_manager.create_grid()
    
    # Real-time actions
    grid.add_row([
        button_manager.create_button("🔄 Refresh Status", "refresh_tracking", emoji="🔄"),
        button_manager.create_button("📧 Send Reminders", "send_payment_reminders", emoji="📧")
    ])
    
    # Issue management
    grid.add_row([
        button_manager.create_button("⚠️ Handle Overdue", "handle_overdue_payments", emoji="⚠️"),
        button_manager.create_button("🔒 Use Security Deposits", "use_security_deposits", emoji="🔒")
    ])
    
    # Communication
    grid.add_row([
        button_manager.create_button("💬 Group Message", "send_group_message", emoji="💬"),
        button_manager.create_button("📞 Contact Admin", "contact_group_admin", emoji="📞")
    ])
    
    # Analytics
    grid.add_row([
        button_manager.create_button("📊 Detailed Report", "detailed_tracking_report", emoji="📊"),
        button_manager.create_button("📈 Trends", "payment_trends", emoji="📈")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "contribution_dashboard", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=tracking_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_upload_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle receipt upload interface."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    upload_text = f"""
📸 *Upload Payment Receipt*

*Payment Details:*
• Group: Office Savings
• Recipient: Alice Johnson  
• Amount: KES 5,000

📱 *Upload Options:*

1️⃣ **Take Photo**
   • Use camera to capture receipt
   • Ensure text is clear and readable
   • Include transaction details

2️⃣ **Upload from Gallery**
   • Select existing photo
   • M-Pesa screenshot accepted
   • Bank receipt photos accepted

3️⃣ **Forward M-Pesa SMS**
   • Forward confirmation SMS
   • Include transaction code
   • Automatic parsing

📋 *Receipt Requirements:*
• Must show amount: KES 5,000
• Must show recipient phone/name
• Must show transaction date/time
• Must be legible and complete

🔒 *Privacy & Security:*
• Receipts stored securely
• Only visible to group admin
• Automatically deleted after 30 days
• Used only for dispute resolution

Ready to upload your receipt?
    """.strip()
    
    # Create upload action buttons
    grid = button_manager.create_grid()
    
    # Upload methods
    grid.add_row([
        button_manager.create_button("📷 Take Photo", "take_receipt_photo", emoji="📷"),
        button_manager.create_button("🖼️ Upload from Gallery", "upload_from_gallery", emoji="🖼️")
    ])
    
    # Alternative methods
    grid.add_row([
        button_manager.create_button("📱 Forward M-Pesa SMS", "forward_mpesa_sms", emoji="📱"),
        button_manager.create_button("💬 Send Transaction Code", "send_transaction_code", emoji="💬")
    ])
    
    # Help and examples
    grid.add_row([
        button_manager.create_button("📖 Upload Guide", "receipt_upload_guide", emoji="📖"),
        button_manager.create_button("👁️ See Examples", "receipt_examples", emoji="👁️")
    ])
    
    # Skip and navigation
    grid.add_row([
        button_manager.create_button("⏭️ Skip for Now", "skip_receipt_upload", emoji="⏭️"),
        button_manager.create_button("⬅️ Back", "pay_contribution", emoji="⬅️")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=upload_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# Register callback handlers for contribution confirmation
def register_contribution_callbacks(button_manager: ButtonManager) -> None:
    """Register callback functions for contribution confirmation."""
    
    # Main contribution callbacks
    button_manager.register_callback("contribution_dashboard", handle_contribution_dashboard)
    button_manager.register_callback("payment_schedule", handle_payment_schedule)
    button_manager.register_callback("payment_history", handle_payment_history)
    
    # Payment flow callbacks would be handled with pattern matching in main handler
    
    logger.info("Contribution confirmation callbacks registered")