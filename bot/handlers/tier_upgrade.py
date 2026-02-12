"""Tier upgrade interface handlers."""

from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger
from datetime import datetime, timedelta

from utils.button_manager import ButtonManager
from utils.state_manager import StateManager, ConversationState
from utils.ui_components import InteractiveCard, UIContext, ProgressIndicator
from utils.formatters import MessageFormatter, EmojiHelper
from utils.feedback_system import VisualFeedbackManager


async def handle_tier_upgrade_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main tier upgrade interface."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    
    if query:
        await query.answer()
    
    upgrade_text = f"""
**Upgrade Your Tier**

*Current:* Starter (Free)

━━━━━━━━━━━━━━━━━━━━

**Your Usage:**
• Groups: 1/1 (100% used)
• Members: 7/10 per group (70% used)
• Features: Basic only

**Why Upgrade?**
• Create more MyPoolr groups
• Invite more members per group
• Priority support & notifications
• Advanced analytics
• Premium features

*Payment via M-Pesa STK Push*

Choose your tier:
    """.strip()
    
    # Create tier selection buttons
    grid = button_manager.create_grid(max_buttons_per_row=1)
    
    tiers = [
        {"id": "essential", "name": "Essential", "price": 2, "popular": False},
        {"id": "advanced", "name": "Advanced", "price": 5, "popular": True},
        {"id": "extended", "name": "Extended", "price": 10, "popular": False}
    ]
    
    for tier in tiers:
        popular_text = " — Most Popular" if tier.get("popular") else ""
        button_text = f"{tier['name']} — ${tier['price']}/month{popular_text}"
        
        grid.add_row([
            button_manager.create_button(button_text, f"select_tier:{tier['id']}")
        ])
    
    # Add comparison and help buttons
    grid.add_row([
        button_manager.create_button("Compare Features", "compare_tiers"),
        button_manager.create_button("Pricing Calculator", "pricing_calculator")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("Help", "upgrade_help"),
        button_manager.create_button("Main Menu", "main_menu")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    if query:
        await query.edit_message_text(
            text=upgrade_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=upgrade_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def handle_tier_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle specific tier selection and show details."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace("select_tier:", "")
    
    # Tier details
    tier_details = {
        "essential": {
            "name": "Essential",
            "price": 2,
            "savings": 0,
            "max_groups": 3,
            "max_members": 25,
            "features": [
                "✅ 3 MyPoolr groups (vs 1 in Starter)",
                "✅ 25 members per group (vs 10 in Starter)",
                "✅ Priority notifications & reminders",
                "✅ Email support (24-48 hour response)",
                "✅ Basic analytics & reports",
                "✅ Custom group descriptions",
                "✅ Member management tools"
            ],
            "best_for": "Small businesses, family groups"
        },
        "advanced": {
            "name": "Advanced", 
            "price": 5,
            "savings": 4,  # vs buying Essential for 2 groups
            "max_groups": 10,
            "max_members": 50,
            "features": [
                "✅ Everything in Essential, plus:",
                "✅ 10 MyPoolr groups (vs 3 in Essential)",
                "✅ 50 members per group (vs 25 in Essential)",
                "✅ Custom rotation schedules & frequencies",
                "✅ Advanced analytics & insights",
                "✅ Export reports (PDF, Excel)",
                "✅ Priority support (4-12 hour response)",
                "✅ Group templates & presets",
                "✅ Bulk member management"
            ],
            "best_for": "Organizations, multiple communities"
        },
        "extended": {
            "name": "Extended",
            "price": 10,
            "savings": 15,  # vs multiple Advanced subscriptions
            "max_groups": "Unlimited",
            "max_members": "Unlimited", 
            "features": [
                "✅ Everything in Advanced, plus:",
                "✅ Unlimited groups & members",
                "✅ White-label branding (your logo/colors)",
                "✅ API access for integrations",
                "✅ Dedicated support manager",
                "✅ Custom feature development",
                "✅ Advanced security & compliance",
                "✅ Multi-admin management",
                "✅ Custom reporting & dashboards"
            ],
            "best_for": "Enterprises, financial institutions"
        }
    }
    
    tier = tier_details.get(tier_id, tier_details["essential"])
    
    # Calculate potential savings
    savings_text = ""
    if tier["savings"] > 0:
        savings_text = f"\n💰 *Save ${tier['savings']}/month* vs multiple lower tiers"
    
    selection_text = f"""
⭐ *{tier['name']} Tier - ${tier['price']}/month*

🎯 *Perfect for:* {tier['best_for']}{savings_text}

📊 *What You Get:*
• **Groups:** {tier['max_groups']} MyPoolr groups
• **Members:** {tier['max_members']} per group
• **Support:** Priority assistance

✨ *Features Included:*
{chr(10).join(tier['features'])}

💳 *Payment Details:*
• Monthly billing: ${tier['price']}/month
• Billed to M-Pesa: KES {tier['price'] * 130}/month
• Cancel anytime, no contracts
• 7-day free trial included

🚀 *Instant Activation:*
Features unlock immediately after payment confirmation!

Ready to upgrade to {tier['name']}?
    """.strip()
    
    # Create upgrade action buttons
    grid = button_manager.create_grid()
    
    # Main upgrade action
    grid.add_row([
        button_manager.create_button(
            f"🚀 Upgrade to {tier['name']} - ${tier['price']}/mo",
            f"initiate_payment:{tier_id}",
            emoji="🚀"
        )
    ])
    
    # Trial and alternatives
    grid.add_row([
        button_manager.create_button("🆓 Start 7-Day Trial", f"start_trial:{tier_id}", emoji="🆓"),
        button_manager.create_button("📊 See All Features", f"detailed_features:{tier_id}", emoji="📊")
    ])
    
    # Comparison and help
    grid.add_row([
        button_manager.create_button("⚖️ Compare Tiers", "compare_tiers", emoji="⚖️"),
        button_manager.create_button("💬 Contact Sales", "contact_sales", emoji="💬")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back to Tiers", "upgrade_tier", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=selection_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_payment_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle M-Pesa payment initiation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace("initiate_payment:", "")
    
    # Mock payment initiation
    payment_text = f"""
💳 *M-Pesa Payment Initiation*

*Upgrading to:* {tier_id.title()} Tier
*Amount:* KES 260 (≈ $2 USD)

📱 *M-Pesa STK Push Initiated*

Please check your phone for the M-Pesa payment request:

1️⃣ **Check Your Phone**
   Look for M-Pesa payment prompt

2️⃣ **Enter Your PIN**
   Complete the payment on your phone

3️⃣ **Confirm Payment**
   Payment will be processed automatically

⏱️ *Payment Status:* Waiting for confirmation...

🔒 *Secure Payment:*
• Processed via Safaricom M-Pesa
• 256-bit SSL encryption
• No card details stored
• Instant confirmation

⚠️ *Important:*
• Don't close this chat until payment completes
• Payment expires in 5 minutes
• Contact support if issues occur

Waiting for your payment confirmation...
    """.strip()
    
    # Create payment status buttons
    grid = button_manager.create_grid()
    
    # Payment actions
    grid.add_row([
        button_manager.create_button("🔄 Check Payment Status", f"check_payment:{tier_id}", emoji="🔄"),
        button_manager.create_button("📱 Resend STK Push", f"resend_stk:{tier_id}", emoji="📱")
    ])
    
    # Help and alternatives
    grid.add_row([
        button_manager.create_button("❓ Payment Help", "payment_help", emoji="❓"),
        button_manager.create_button("💳 Alternative Payment", f"alt_payment:{tier_id}", emoji="💳")
    ])
    
    # Cancel and navigation
    grid.add_row([
        button_manager.create_button("❌ Cancel Payment", "cancel_payment", emoji="❌"),
        button_manager.create_button("💬 Contact Support", "contact_support", emoji="💬")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=payment_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    # Simulate payment processing (in real app, this would be async)
    import asyncio
    await asyncio.sleep(3)  # Simulate processing time
    
    # Show payment success (mock)
    await handle_payment_success(update, context, tier_id)


async def handle_payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE, tier_id: str = None) -> None:
    """Handle successful payment and tier upgrade."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    if not tier_id:
        tier_id = "essential"  # Default fallback
    
    tier_names = {
        "essential": "Essential",
        "advanced": "Advanced", 
        "extended": "Extended"
    }
    
    tier_name = tier_names.get(tier_id, "Essential")
    
    success_text = f"""
🎉 *Payment Successful!*

*Congratulations!* You've successfully upgraded to {tier_name} tier!

✅ *Payment Confirmed:*
• Transaction ID: TXN-2024-UP-001234
• Amount: KES 260
• Method: M-Pesa
• Status: Completed

🚀 *Features Unlocked Instantly:*
• Create up to 3 MyPoolr groups (was 1)
• Invite up to 25 members per group (was 10)
• Priority notifications enabled
• Email support activated
• Basic analytics unlocked

📊 *Your New Limits:*
• Groups: 1/3 used (200% increase!)
• Members: 7/25 per group (150% increase!)
• Support: Priority queue activated

🎁 *Welcome Bonus:*
• 7-day money-back guarantee
• Free setup consultation
• Priority onboarding support

🔔 *What's Next:*
• Create your second MyPoolr group
• Invite more members to existing groups
• Explore new analytics features
• Contact support for any questions

Thank you for upgrading! Enjoy your enhanced MyPoolr experience! 🚀
    """.strip()
    
    # Create post-upgrade action buttons
    grid = button_manager.create_grid()
    
    # Immediate actions
    grid.add_row([
        button_manager.create_button("➕ Create New Group", "create_mypoolr", emoji="➕"),
        button_manager.create_button("👥 Invite More Members", "invite_members", emoji="👥")
    ])
    
    # Explore new features
    grid.add_row([
        button_manager.create_button("📊 View Analytics", "view_analytics", emoji="📊"),
        button_manager.create_button("🔔 Setup Notifications", "setup_notifications", emoji="🔔")
    ])
    
    # Support and receipt
    grid.add_row([
        button_manager.create_button("📄 Download Receipt", "download_receipt", emoji="📄"),
        button_manager.create_button("💬 Get Support", "premium_support", emoji="💬")
    ])
    
    # Social sharing
    grid.add_row([
        button_manager.create_button("🎉 Share Success", "share_upgrade", emoji="🎉"),
        button_manager.create_button("⭐ Rate Experience", "rate_upgrade", emoji="⭐")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    # Update the message with success content
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=success_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=success_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error updating message with payment success: {e}")
        # Send new message if edit fails
        await update.effective_chat.send_message(
            text=success_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
async def handle_tier_comparison(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle detailed tier comparison table."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    comparison_text = f"""
📊 *Complete Tier Comparison*

*Choose the perfect tier for your needs:*

┌─────────────────────────────────────┐
│ **STARTER** (Current) - FREE       │
├─────────────────────────────────────┤
│ • 1 MyPoolr group                   │
│ • 10 members per group              │
│ • Basic notifications               │
│ • Community support                 │
│ • Standard features only            │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ **ESSENTIAL** - $2/month ⭐         │
├─────────────────────────────────────┤
│ • 3 MyPoolr groups (+200%)          │
│ • 25 members per group (+150%)      │
│ • Priority notifications            │
│ • Email support (24-48h)            │
│ • Basic analytics                   │
│ • Custom descriptions               │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ **ADVANCED** - $5/month 🔥 POPULAR │
├─────────────────────────────────────┤
│ • 10 MyPoolr groups (+900%)         │
│ • 50 members per group (+400%)      │
│ • Custom rotation schedules         │
│ • Advanced analytics & insights     │
│ • Export reports (PDF/Excel)        │
│ • Priority support (4-12h)          │
│ • Group templates                   │
│ • Bulk member management            │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ **EXTENDED** - $10/month 💎        │
├─────────────────────────────────────┤
│ • Unlimited groups & members        │
│ • White-label branding              │
│ • API access & integrations         │
│ • Dedicated support manager         │
│ • Custom feature development        │
│ • Advanced security & compliance    │
│ • Multi-admin management            │
│ • Custom dashboards                 │
└─────────────────────────────────────┘

💡 *Recommendations:*
• **Essential:** Perfect for families & small groups
• **Advanced:** Ideal for businesses & organizations  
• **Extended:** Best for enterprises & institutions

All tiers include 7-day free trial & money-back guarantee!
    """.strip()
    
    # Create comparison action buttons
    grid = button_manager.create_grid()
    
    # Quick upgrade buttons
    grid.add_row([
        button_manager.create_button("⭐ Choose Essential", "select_tier:essential", emoji="⭐"),
        button_manager.create_button("🔥 Choose Advanced", "select_tier:advanced", emoji="🔥")
    ])
    
    grid.add_row([
        button_manager.create_button("💎 Choose Extended", "select_tier:extended", emoji="💎")
    ])
    
    # Detailed information
    grid.add_row([
        button_manager.create_button("💰 Pricing Calculator", "pricing_calculator", emoji="💰"),
        button_manager.create_button("📋 Feature Details", "feature_details", emoji="📋")
    ])
    
    # Help and consultation
    grid.add_row([
        button_manager.create_button("💬 Get Recommendation", "get_tier_recommendation", emoji="💬"),
        button_manager.create_button("📞 Talk to Sales", "talk_to_sales", emoji="📞")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "upgrade_tier", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=comparison_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_upgrade_status_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle upgrade status and subscription management."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    # Mock subscription data
    status_text = f"""
📊 *Subscription Status*

*Current Tier:* Essential ⭐
*Status:* Active & Healthy

💳 *Billing Information:*
• Plan: Essential ($2/month)
• Next billing: February 15, 2024
• Payment method: M-Pesa (+254-XXX-XXXX)
• Auto-renewal: ✅ Enabled

📈 *Usage This Month:*
• Groups created: 2/3 (67% used)
• Members invited: 18/25 per group (72% used)
• Support tickets: 1/unlimited
• Analytics views: 45/unlimited

🎯 *Feature Usage:*
• Priority notifications: ✅ Active
• Email support: ✅ Used 1x this month
• Basic analytics: ✅ Viewed 45 times
• Custom descriptions: ✅ Used on 2 groups

💰 *Billing History:*
• Feb 1, 2024: KES 260 - Paid ✅
• Jan 1, 2024: KES 260 - Paid ✅
• Dec 1, 2023: KES 260 - Paid ✅

🔔 *Notifications:*
• Approaching group limit (2/3 used)
• Next billing in 10 days
• New features available in Advanced tier

⚡ *Upgrade Recommendations:*
You're using 67% of your group limit. Consider upgrading to Advanced for 10 groups!
    """.strip()
    
    # Create subscription management buttons
    grid = button_manager.create_grid()
    
    # Subscription actions
    grid.add_row([
        button_manager.create_button("⬆️ Upgrade Tier", "upgrade_from_current", emoji="⬆️"),
        button_manager.create_button("⬇️ Downgrade Tier", "downgrade_tier", emoji="⬇️")
    ])
    
    # Billing management
    grid.add_row([
        button_manager.create_button("💳 Update Payment", "update_payment_method", emoji="💳"),
        button_manager.create_button("📄 Billing History", "billing_history", emoji="📄")
    ])
    
    # Settings and preferences
    grid.add_row([
        button_manager.create_button("🔔 Billing Alerts", "billing_alerts", emoji="🔔"),
        button_manager.create_button("⚙️ Auto-Renewal", "auto_renewal_settings", emoji="⚙️")
    ])
    
    # Support and cancellation
    grid.add_row([
        button_manager.create_button("💬 Billing Support", "billing_support", emoji="💬"),
        button_manager.create_button("❌ Cancel Subscription", "cancel_subscription", emoji="❌")
    ])
    
    # Navigation
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=status_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_feature_unlock_celebration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feature unlock celebration and onboarding."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    celebration_text = f"""
🎊 *Welcome to Essential Tier!*

*Your new superpowers are now active!*

🚀 *Just Unlocked:*

✨ **Create More Groups**
   • Was: 1 group → Now: 3 groups
   • Create groups for work, family, friends!

👥 **Invite More Members**  
   • Was: 10 members → Now: 25 members
   • Build bigger, stronger savings circles!

🔔 **Priority Notifications**
   • Get notified first about payments
   • Never miss important deadlines
   • Customizable reminder schedules

📧 **Email Support**
   • Direct email support line
   • 24-48 hour response guarantee
   • Priority queue access

📊 **Basic Analytics**
   • Track group performance
   • Member contribution patterns
   • Payment success rates

🎯 *Quick Start Guide:*

1️⃣ **Create Your Second Group**
   Perfect for a different circle (work vs family)

2️⃣ **Invite More Members**
   Expand your existing group to 25 members

3️⃣ **Explore Analytics**
   See insights about your group performance

4️⃣ **Setup Notifications**
   Customize your priority alerts

Ready to explore your new features?
    """.strip()
    
    # Create feature exploration buttons
    grid = button_manager.create_grid()
    
    # Quick actions to try new features
    grid.add_row([
        button_manager.create_button("🚀 Create 2nd Group", "create_second_group", emoji="🚀"),
        button_manager.create_button("👥 Invite More Members", "invite_more_members", emoji="👥")
    ])
    
    # Explore new capabilities
    grid.add_row([
        button_manager.create_button("📊 View Analytics", "explore_analytics", emoji="📊"),
        button_manager.create_button("🔔 Setup Notifications", "setup_priority_notifications", emoji="🔔")
    ])
    
    # Help and guidance
    grid.add_row([
        button_manager.create_button("📖 Feature Guide", "essential_feature_guide", emoji="📖"),
        button_manager.create_button("💬 Get Help", "essential_support", emoji="💬")
    ])
    
    # Skip onboarding
    grid.add_row([
        button_manager.create_button("⏭️ Skip Tour", "skip_onboarding", emoji="⏭️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=celebration_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_start_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle starting a free trial for a tier."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace("start_trial:", "")
    
    tier_names = {
        "essential": "Essential",
        "advanced": "Advanced",
        "extended": "Extended"
    }
    
    tier_name = tier_names.get(tier_id, "Essential")
    trial_end = datetime.now() + timedelta(days=7)
    
    trial_text = f"""
🆓 *7-Day Free Trial - {tier_name} Tier*

*Trial Details:*
• Duration: 7 days (ends {trial_end.strftime('%B %d, %Y')})
• Full access to all {tier_name} features
• No credit card required
• Cancel anytime during trial
• Auto-converts to paid after trial

*What You Get During Trial:*
✅ All {tier_name} tier features unlocked
✅ Full member limits and group capacity
✅ Priority support access
✅ No restrictions or limitations

*After Trial Ends:*
• Automatic upgrade to {tier_name} tier
• First payment via M-Pesa STK Push
• Continue with all features unlocked
• Or downgrade back to Starter (free)

*Important Notes:*
• You can only use one trial per tier
• Trial starts immediately upon activation
• Reminder sent 2 days before trial ends

Ready to start your free trial?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button(
            f"🚀 Start {tier_name} Trial Now",
            f"confirm_trial:{tier_id}",
            emoji="🚀"
        )
    ])
    grid.add_row([
        button_manager.create_button("💳 Skip Trial & Pay Now", f"initiate_payment:{tier_id}", emoji="💳"),
        button_manager.create_button("📋 Trial Terms", f"trial_terms:{tier_id}", emoji="📋")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", f"select_tier:{tier_id}", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=trial_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_detailed_features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle detailed feature breakdown for a tier."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace("detailed_features:", "")
    
    feature_details = {
        "essential": {
            "name": "Essential",
            "price": 2,
            "categories": {
                "📊 Group Management": [
                    "Create up to 3 MyPoolr groups",
                    "25 members per group maximum",
                    "Custom group names & descriptions",
                    "Group activity dashboard",
                    "Member invitation system"
                ],
                "🔔 Notifications": [
                    "Priority push notifications",
                    "Payment reminders (24h, 6h, 1h)",
                    "Rotation update alerts",
                    "Security deposit notifications",
                    "Email notification support"
                ],
                "💰 Financial Features": [
                    "Automated contribution tracking",
                    "Payment history & receipts",
                    "Security deposit management",
                    "Basic financial reports",
                    "M-Pesa integration"
                ],
                "🛠️ Support & Tools": [
                    "Email support (24-48h response)",
                    "Basic analytics dashboard",
                    "Member management tools",
                    "Group settings customization",
                    "Help center access"
                ]
            }
        },
        "advanced": {
            "name": "Advanced",
            "price": 5,
            "categories": {
                "📊 Group Management": [
                    "Create up to 10 MyPoolr groups",
                    "50 members per group maximum",
                    "Custom rotation schedules",
                    "Group templates & presets",
                    "Bulk member management",
                    "Advanced group settings"
                ],
                "🔔 Notifications": [
                    "All Essential notifications, plus:",
                    "Custom notification schedules",
                    "SMS notifications (optional)",
                    "Multi-channel alerts",
                    "Notification preferences per group"
                ],
                "💰 Financial Features": [
                    "All Essential features, plus:",
                    "Advanced analytics & insights",
                    "Export reports (PDF, Excel)",
                    "Custom contribution schedules",
                    "Financial forecasting",
                    "Detailed transaction logs"
                ],
                "🛠️ Support & Tools": [
                    "Priority support (4-12h response)",
                    "Advanced analytics dashboard",
                    "Custom reporting tools",
                    "API access (basic)",
                    "Integration options",
                    "Training resources"
                ]
            }
        },
        "extended": {
            "name": "Extended",
            "price": 10,
            "categories": {
                "📊 Group Management": [
                    "Unlimited MyPoolr groups",
                    "Unlimited members per group",
                    "White-label branding options",
                    "Multi-admin management",
                    "Enterprise-grade controls",
                    "Custom workflows"
                ],
                "🔔 Notifications": [
                    "All Advanced notifications, plus:",
                    "Custom notification templates",
                    "Branded notifications",
                    "Advanced automation rules",
                    "Integration with external systems"
                ],
                "💰 Financial Features": [
                    "All Advanced features, plus:",
                    "Custom reporting & dashboards",
                    "Advanced compliance tools",
                    "Audit trail & logging",
                    "Financial API access",
                    "Custom integrations"
                ],
                "🛠️ Support & Tools": [
                    "Dedicated support manager",
                    "24/7 priority support",
                    "Custom feature development",
                    "Full API access",
                    "Advanced security features",
                    "Compliance assistance",
                    "Training & onboarding"
                ]
            }
        }
    }
    
    tier = feature_details.get(tier_id, feature_details["essential"])
    
    # Build feature list
    feature_sections = []
    for category, features in tier["categories"].items():
        feature_list = "\n".join([f"  • {f}" for f in features])
        feature_sections.append(f"{category}\n{feature_list}")
    
    features_text = f"""
✨ *{tier['name']} Tier - Complete Features*

*Price:* ${tier['price']}/month

━━━━━━━━━━━━━━━━━━━━

{chr(10).join(feature_sections)}

━━━━━━━━━━━━━━━━━━━━

💡 *All features activate immediately after payment*

Ready to upgrade?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button(
            f"🚀 Upgrade to {tier['name']}",
            f"initiate_payment:{tier_id}",
            emoji="🚀"
        )
    ])
    grid.add_row([
        button_manager.create_button("🆓 Start Free Trial", f"start_trial:{tier_id}", emoji="🆓"),
        button_manager.create_button("⚖️ Compare Tiers", "compare_tiers", emoji="⚖️")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", f"select_tier:{tier_id}", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await query.edit_message_text(
        text=features_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# Register callback handlers for tier upgrade
def register_tier_upgrade_callbacks(button_manager: ButtonManager) -> None:
    """Register callback functions for tier upgrade."""
    
    # Main tier upgrade callbacks
    button_manager.register_callback("upgrade_tier", handle_tier_upgrade_main)
    button_manager.register_callback("compare_tiers", handle_tier_comparison)
    button_manager.register_callback("upgrade_status", handle_upgrade_status_tracking)
    button_manager.register_callback("feature_celebration", handle_feature_unlock_celebration)
    
    # Tier selection callbacks would be handled with pattern matching in main handler
    
    logger.info("Tier upgrade callbacks registered")