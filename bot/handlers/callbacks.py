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
    elif callback_data.startswith("settings_"):
        await handle_settings_section(update, context, callback_data)
    elif callback_data == "learn_mypoolr":
        await handle_learn_mypoolr(update, context)
    elif callback_data == "enter_invitation_code":
        await handle_paste_invitation(update, context)
    elif callback_data == "export_data":
        await handle_export_data(update, context)
    elif callback_data == "email_support":
        await handle_email_support(update, context)
    elif callback_data == "telegram_support":
        await handle_telegram_support(update, context)
    elif callback_data == "pay_security_deposit":
        await handle_pay_security_deposit(update, context)
    elif callback_data == "learn_security":
        await handle_learn_security(update, context)
    elif callback_data == "help_joining":
        await handle_help_section(update, context, "help_joining")
    elif callback_data == "help_creating":
        await handle_help_section(update, context, "help_creating")
    elif callback_data == "help_getting_started":
        await handle_help_section(update, context, "help_getting_started")
    elif callback_data == "help_troubleshoot":
        await handle_help_section(update, context, "help_troubleshoot")
    elif callback_data == "help_tiers":
        await handle_help_section(update, context, "help_tiers")
    elif callback_data == "full_report":
        await handle_full_report(update, context)
    elif callback_data == "export_transactions":
        await handle_export_specific(update, context, "transactions")
    elif callback_data == "export_groups":
        await handle_export_specific(update, context, "groups")
    elif callback_data == "export_security":
        await handle_export_specific(update, context, "security")
    elif callback_data == "export_report_pdf":
        await handle_export_report(update, context, "pdf")
    elif callback_data == "export_report_excel":
        await handle_export_report(update, context, "excel")
    elif callback_data.startswith("pay_deposit:"):
        await handle_pay_specific_deposit(update, context, callback_data)
    elif callback_data == "pricing_calculator":
        await handle_pricing_calculator(update, context)
    elif callback_data == "contact_sales":
        await handle_contact_sales(update, context)
    elif callback_data == "help_guide":
        await handle_help_section(update, context, "help_getting_started")
    elif callback_data == "feature_details":
        await handle_feature_details(update, context)
    elif callback_data == "help_contributions":
        await handle_help_section(update, context, "help_contributions")
    elif callback_data == "help_security":
        await handle_help_section(update, context, "help_security")
    elif callback_data.startswith("help_"):
        await handle_help_section(update, context, callback_data)
    elif callback_data == "contact_support":
        await handle_contact_support(update, context)
    # Additional settings callbacks
    elif callback_data == "settings_notifications":
        await handle_settings_section(update, context, "settings_notifications")
    elif callback_data == "settings_currency":
        await handle_settings_section(update, context, "settings_currency")
    # Conversation/creation callbacks
    elif callback_data == "start_mypoolr_creation":
        await handle_start_creation(update, context)
    elif callback_data == "confirm_create":
        await handle_confirm_create(update, context)
    elif callback_data == "cancel_creation":
        await handle_cancel_creation(update, context)
    elif callback_data == "edit_details":
        await handle_edit_details(update, context)
    # Export format callbacks
    elif callback_data.startswith("export_") and callback_data.endswith(("_pdf", "_csv", "_excel")):
        await handle_export_format(update, context, callback_data)
    # Payment and billing callbacks
    elif callback_data == "billing_history":
        await handle_billing_history(update, context)
    elif callback_data == "billing_alerts":
        await handle_billing_alerts(update, context)
    elif callback_data == "billing_support":
        await handle_billing_support(update, context)
    elif callback_data == "cancel_payment":
        await handle_cancel_payment(update, context)
    elif callback_data == "cancel_subscription":
        await handle_cancel_subscription(update, context)
    elif callback_data == "auto_renewal_settings":
        await handle_auto_renewal_settings(update, context)
    elif callback_data == "update_payment_method":
        await handle_update_payment_method(update, context)
    # Member and invitation management
    elif callback_data == "invitation_settings":
        await handle_invitation_settings(update, context)
    elif callback_data == "invitation_stats":
        await handle_invitation_stats(update, context)
    elif callback_data == "invitation_analytics":
        await handle_invitation_analytics(update, context)
    elif callback_data == "generate_new_invitation":
        await handle_generate_new_invitation(update, context)
    elif callback_data == "resend_invitations":
        await handle_resend_invitations(update, context)
    elif callback_data == "deactivate_invitations":
        await handle_deactivate_invitations(update, context)
    elif callback_data == "track_invitation_responses":
        await handle_track_invitation_responses(update, context)
    elif callback_data == "custom_invitation_message":
        await handle_custom_invitation_message(update, context)
    elif callback_data == "new_invitation_link":
        await handle_new_invitation_link(update, context)
    elif callback_data.startswith("remind_member:"):
        await handle_remind_member(update, context, callback_data)
    elif callback_data == "invite_more_members":
        await handle_invite_more_members(update, context)
    elif callback_data == "export_members":
        await handle_export_members(update, context)
    elif callback_data == "message_all_members":
        await handle_message_all_members(update, context)
    elif callback_data == "send_group_message":
        await handle_send_group_message(update, context)
    elif callback_data == "member_settings":
        await handle_member_settings(update, context)
    # Analytics and reporting
    elif callback_data == "view_analytics":
        await handle_view_analytics(update, context)
    elif callback_data == "detailed_analytics":
        await handle_detailed_analytics(update, context)
    elif callback_data == "payment_analytics":
        await handle_payment_analytics(update, context)
    elif callback_data == "detailed_payment_analytics":
        await handle_detailed_payment_analytics(update, context)
    elif callback_data == "payment_trends":
        await handle_payment_trends(update, context)
    elif callback_data == "explore_analytics":
        await handle_explore_analytics(update, context)
    elif callback_data == "detailed_tracking_report":
        await handle_detailed_tracking_report(update, context)
    elif callback_data == "export_stats_report":
        await handle_export_stats_report(update, context)
    elif callback_data == "security_report":
        await handle_security_report(update, context)
    elif callback_data == "filter_by_date":
        await handle_filter_by_date(update, context)
    elif callback_data == "filter_by_group":
        await handle_filter_by_group(update, context)
    # Payment and contribution callbacks
    elif callback_data == "pay_office_savings":
        await handle_pay_office_savings(update, context)
    elif callback_data == "prepare_next_payment":
        await handle_prepare_next_payment(update, context)
    elif callback_data == "next_payment_schedule":
        await handle_next_payment_schedule(update, context)
    elif callback_data == "view_all_contributions":
        await handle_view_all_contributions(update, context)
    elif callback_data == "contribution_help":
        await handle_contribution_help(update, context)
    elif callback_data == "payment_help":
        await handle_payment_help(update, context)
    elif callback_data == "recipient_help":
        await handle_recipient_help(update, context)
    elif callback_data == "send_payment_reminders":
        await handle_send_payment_reminders(update, context)
    elif callback_data == "set_payment_reminders":
        await handle_set_payment_reminders(update, context)
    elif callback_data == "handle_overdue_payments":
        await handle_overdue_payments(update, context)
    elif callback_data == "remove_overdue_members":
        await handle_remove_overdue_members(update, context)
    elif callback_data == "report_payment_problem":
        await handle_report_payment_problem(update, context)
    elif callback_data.startswith("remind_recipient:"):
        await handle_remind_recipient(update, context, callback_data)
    elif callback_data.startswith("message_recipient:"):
        await handle_message_recipient(update, context, callback_data)
    elif callback_data == "get_recipient_details":
        await handle_get_recipient_details(update, context)
    elif callback_data == "contact_sender":
        await handle_contact_sender(update, context)
    elif callback_data == "contact_admin":
        await handle_contact_admin(update, context)
    elif callback_data == "contact_group_admin":
        await handle_contact_group_admin(update, context)
    # Receipt and transaction callbacks
    elif callback_data == "download_receipt":
        await handle_download_receipt(update, context)
    elif callback_data == "download_all_receipts":
        await handle_download_all_receipts(update, context)
    elif callback_data == "receipt_upload_guide":
        await handle_receipt_upload_guide(update, context)
    elif callback_data == "receipt_examples":
        await handle_receipt_examples(update, context)
    elif callback_data == "take_receipt_photo":
        await handle_take_receipt_photo(update, context)
    elif callback_data == "upload_from_gallery":
        await handle_upload_from_gallery(update, context)
    elif callback_data == "skip_receipt_upload":
        await handle_skip_receipt_upload(update, context)
    elif callback_data == "check_mpesa_messages":
        await handle_check_mpesa_messages(update, context)
    elif callback_data == "forward_mpesa_sms":
        await handle_forward_mpesa_sms(update, context)
    elif callback_data == "send_transaction_code":
        await handle_send_transaction_code(update, context)
    elif callback_data == "view_transaction":
        await handle_view_transaction(update, context)
    elif callback_data == "view_transaction_details":
        await handle_view_transaction_details(update, context)
    elif callback_data == "export_payment_history":
        await handle_export_payment_history(update, context)
    # Tier and upgrade callbacks
    elif callback_data == "downgrade_tier":
        await handle_downgrade_tier(update, context)
    elif callback_data == "upgrade_from_current":
        await handle_upgrade_from_current(update, context)
    elif callback_data == "upgrade_help":
        await handle_upgrade_help(update, context)
    elif callback_data == "get_tier_recommendation":
        await handle_get_tier_recommendation(update, context)
    elif callback_data == "essential_feature_guide":
        await handle_essential_feature_guide(update, context)
    elif callback_data == "essential_support":
        await handle_essential_support(update, context)
    elif callback_data == "premium_support":
        await handle_premium_support(update, context)
    elif callback_data == "rate_upgrade":
        await handle_rate_upgrade(update, context)
    elif callback_data == "share_upgrade":
        await handle_share_upgrade(update, context)
    # Sales and support callbacks
    elif callback_data == "schedule_demo":
        await handle_schedule_demo(update, context)
    elif callback_data == "email_sales":
        await handle_email_sales(update, context)
    elif callback_data == "talk_to_sales":
        await handle_talk_to_sales(update, context)
    # Group optimization and management
    elif callback_data == "optimize_group":
        await handle_optimize_group(update, context)
    elif callback_data == "optimize_schedule":
        await handle_optimize_schedule(update, context)
    elif callback_data == "recalculate_deposits":
        await handle_recalculate_deposits(update, context)
    elif callback_data == "use_security_deposits":
        await handle_use_security_deposits(update, context)
    elif callback_data == "compare_groups":
        await handle_compare_groups(update, context)
    elif callback_data == "create_second_group":
        await handle_create_second_group(update, context)
    # Notification and settings callbacks
    elif callback_data == "notification_settings":
        await handle_notification_settings(update, context)
    elif callback_data == "setup_notifications":
        await handle_setup_notifications(update, context)
    elif callback_data == "setup_priority_notifications":
        await handle_setup_priority_notifications(update, context)
    # Miscellaneous callbacks
    elif callback_data == "refresh_tracking":
        await handle_refresh_tracking(update, context)
    elif callback_data == "add_to_calendar":
        await handle_add_to_calendar(update, context)
    elif callback_data == "share_via_sms":
        await handle_share_via_sms(update, context)
    elif callback_data == "share_success":
        await handle_share_success(update, context)
    elif callback_data == "rate_experience":
        await handle_rate_experience(update, context)
    elif callback_data == "skip_onboarding":
        await handle_skip_onboarding(update, context)
    elif callback_data == "address_issues":
        await handle_address_issues(update, context)
    elif callback_data.startswith("upload_deposit_receipt:"):
        await handle_upload_deposit_receipt(update, context, callback_data)
    # Back navigation callbacks
    elif callback_data.startswith("back_to_"):
        await handle_back_navigation(update, context, callback_data)
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
    elif callback_data == "view_trends":
        await handle_view_trends(update, context)
    elif callback_data == "confirm_cancel_subscription":
        await handle_confirm_cancel_subscription(update, context)
    elif callback_data == "disable_auto_renewal":
        await handle_disable_auto_renewal(update, context)
    elif callback_data == "change_billing_date":
        await handle_change_billing_date(update, context)
    elif callback_data == "confirm_disable_renewal":
        await handle_confirm_disable_renewal(update, context)
    elif callback_data == "pause_subscription":
        await handle_pause_subscription(update, context)
    elif callback_data == "process_cancellation":
        await handle_process_cancellation(update, context)
    elif callback_data.startswith("pause_for:"):
        await handle_pause_for(update, context, callback_data)
    elif callback_data.startswith("set_billing_date:"):
        await handle_set_billing_date(update, context, callback_data)
    elif callback_data == "reactivate_subscription":
        await handle_reactivate_subscription(update, context)
    elif callback_data == "cancellation_feedback":
        await handle_cancellation_feedback(update, context)
    elif callback_data == "email_cancellation_receipt":
        await handle_email_cancellation_receipt(update, context)
    elif callback_data.startswith("confirm_reactivate:"):
        await handle_confirm_reactivate(update, context, callback_data)
    elif callback_data == "email_billing_change":
        await handle_email_billing_change(update, context)
    elif callback_data == "email_pause_confirmation":
        await handle_email_pause_confirmation(update, context)
    elif callback_data.startswith("feedback:"):
        await handle_feedback_submission(update, context, callback_data)
    elif callback_data == "resend_cancellation_receipt":
        await handle_resend_cancellation_receipt(update, context)
    elif callback_data == "update_email_address":
        await handle_update_email_address(update, context)
    elif callback_data == "email_preferences":
        await handle_email_preferences(update, context)
    elif callback_data == "email_reactivation_confirmation":
        await handle_email_reactivation_confirmation(update, context)
    elif callback_data == "feature_request":
        await handle_feature_request(update, context)
    elif callback_data == "prompt_new_email":
        await handle_prompt_new_email(update, context)
    elif callback_data == "resend_billing_confirmation":
        await handle_resend_billing_confirmation(update, context)
    elif callback_data == "sms_receipt":
        await handle_sms_receipt(update, context)
    elif callback_data == "verify_current_email":
        await handle_verify_current_email(update, context)
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


async def handle_settings_section(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle specific settings sections."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    section = callback_data.replace("settings_", "")
    
    settings_content = {
        "notifications": {
            "title": "🔔 Notification Settings",
            "content": """
*Notification Preferences*

*Current Settings:*
• Payment reminders: ✅ Enabled
• Rotation updates: ✅ Enabled
• Group invitations: ✅ Enabled
• Security alerts: ✅ Enabled
• Marketing updates: ❌ Disabled

*Notification Channels:*
• Telegram: ✅ Active
• Email: ❌ Not configured
• SMS: ❌ Not configured

*Reminder Timing:*
• 24 hours before payment due
• 6 hours before payment due
• 1 hour before payment due

You can customize these settings to match your preferences.
            """
        },
        "language": {
            "title": "🌍 Language Settings",
            "content": """
*Language Preferences*

*Current Language:* English 🇬🇧

*Available Languages:*
• English 🇬🇧
• Swahili 🇰🇪
• French 🇫🇷
• Spanish 🇪🇸

*Regional Settings:*
• Date format: DD/MM/YYYY
• Time format: 24-hour
• First day of week: Monday

Select your preferred language below to change the bot interface language.
            """
        },
        "security": {
            "title": "🔒 Security Settings",
            "content": """
*Security & Privacy*

*Account Security:*
• Two-factor authentication: ❌ Disabled
• Phone verification: ✅ Verified
• Email verification: ❌ Not set up
• Login alerts: ✅ Enabled

*Privacy Settings:*
• Profile visibility: Members only
• Payment history: Private
• Group membership: Visible to group members

*Security Deposits:*
• Auto-calculation: ✅ Enabled
• Deposit status: Up to date
• Total deposits held: KES 0

*Recommendations:*
• Enable two-factor authentication for extra security
• Verify your email address for account recovery
• Review your privacy settings regularly
            """
        },
        "currency": {
            "title": "💱 Currency Settings",
            "content": """
*Currency Preferences*

*Current Currency:* KES (Kenyan Shilling) 🇰🇪

*Available Currencies:*
• KES - Kenyan Shilling 🇰🇪
• USD - US Dollar 🇺🇸
• EUR - Euro 🇪🇺
• GBP - British Pound 🇬🇧
• TZS - Tanzanian Shilling 🇹🇿
• UGX - Ugandan Shilling 🇺🇬

*Display Format:*
• Symbol position: Before amount
• Decimal separator: .
• Thousands separator: ,
• Example: KES 1,000.00

Note: Currency is set per MyPoolr group and cannot be changed after group creation.
            """
        }
    }
    
    content = settings_content.get(section, {
        "title": "⚙️ Settings",
        "content": "This settings section is not available. Please contact support for assistance."
    })
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("⬅️ Back to Settings", "settings", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=f"{content['title']}\n\n{content['content'].strip()}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_export_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle data export request."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    export_text = """
📊 *Export Your Data*

You can export your MyPoolr data in various formats for your records.

*Available Exports:*

📄 **Transaction History**
   • All your contributions and receipts
   • Payment confirmations
   • Security deposit records
   • Format: PDF, CSV, Excel

📊 **Group Reports**
   • Member lists and positions
   • Rotation schedules
   • Payment status tracking
   • Format: PDF, Excel

🔒 **Security Records**
   • Deposit history
   • Lock-in status
   • Account security logs
   • Format: PDF

*How to Export:*
1. Select the data type you want to export
2. Choose your preferred format
3. We'll generate and send the file to you
4. Download within 24 hours

*Privacy Note:*
Exported data is encrypted and only accessible to you.
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📄 Transaction History", "export_transactions", emoji="📄"),
        button_manager.create_button("📊 Group Reports", "export_groups", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("🔒 Security Records", "export_security", emoji="🔒")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back to Settings", "settings", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=export_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_email_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle email support contact."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    email_text = f"""
📧 *Email Support*

Send us an email and we'll get back to you within 2-4 hours.

*Email Address:*
support@mypoolr.com

*What to Include:*
• Your user ID: `{update.effective_user.id}`
• Clear description of your issue
• Screenshots if applicable
• Any error messages you received

*Response Time:*
• Standard: 2-4 hours
• Complex issues: 24 hours
• Weekends: Next business day

*Tip:* For faster support, use Telegram support for urgent issues.
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💬 Telegram Support", "telegram_support", emoji="💬"),
        button_manager.create_button("❓ Help Center", "help_main", emoji="❓")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "contact_support", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=email_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_telegram_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Telegram support contact."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    telegram_text = f"""
💬 *Telegram Support*

Get instant help from our support team on Telegram.

*Support Channel:*
@mypoolr_support

*How to Get Help:*
1. Join our support channel
2. Send your question or issue
3. Include your user ID: `{update.effective_user.id}`
4. Our team will respond within 30 minutes

*Available Hours:*
• Monday - Friday: 8 AM - 8 PM EAT
• Saturday: 9 AM - 5 PM EAT
• Sunday: Emergency support only

*For Urgent Issues:*
We prioritize payment issues, security concerns, and account access problems.
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📧 Email Support", "email_support", emoji="📧"),
        button_manager.create_button("❓ Help Center", "help_main", emoji="❓")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "contact_support", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=telegram_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_pay_security_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle security deposit payment."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    user_id = update.effective_user.id
    
    await update.callback_query.answer()
    
    try:
        # Fetch pending security deposits from backend
        result = await backend_client.get_pending_deposits(user_id)
        
        if not result.get('success'):
            await update.callback_query.edit_message_text(
                "❌ Unable to fetch pending deposits. Please try again.",
                parse_mode="Markdown"
            )
            return
        
        deposits = result.get('deposits', [])
        
        if not deposits:
            deposit_text = """
✅ *No Pending Deposits*

You don't have any pending security deposits at the moment.

Security deposits are required when:
• Joining a new MyPoolr group
• Upgrading to a higher tier
• Replacing a defaulted deposit

All your current deposits are up to date!
            """.strip()
            
            grid = button_manager.create_grid()
            grid.add_row([
                button_manager.create_button("📋 My Groups", "my_groups", emoji="📋"),
                button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
            ])
        else:
            # Show pending deposits
            deposit_list = []
            for deposit in deposits:
                deposit_list.append(
                    f"🎯 **{deposit['group_name']}**\n"
                    f"💰 Amount: KES {deposit['amount']:,}\n"
                    f"📅 Due: {deposit['due_date']}\n"
                    f"Status: {deposit['status']}"
                )
            
            deposit_text = f"""
💰 *Pay Security Deposit*

You have {len(deposits)} pending security deposit(s):

{chr(10).join(deposit_list)}

*Payment Instructions:*
1. Pay via M-Pesa to the group admin
2. Upload payment receipt below
3. Wait for admin confirmation
4. You'll be added to the rotation schedule

*What is a security deposit?*
It protects all members from losses. If someone defaults, their deposit covers it. Returned when the cycle completes successfully.
            """.strip()
            
            grid = button_manager.create_grid()
            for deposit in deposits[:3]:  # Show max 3 deposits
                grid.add_row([
                    button_manager.create_button(
                        f"💳 Pay {deposit['group_name'][:20]}", 
                        f"pay_deposit:{deposit['id']}", 
                        emoji="💳"
                    )
                ])
            
            grid.add_row([
                button_manager.create_button("📖 Learn More", "learn_security", emoji="📖"),
                button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
            ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await update.callback_query.edit_message_text(
            text=deposit_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error fetching pending deposits: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while fetching pending deposits. Please try again.",
            parse_mode="Markdown"
        )


async def handle_learn_security(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle learn about security deposits."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    security_text = """
🔒 *Understanding Security Deposits*

*What is a Security Deposit?*
A security deposit is money you pay upfront to protect all other members in your MyPoolr group. It's the foundation of our no-loss guarantee.

*How It Works:*

1️⃣ *Everyone Pays Upfront*
   • Before joining, you pay a security deposit
   • Amount is calculated to cover potential losses
   • Held securely until cycle completes

2️⃣ *Protection Against Defaults*
   • If someone doesn't pay their contribution
   • Their security deposit covers the missing amount
   • No other member loses money

3️⃣ *Account Lock-in*
   • After receiving your payout, you can't leave
   • Ensures you complete all your contributions
   • Prevents hit-and-run scenarios

4️⃣ *Deposit Return*
   • When the cycle completes successfully
   • Everyone gets their deposit back
   • Plus any interest earned (if applicable)

*Calculation Formula:*
Your deposit = (Total members - Your position) × Contribution amount

*Example:*
• 5 members, KES 1,000 contribution
• You're position #2
• Your deposit: (5-2) × 1,000 = KES 3,000

*Why This Amount?*
If you receive your payout and then default on all remaining contributions, your deposit covers exactly what you owe to other members.

*Key Benefits:*
✅ 100% protection for all members
✅ Mathematical guarantee of no losses
✅ Transparent and fair calculation
✅ Returned when cycle completes
✅ Creates trust and accountability

Ready to join with confidence?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💰 Pay Deposit", "pay_security_deposit", emoji="💰"),
        button_manager.create_button("❓ More Help", "help_security", emoji="❓")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=security_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_learn_mypoolr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle learn more about MyPoolr."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    learn_text = """
📖 *Learn About MyPoolr*

*What is MyPoolr?*
MyPoolr is a digital platform for managing savings groups (chamas) with complete security and transparency. It automates rotation management and ensures no member ever loses money.

*How It Works:*

1️⃣ *Create or Join a Group*
   • Set contribution amount and frequency
   • Define member limit and rotation schedule
   • Everyone pays a security deposit upfront

2️⃣ *Automated Rotation*
   • Members take turns receiving the pool
   • System tracks who pays and who receives
   • Notifications keep everyone informed

3️⃣ *Security Guarantee*
   • Security deposits protect against defaults
   • If someone doesn't pay, their deposit covers it
   • No member ever loses their own money

4️⃣ *Two-Party Confirmation*
   • Both sender and recipient confirm payments
   • Creates transparent audit trail
   • Prevents disputes and misunderstandings

5️⃣ *Account Lock-in*
   • After receiving payout, you can't leave early
   • Ensures everyone completes their obligations
   • Deposits returned when cycle completes

*Key Benefits:*
✅ 100% no-loss guarantee
✅ Automated management
✅ Transparent tracking
✅ Secure deposits
✅ Real-time notifications

Ready to create your first MyPoolr group?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🎯 Create Group", "create_mypoolr", emoji="🎯"),
        button_manager.create_button("🔗 Join Group", "join_via_link", emoji="🔗")
    ])
    grid.add_row([
        button_manager.create_button("❓ Help Center", "help_main", emoji="❓"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=learn_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_full_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle full report generation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    user_id = update.effective_user.id
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "⏳ *Generating Report...*\n\nPlease wait while we compile your complete MyPoolr report.",
        parse_mode="Markdown"
    )
    
    try:
        # Fetch comprehensive report data from backend
        result = await backend_client.get_full_report(user_id)
        
        if not result.get('success'):
            await update.callback_query.edit_message_text(
                "❌ Unable to generate report. Please try again.",
                parse_mode="Markdown"
            )
            return
        
        report_data = result.get('report', {})
        
        report_text = f"""
📊 *MyPoolr Complete Report*

*Account Summary:*
• Member since: {report_data.get('member_since', 'N/A')}
• Total groups: {report_data.get('total_groups', 0)}
• Active groups: {report_data.get('active_groups', 0)}
• Current tier: {report_data.get('tier', 'Starter')}

*Financial Overview:*
• Total contributed: KES {report_data.get('total_contributed', 0):,}
• Total received: KES {report_data.get('total_received', 0):,}
• Pending payments: KES {report_data.get('pending_payments', 0):,}
• Security deposits held: KES {report_data.get('deposits_held', 0):,}

*Payment Statistics:*
• On-time payments: {report_data.get('on_time_payments', 0)}
• Late payments: {report_data.get('late_payments', 0)}
• Payment success rate: {report_data.get('success_rate', 100)}%

*Upcoming Schedule:*
• Next contribution: {report_data.get('next_contribution', 'None')}
• Next payout: {report_data.get('next_payout', 'None')}

*Group Performance:*
• Completed cycles: {report_data.get('completed_cycles', 0)}
• Active cycles: {report_data.get('active_cycles', 0)}
• Average group size: {report_data.get('avg_group_size', 0)} members

Would you like to export this report?
        """.strip()
        
        grid = button_manager.create_grid()
        grid.add_row([
            button_manager.create_button("📄 Export PDF", "export_report_pdf", emoji="📄"),
            button_manager.create_button("📊 Export Excel", "export_report_excel", emoji="📊")
        ])
        grid.add_row([
            button_manager.create_button("📅 My Schedule", "my_schedule", emoji="📅"),
            button_manager.create_button("💰 Pending Payments", "pending_payments", emoji="💰")
        ])
        grid.add_row([
            button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
        ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await update.callback_query.edit_message_text(
            text=report_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error generating full report: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while generating the report. Please try again.",
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
        "creating": {
            "title": "🎯 Creating Groups",
            "content": """
*How to Create a MyPoolr Group*

*Step-by-Step Guide:*

1️⃣ *Basic Information*
   • Choose a memorable group name
   • Write a clear description
   • Select your country

2️⃣ *Financial Settings*
   • Set contribution amount
   • Choose rotation frequency (weekly/monthly)
   • Define member limit

3️⃣ *Tier Selection*
   • Choose your tier based on needs
   • Higher tiers = more members allowed
   • Upgrade anytime later

4️⃣ *Invite Members*
   • Share invitation link
   • Members join and pay deposits
   • Start when group is full

*Best Practices:*
• Only invite people you trust
• Set realistic contribution amounts
• Explain the security deposit clearly
• Start with smaller groups first

Ready to create your group?
            """
        },
        "joining": {
            "title": "❓ How Joining Works",
            "content": """
*Joining a MyPoolr Group*

*Two Ways to Join:*

1️⃣ **Invitation Link**
   • Admin shares a link
   • Click to view group details
   • Confirm to join

2️⃣ **Invitation Code**
   • Format: MYPOOLR-XXXXX-XXXXX
   • Enter code in the bot
   • View details and join

*What Happens Next:*

1. Review group details carefully
2. Pay security deposit (protects everyone)
3. Get assigned a position in rotation
4. Receive schedule and notifications
5. Start contributing when it's time

*Before Joining:*
✅ Verify you can afford contributions
✅ Understand the security deposit
✅ Check the rotation schedule
✅ Know the group admin
✅ Read the group rules

Questions? Contact the group admin!
            """
        },
        "troubleshoot": {
            "title": "🔧 Troubleshooting",
            "content": """
*Common Issues & Solutions*

*Payment Issues:*
❌ Payment not confirmed
   → Both parties must confirm
   → Check with recipient
   → Contact support if stuck

❌ M-Pesa payment failed
   → Check your balance
   → Verify phone number
   → Try again in a few minutes

*Account Issues:*
❌ Can't join group
   → Check invitation code
   → Verify group isn't full
   → Ensure you meet requirements

❌ Not receiving notifications
   → Check bot settings
   → Unblock the bot
   → Update notification preferences

*Group Issues:*
❌ Member not paying
   → Admin can send reminders
   → System tracks defaults
   → Security deposit covers it

❌ Wrong rotation schedule
   → Contact group admin
   → Admin can adjust schedule
   → Changes require member approval

*Still Having Issues?*
Contact our support team 24/7!
            """
        },
        "tiers": {
            "title": "💎 Tiers & Features",
            "content": """
*MyPoolr Tier System*

*🆓 Starter (Free)*
• 1 MyPoolr group
• Up to 10 members
• Basic notifications
• Community support

*⭐ Essential ($2/month)*
• 3 MyPoolr groups
• Up to 25 members per group
• Priority support
• Advanced notifications
• Payment reminders

*⭐⭐ Advanced ($5/month)*
• 10 MyPoolr groups
• Up to 50 members per group
• Custom rotation schedules
• Detailed analytics
• Export reports
• Priority support

*⭐⭐⭐ Extended ($10/month)*
• Unlimited MyPoolr groups
• Unlimited members
• White-label branding
• API access
• Dedicated support
• Custom integrations

*How to Upgrade:*
1. Go to Settings → Upgrade Tier
2. Select your desired tier
3. Pay via M-Pesa STK Push
4. Instant activation

Ready to unlock more features?
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


async def handle_export_specific(update: Update, context: ContextTypes.DEFAULT_TYPE, export_type: str) -> None:
    """Handle specific data export requests."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    export_titles = {
        "transactions": "📄 Transaction History",
        "groups": "📊 Group Reports",
        "security": "🔒 Security Records"
    }
    
    export_descriptions = {
        "transactions": "All your contributions, receipts, and payment confirmations",
        "groups": "Member lists, rotation schedules, and payment tracking",
        "security": "Deposit history, lock-in status, and security logs"
    }
    
    title = export_titles.get(export_type, "📊 Export Data")
    description = export_descriptions.get(export_type, "Your MyPoolr data")
    
    export_text = f"""
{title}

*What's Included:*
{description}

*Available Formats:*
• PDF - Best for viewing and printing
• CSV - Best for spreadsheets
• Excel - Best for analysis

*How It Works:*
1. Select your preferred format
2. We'll generate the file
3. Download link sent to you
4. Valid for 24 hours

*Privacy & Security:*
• Files are encrypted
• Only you can access them
• Automatically deleted after 24 hours

Select your preferred format:
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📄 PDF", f"export_{export_type}_pdf", emoji="📄"),
        button_manager.create_button("📊 CSV", f"export_{export_type}_csv", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("📈 Excel", f"export_{export_type}_excel", emoji="📈")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "export_data", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=export_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_export_report(update: Update, context: ContextTypes.DEFAULT_TYPE, format_type: str) -> None:
    """Handle report export in specific format."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    user_id = update.effective_user.id
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"⏳ *Generating {format_type.upper()} Report...*\n\nPlease wait while we prepare your file.",
        parse_mode="Markdown"
    )
    
    try:
        # Request report generation from backend
        result = await backend_client.generate_report(user_id, format_type)
        
        if result.get('success'):
            download_url = result.get('download_url')
            expires_at = result.get('expires_at', '24 hours')
            
            success_text = f"""
✅ *Report Generated Successfully!*

Your {format_type.upper()} report is ready for download.

*Download Link:*
{download_url}

*Important:*
• Link expires in {expires_at}
• File is encrypted and secure
• Only you can access this link

*What's Next?*
• Download the file to your device
• Review your MyPoolr data
• Share with your accountant if needed

Need another format?
            """.strip()
            
            grid = button_manager.create_grid()
            grid.add_row([
                button_manager.create_button("📄 PDF", "export_report_pdf", emoji="📄"),
                button_manager.create_button("📊 Excel", "export_report_excel", emoji="📊")
            ])
            grid.add_row([
                button_manager.create_button("📊 Full Report", "full_report", emoji="📊"),
                button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
            ])
            
            keyboard = button_manager.build_keyboard(grid)
            
            await update.callback_query.edit_message_text(
                text=success_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            error_msg = result.get('error', 'Unable to generate report')
            await update.callback_query.edit_message_text(
                f"❌ *Export Failed*\n\n{error_msg}\n\nPlease try again or contact support.",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await update.callback_query.edit_message_text(
            "❌ *Export Failed*\n\n"
            "An error occurred while generating the report. "
            "Please try again or contact support.",
            parse_mode="Markdown"
        )


async def handle_pay_specific_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle payment for a specific security deposit."""
    deposit_id = callback_data.split(":", 1)[1]
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    backend_client: BackendClient = context.bot_data.get("backend_client")
    
    await update.callback_query.answer()
    
    try:
        # Fetch deposit details from backend
        result = await backend_client.get_deposit_details(deposit_id)
        
        if not result.get('success'):
            await update.callback_query.edit_message_text(
                "❌ Unable to fetch deposit details. Please try again.",
                parse_mode="Markdown"
            )
            return
        
        deposit = result.get('deposit')
        
        payment_text = f"""
💰 *Pay Security Deposit*

*Group:* {deposit['group_name']}
*Amount:* KES {deposit['amount']:,}
*Due Date:* {deposit['due_date']}

*Payment Instructions:*

1️⃣ *Send via M-Pesa*
   • Paybill: {deposit.get('paybill', 'TBD')}
   • Account: {deposit.get('account', 'TBD')}
   • Amount: KES {deposit['amount']:,}

2️⃣ *Upload Receipt*
   • Take screenshot of M-Pesa message
   • Upload using button below
   • Include transaction code

3️⃣ *Wait for Confirmation*
   • Admin will verify payment
   • You'll receive notification
   • Then added to rotation schedule

*What is this deposit for?*
It protects all members from losses. If someone defaults, their deposit covers it. You get it back when the cycle completes.

Ready to pay?
        """.strip()
        
        grid = button_manager.create_grid()
        grid.add_row([
            button_manager.create_button("📤 Upload Receipt", f"upload_deposit_receipt:{deposit_id}", emoji="📤")
        ])
        grid.add_row([
            button_manager.create_button("📖 Learn More", "learn_security", emoji="📖"),
            button_manager.create_button("💰 All Deposits", "pay_security_deposit", emoji="💰")
        ])
        grid.add_row([
            button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
        ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await update.callback_query.edit_message_text(
            text=payment_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error fetching deposit details: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred. Please try again.",
            parse_mode="Markdown"
        )


async def handle_pricing_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pricing calculator for tier selection."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    calculator_text = """
💰 *Pricing Calculator*

Calculate the best tier for your needs!

*How many MyPoolr groups do you need?*

🆓 **1 group** → Starter (Free)
⭐ **2-3 groups** → Essential ($2/month)
⭐⭐ **4-10 groups** → Advanced ($5/month)
⭐⭐⭐ **Unlimited** → Extended ($10/month)

*How many members per group?*

🆓 **Up to 10** → Starter (Free)
⭐ **Up to 25** → Essential ($2/month)
⭐⭐ **Up to 50** → Advanced ($5/month)
⭐⭐⭐ **Unlimited** → Extended ($10/month)

*Do you need advanced features?*

📊 Analytics & Reports → Advanced or Extended
🎨 White-label branding → Extended only
🔌 API access → Extended only
👨‍💼 Dedicated support → Extended only

*Cost Comparison:*
• Essential: $24/year (save $0)
• Advanced: $60/year (save $0)
• Extended: $120/year (save $0)

*Annual billing available with 20% discount!*

Ready to upgrade?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("⭐ Essential", "select_tier:essential", emoji="⭐"),
        button_manager.create_button("⭐⭐ Advanced", "select_tier:advanced", emoji="⭐⭐")
    ])
    grid.add_row([
        button_manager.create_button("⭐⭐⭐ Extended", "select_tier:extended", emoji="⭐⭐⭐")
    ])
    grid.add_row([
        button_manager.create_button("📊 Compare Tiers", "compare_tiers", emoji="📊"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=calculator_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_contact_sales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle contact sales for enterprise inquiries."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    sales_text = f"""
💬 *Contact Sales Team*

Interested in Extended tier or enterprise solutions?

*Our Sales Team Can Help With:*
• Custom pricing for large organizations
• White-label branding options
• API integration support
• Dedicated account management
• Custom feature development
• Training and onboarding

*Contact Methods:*

📧 **Email**
sales@mypoolr.com
Response: Within 4 hours

💬 **Telegram**
@mypoolr_sales
Response: Within 1 hour

📞 **Phone**
+254-XXX-XXXXXX
Available: Mon-Fri, 9 AM - 6 PM EAT

*Schedule a Demo:*
Book a 30-minute demo to see MyPoolr in action and discuss your specific needs.

*Your Information:*
User ID: `{update.effective_user.id}`
Current Tier: Starter

Ready to scale your savings groups?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📅 Schedule Demo", "schedule_demo", emoji="📅"),
        button_manager.create_button("📧 Email Sales", "email_sales", emoji="📧")
    ])
    grid.add_row([
        button_manager.create_button("💎 View Tiers", "upgrade_tier", emoji="💎"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=sales_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_feature_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle detailed feature comparison."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    features_text = """
📋 *Detailed Feature Comparison*

*Core Features (All Tiers):*
✅ Security deposit system
✅ Two-party confirmation
✅ Automated rotation
✅ Basic notifications
✅ Payment tracking
✅ No-loss guarantee

*Essential Tier ($2/month):*
✅ All core features
✅ 3 MyPoolr groups
✅ 25 members per group
✅ Priority support
✅ Advanced notifications
✅ Payment reminders
✅ Email notifications

*Advanced Tier ($5/month):*
✅ All Essential features
✅ 10 MyPoolr groups
✅ 50 members per group
✅ Custom rotation schedules
✅ Detailed analytics
✅ Export reports (PDF, Excel)
✅ Payment history tracking
✅ Member performance stats

*Extended Tier ($10/month):*
✅ All Advanced features
✅ Unlimited MyPoolr groups
✅ Unlimited members
✅ White-label branding
✅ API access
✅ Dedicated support
✅ Custom integrations
✅ Advanced security features
✅ Priority feature requests

*Support Levels:*
🆓 Starter: Community support
⭐ Essential: Priority email support
⭐⭐ Advanced: Priority email + chat
⭐⭐⭐ Extended: Dedicated account manager

Ready to choose your tier?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💰 Pricing Calculator", "pricing_calculator", emoji="💰"),
        button_manager.create_button("💎 Upgrade Now", "upgrade_tier", emoji="💎")
    ])
    grid.add_row([
        button_manager.create_button("💬 Contact Sales", "contact_sales", emoji="💬"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=features_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ============================================================================
# CONVERSATION AND CREATION HANDLERS
# ============================================================================

async def handle_start_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle starting MyPoolr creation flow."""
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    if state_manager:
        state_manager.start_conversation(user_id, ConversationState.CREATING_MYPOOLR)
    
    await update.callback_query.edit_message_text(
        "🎯 *Let's Create Your MyPoolr!*\n\n"
        "Please send me the name for your MyPoolr group.\n\n"
        "*Example:* Office Savings, Family Circle, Friends Chama",
        parse_mode="Markdown"
    )


async def handle_confirm_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle confirming MyPoolr creation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    await update.callback_query.answer("Creating your MyPoolr...")
    await update.callback_query.edit_message_text(
        "⏳ *Creating Your MyPoolr...*\n\nPlease wait while we set up your group.",
        parse_mode="Markdown"
    )
    # Actual creation logic would be in conversation handler


async def handle_cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle canceling MyPoolr creation."""
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    if state_manager:
        state_manager.end_conversation(user_id)
    
    await handle_main_menu(update, context)


async def handle_edit_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle editing MyPoolr details during creation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    edit_text = """
✏️ *Edit MyPoolr Details*

What would you like to change?

*Current Details:*
• Name: Office Savings
• Amount: KES 5,000
• Frequency: Monthly
• Members: 10
• Country: Kenya

Select what to edit:
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📝 Name", "back_to_name", emoji="📝"),
        button_manager.create_button("💰 Amount", "back_to_amount", emoji="💰")
    ])
    grid.add_row([
        button_manager.create_button("📅 Frequency", "back_to_frequency", emoji="📅"),
        button_manager.create_button("👥 Members", "back_to_members", emoji="👥")
    ])
    grid.add_row([
        button_manager.create_button("🌍 Country", "back_to_country", emoji="🌍"),
        button_manager.create_button("💎 Tier", "back_to_tier", emoji="💎")
    ])
    grid.add_row([
        button_manager.create_button("✅ Looks Good", "confirm_create", emoji="✅"),
        button_manager.create_button("❌ Cancel", "cancel_creation", emoji="❌")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=edit_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_back_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle back navigation during creation flow."""
    field = callback_data.replace("back_to_", "")
    
    messages = {
        "name": "📝 Please send me the new group name:",
        "amount": "💰 Please send me the new contribution amount (e.g., 5000):",
        "frequency": "📅 Please select the new frequency:",
        "members": "👥 Please send me the new member limit (e.g., 10):",
        "country": "🌍 Please select the new country:",
        "tier": "💎 Please select the new tier:"
    }
    
    await update.callback_query.edit_message_text(
        messages.get(field, "Please provide the new value:"),
        parse_mode="Markdown"
    )


# ============================================================================
# BILLING AND PAYMENT HANDLERS
# ============================================================================

async def handle_billing_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle billing history display."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    billing_text = """
💳 *Billing History*

*Recent Transactions:*

📅 **January 2024**
• Tier: Starter (Free)
• Amount: KES 0
• Status: ✅ Active

📅 **December 2023**
• Tier: Starter (Free)
• Amount: KES 0
• Status: ✅ Active

*Payment Method:*
• M-Pesa: +254-XXX-XXXXXX

*Next Billing Date:*
• N/A (Free tier)

Upgrade to access premium features!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💎 Upgrade Tier", "upgrade_tier", emoji="💎"),
        button_manager.create_button("💳 Update Payment", "update_payment_method", emoji="💳")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "settings", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=billing_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_billing_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle billing alerts settings."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    alerts_text = """
🔔 *Billing Alerts*

*Current Settings:*
• Payment reminders: ✅ Enabled
• Failed payment alerts: ✅ Enabled
• Renewal reminders: ✅ Enabled
• Receipt notifications: ✅ Enabled

*Alert Timing:*
• 7 days before renewal
• 3 days before renewal
• 1 day before renewal
• On payment failure

*Notification Channels:*
• Telegram: ✅ Active
• Email: ❌ Not configured

Stay informed about your billing!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("⚙️ Configure Alerts", "notification_settings", emoji="⚙️"),
        button_manager.create_button("📧 Add Email", "email_support", emoji="📧")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "billing_history", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=alerts_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_billing_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle billing support."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    support_text = f"""
💬 *Billing Support*

Need help with billing or payments?

*Common Issues:*
• Payment failed or declined
• Incorrect billing amount
• Refund requests
• Subscription cancellation
• Payment method updates

*Contact Billing Support:*
📧 billing@mypoolr.com
💬 @mypoolr_billing

*Your Information:*
• User ID: `{update.effective_user.id}`
• Current Tier: Starter (Free)
• Payment Status: N/A

*Response Time:*
• Standard: 2-4 hours
• Urgent: 30 minutes

We're here to help!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📧 Email Support", "email_support", emoji="📧"),
        button_manager.create_button("💬 Chat Support", "telegram_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "billing_history", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=support_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment cancellation."""
    await update.callback_query.answer("Payment cancelled")
    await handle_main_menu(update, context)


async def handle_cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription cancellation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    cancel_text = """
⚠️ *Cancel Subscription*

Are you sure you want to cancel your subscription?

*What happens when you cancel:*
• Access to premium features ends
• Downgrade to Starter (Free) tier
• Existing groups remain active
• No refund for current period

*You'll lose access to:*
• Multiple MyPoolr groups
• Advanced analytics
• Priority support
• Export features

Consider downgrading instead of canceling!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💎 Downgrade Instead", "downgrade_tier", emoji="💎"),
        button_manager.create_button("❌ Confirm Cancel", "confirm_cancel_subscription", emoji="❌")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Keep Subscription", "billing_history", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=cancel_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_auto_renewal_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle auto-renewal settings."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    renewal_text = """
🔄 *Auto-Renewal Settings*

*Current Status:*
• Auto-renewal: ✅ Enabled
• Next renewal: N/A (Free tier)
• Payment method: M-Pesa

*How Auto-Renewal Works:*
1. We charge your payment method automatically
2. You receive a receipt via Telegram
3. Your subscription continues uninterrupted
4. You can cancel anytime

*Benefits:*
• Never lose access to features
• No manual payment required
• Automatic receipt generation
• Cancel anytime, no penalties

*Manage Your Subscription:*
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔴 Disable Auto-Renewal", "disable_auto_renewal", emoji="🔴"),
        button_manager.create_button("💳 Update Payment", "update_payment_method", emoji="💳")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "billing_history", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=renewal_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_update_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment method update."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    payment_text = """
💳 *Update Payment Method*

*Current Payment Method:*
• M-Pesa: +254-XXX-XXXXXX

*Available Payment Methods:*

📱 **M-Pesa (Kenya)**
   • Instant processing
   • STK Push supported
   • Most popular

🏦 **Bank Transfer**
   • Manual processing
   • 1-2 business days
   • All Kenyan banks

💳 **Credit/Debit Card**
   • Coming soon
   • International payments
   • Secure processing

*To Update:*
Please send your new M-Pesa number in the format: +254XXXXXXXXX
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("⬅️ Back", "billing_history", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=payment_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_view_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle viewing payment trends and analytics."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    trends_text = """
📈 *Payment Trends & Analytics*

*Monthly Payment Performance:*
• January: 98% on-time payments
• February: 95% on-time payments  
• March: 97% on-time payments
• Average: 96.7% success rate

*Group Performance Trends:*
• Office Savings: 100% completion rate
• Family Circle: 95% completion rate
• Friends Group: 92% completion rate

*Payment Method Trends:*
• M-Pesa: 85% of payments
• Bank Transfer: 12% of payments
• Cash: 3% of payments

*Peak Payment Days:*
• Monday: 35% of payments
• Friday: 28% of payments
• Tuesday: 20% of payments

*Seasonal Patterns:*
• End of month: Higher payment volumes
• Holiday periods: Slight delays
• Salary weeks: Faster payments

*Recommendations:*
• Schedule payments after salary days
• Send reminders 2 days before due date
• Consider flexible payment windows during holidays

Want detailed analytics for your groups?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📊 Detailed Analytics", "detailed_analytics", emoji="📊"),
        button_manager.create_button("📈 Payment Analytics", "payment_analytics", emoji="📈")
    ])
    grid.add_row([
        button_manager.create_button("📋 Export Report", "export_stats_report", emoji="📋"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=trends_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_confirm_cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription cancellation confirmation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    cancel_text = """
⚠️ *Confirm Subscription Cancellation*

Are you sure you want to cancel your subscription?

*What happens when you cancel:*
• Your subscription will end at the current billing period
• You'll lose access to premium features
• Your groups will be limited to Starter tier limits
• No refund for the current billing period

*Current Subscription:*
• Tier: Advanced ($5/month)
• Next billing: March 15, 2024
• Features: 10 groups, 50 members each, analytics

*Alternative Options:*
• Downgrade to Essential ($2/month)
• Pause subscription for 1-3 months
• Switch to annual billing (20% discount)

*If you're having issues:*
Contact our support team - we're here to help!

Are you sure you want to proceed with cancellation?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("❌ Yes, Cancel", "process_cancellation", emoji="❌"),
        button_manager.create_button("⏸️ Pause Instead", "pause_subscription", emoji="⏸️")
    ])
    grid.add_row([
        button_manager.create_button("📉 Downgrade", "downgrade_tier", emoji="📉"),
        button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Keep Subscription", "billing_history", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=cancel_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_change_billing_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle changing billing date."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    billing_date_text = """
📅 *Change Billing Date*

*Current Billing Date:* 15th of each month
*Next Billing:* March 15, 2024

*Available Billing Dates:*
Choose a date that works best for your budget:

• 1st of month - Right after salary
• 5th of month - Early month
• 15th of month - Mid-month (current)
• 25th of month - End of month

*Important Notes:*
• Changes take effect from next billing cycle
• Prorated charges may apply for partial months
• You'll receive confirmation email
• Auto-renewal continues with new date

*Why change billing date?*
• Align with salary schedule
• Better cash flow management
• Avoid end-of-month expenses

Select your preferred billing date:
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("1️⃣ 1st of Month", "set_billing_date:1", emoji="1️⃣"),
        button_manager.create_button("5️⃣ 5th of Month", "set_billing_date:5", emoji="5️⃣")
    ])
    grid.add_row([
        button_manager.create_button("🔄 15th (Current)", "set_billing_date:15", emoji="🔄"),
        button_manager.create_button("2️⃣5️⃣ 25th of Month", "set_billing_date:25", emoji="2️⃣5️⃣")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "auto_renewal_settings", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=billing_date_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_confirm_disable_renewal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle confirming auto-renewal disable."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "⏳ *Processing...*\n\nDisabling auto-renewal for your subscription.",
        parse_mode="Markdown"
    )
    
    # Simulate processing delay
    import asyncio
    await asyncio.sleep(2)
    
    success_text = """
✅ *Auto-Renewal Disabled*

Your auto-renewal has been successfully disabled.

*What this means:*
• Your subscription will end on March 15, 2024
• No automatic charges will occur
• You'll receive reminders before expiration
• You can manually renew anytime

*Important Reminders:*
• 7 days before expiration
• 3 days before expiration  
• 1 day before expiration

*To reactivate auto-renewal:*
Go to Settings → Billing → Auto-Renewal Settings

*Need help?*
Contact our support team anytime.

Thank you for using MyPoolr!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔄 Reactivate Auto-Renewal", "auto_renewal_settings", emoji="🔄"),
        button_manager.create_button("📊 Billing History", "billing_history", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=success_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_pause_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pausing subscription instead of canceling."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    pause_text = """
⏸️ *Pause Subscription*

Instead of canceling, you can pause your subscription temporarily.

*Pause Options:*

🗓️ **1 Month Pause**
• Resume: April 15, 2024
• Cost: Free
• Keep all data and settings

🗓️ **2 Month Pause**  
• Resume: May 15, 2024
• Cost: Free
• Keep all data and settings

🗓️ **3 Month Pause**
• Resume: June 15, 2024
• Cost: Free
• Keep all data and settings

*During the pause:*
• No charges to your account
• Groups limited to Starter features
• Data and settings preserved
• Easy reactivation anytime

*Benefits vs Cancellation:*
• No need to re-setup everything
• Instant reactivation
• Same pricing when you return
• All your groups remain intact

How long would you like to pause?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("1️⃣ 1 Month", "pause_for:1", emoji="1️⃣"),
        button_manager.create_button("2️⃣ 2 Months", "pause_for:2", emoji="2️⃣")
    ])
    grid.add_row([
        button_manager.create_button("3️⃣ 3 Months", "pause_for:3", emoji="3️⃣")
    ])
    grid.add_row([
        button_manager.create_button("❌ Cancel Instead", "confirm_cancel_subscription", emoji="❌"),
        button_manager.create_button("⬅️ Keep Active", "billing_history", emoji="⬅️")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=pause_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_pause_for(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle pausing subscription for specific duration."""
    months = callback_data.split(":")[1]
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"⏳ *Processing...*\n\nPausing your subscription for {months} month(s).",
        parse_mode="Markdown"
    )
    
    # Simulate processing delay
    import asyncio
    await asyncio.sleep(2)
    
    from datetime import datetime, timedelta
    resume_date = datetime.now() + timedelta(days=30 * int(months))
    
    pause_success_text = f"""
✅ *Subscription Paused*

Your subscription has been successfully paused for {months} month(s).

*Pause Details:*
• Pause Duration: {months} month(s)
• Resume Date: {resume_date.strftime('%B %d, %Y')}
• Cost: Free
• Status: Active until current period ends

*During the pause:*
• No charges to your account
• Groups limited to Starter features (1 group, 10 members)
• All data and settings preserved
• Easy reactivation anytime

*To reactivate early:*
Go to Settings → Billing → Reactivate Subscription

*Reminder:*
We'll send you a reminder 3 days before auto-resumption.

Thank you for staying with MyPoolr!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔄 Reactivate Now", "reactivate_subscription", emoji="🔄"),
        button_manager.create_button("📊 Billing History", "billing_history", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("📧 Email Confirmation", "email_pause_confirmation", emoji="📧"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=pause_success_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_set_billing_date(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle setting new billing date."""
    date = callback_data.split(":")[1]
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"⏳ *Processing...*\n\nChanging your billing date to the {date}th of each month.",
        parse_mode="Markdown"
    )
    
    # Simulate processing delay
    import asyncio
    await asyncio.sleep(2)
    
    date_success_text = f"""
✅ *Billing Date Updated*

Your billing date has been successfully changed.

*New Billing Schedule:*
• Billing Date: {date}th of each month
• Next Billing: {date}th of next month
• Prorated Charge: $0.00 (no partial month)

*What this means:*
• Your subscription will renew on the {date}th
• Auto-renewal continues with new date
• Same pricing and features
• Confirmation email sent

*Benefits:*
• Better aligned with your budget
• Consistent monthly billing
• Easy to remember date

*Need to change again?*
You can update your billing date anytime in settings.

Thank you for using MyPoolr!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📊 Billing History", "billing_history", emoji="📊"),
        button_manager.create_button("⚙️ Auto-Renewal", "auto_renewal_settings", emoji="⚙️")
    ])
    grid.add_row([
        button_manager.create_button("📧 Email Confirmation", "email_billing_change", emoji="📧"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=date_success_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_reactivate_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription reactivation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    reactivate_text = """
🔄 *Reactivate Subscription*

Welcome back! We're glad you want to continue with MyPoolr.

*Reactivation Options:*

💎 **Resume Previous Tier**
• Tier: Advanced ($5/month)
• Features: 10 groups, 50 members, analytics
• Billing: Same date as before

💎 **Choose Different Tier**
• Essential: $2/month (3 groups, 25 members)
• Advanced: $5/month (10 groups, 50 members)  
• Extended: $10/month (unlimited)

*Immediate Benefits:*
• Instant access to premium features
• All your groups and data restored
• No setup required
• Same pricing as before

*Billing:*
• First charge: Today (prorated if needed)
• Next billing: Your regular billing date
• Auto-renewal: Enabled (can be changed)

Ready to reactivate your subscription?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("✅ Resume Advanced", "confirm_reactivate:advanced", emoji="✅"),
        button_manager.create_button("💎 Choose Tier", "upgrade_tier", emoji="💎")
    ])
    grid.add_row([
        button_manager.create_button("❓ Questions?", "billing_support", emoji="❓"),
        button_manager.create_button("⬅️ Back", "billing_history", emoji="⬅️")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=reactivate_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_cancellation_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cancellation feedback collection."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    feedback_text = """
💬 *Cancellation Feedback*

Help us improve MyPoolr by sharing why you cancelled.

*Common Reasons:*

💰 **Too Expensive**
• We offer lower-cost tiers
• Annual billing saves 20%
• Student discounts available

🔧 **Missing Features**
• Tell us what you need
• We're constantly improving
• Feature requests are prioritized

⏰ **Not Using Enough**
• Pause instead of cancel
• We can help optimize usage
• Training resources available

🤝 **Found Alternative**
• We'd love to compete
• What features attracted you?
• How can we improve?

*Your feedback helps us:*
• Improve our service
• Add requested features
• Better serve our community

What was your main reason for cancelling?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💰 Too Expensive", "feedback:expensive", emoji="💰"),
        button_manager.create_button("🔧 Missing Features", "feedback:features", emoji="🔧")
    ])
    grid.add_row([
        button_manager.create_button("⏰ Not Using", "feedback:usage", emoji="⏰"),
        button_manager.create_button("🤝 Found Alternative", "feedback:alternative", emoji="🤝")
    ])
    grid.add_row([
        button_manager.create_button("📝 Other Reason", "feedback:other", emoji="📝"),
        button_manager.create_button("⏭️ Skip Feedback", "billing_history", emoji="⏭️")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=feedback_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_confirm_reactivate(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle confirming subscription reactivation."""
    tier = callback_data.split(":")[1]
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"⏳ *Processing Reactivation...*\n\nReactivating your {tier.title()} subscription.",
        parse_mode="Markdown"
    )
    
    # Simulate processing delay
    import asyncio
    await asyncio.sleep(3)
    
    tier_prices = {"essential": 2, "advanced": 5, "extended": 10}
    price = tier_prices.get(tier, 5)
    
    reactivation_success_text = f"""
✅ *Subscription Reactivated*

Welcome back! Your subscription has been successfully reactivated.

*Reactivation Details:*
• Tier: {tier.title()} (${price}/month)
• Status: Active immediately
• First charge: Today (${price}.00)
• Next billing: Same date as before

*Restored Features:*
• All premium features unlocked
• Your groups and data restored
• Full access to analytics
• Priority support included

*What's Next:*
• All your MyPoolr groups are now active
• Premium features are immediately available
• Billing resumes on your regular schedule
• Welcome back email sent

*Need Help?*
Our support team is here to help you get back up and running.

Thank you for choosing MyPoolr again!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📊 View My Groups", "my_groups", emoji="📊"),
        button_manager.create_button("💎 Tier Features", "feature_details", emoji="💎")
    ])
    grid.add_row([
        button_manager.create_button("📧 Email Confirmation", "email_reactivation_confirmation", emoji="📧"),
        button_manager.create_button("⚙️ Billing Settings", "billing_history", emoji="⚙️")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=reactivation_success_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_email_billing_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle emailing billing change confirmation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📧 *Sending Confirmation...*\n\nPreparing your billing change confirmation email.",
        parse_mode="Markdown"
    )
    
    # Simulate email sending delay
    import asyncio
    await asyncio.sleep(2)
    
    email_sent_text = f"""
✅ *Confirmation Email Sent*

Your billing change confirmation has been sent successfully.

*Email Details:*
• Sent to: {user.first_name.lower()}@example.com
• Subject: Billing Date Changed - MyPoolr
• Reference: BILLING-{user.id}-2024
• Sent: Just now

*Email Contains:*
• New billing date confirmation
• Next billing amount and date
• Payment method on file
• How to make changes

*Didn't receive it?*
• Check your spam/junk folder
• Verify email address in settings
• Email may take up to 5 minutes to arrive

*Need to Update Email?*
You can change your email address in account settings.

Is there anything else you need help with?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📧 Update Email", "update_email_address", emoji="📧"),
        button_manager.create_button("🔄 Resend Email", "resend_billing_confirmation", emoji="🔄")
    ])
    grid.add_row([
        button_manager.create_button("⚙️ Billing Settings", "billing_history", emoji="⚙️"),
        button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=email_sent_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_email_pause_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle emailing pause confirmation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📧 *Sending Confirmation...*\n\nPreparing your subscription pause confirmation email.",
        parse_mode="Markdown"
    )
    
    # Simulate email sending delay
    import asyncio
    await asyncio.sleep(2)
    
    pause_email_text = f"""
✅ *Pause Confirmation Sent*

Your subscription pause confirmation has been sent successfully.

*Email Details:*
• Sent to: {user.first_name.lower()}@example.com
• Subject: Subscription Paused - MyPoolr
• Reference: PAUSE-{user.id}-2024
• Sent: Just now

*Email Contains:*
• Pause duration and resume date
• What happens during the pause
• How to reactivate early
• Important reminders

*Pause Summary:*
• Status: Paused successfully
• Resume: Automatic on scheduled date
• Features: Limited to Starter tier
• Data: Safely preserved

*Important Reminders:*
• We'll email you 3 days before auto-resume
• You can reactivate anytime in settings
• All your data remains safe

Need anything else?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔄 Reactivate Now", "reactivate_subscription", emoji="🔄"),
        button_manager.create_button("📧 Update Email", "update_email_address", emoji="📧")
    ])
    grid.add_row([
        button_manager.create_button("⚙️ Billing Settings", "billing_history", emoji="⚙️"),
        button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=pause_email_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_feedback_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle feedback submission."""
    feedback_type = callback_data.split(":")[1]
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    feedback_responses = {
        "expensive": {
            "title": "💰 Cost Feedback",
            "message": "We understand cost is important. Here are some options:",
            "suggestions": [
                "• Switch to Essential tier ($2/month)",
                "• Annual billing saves 20%",
                "• Student discounts available",
                "• Pause subscription temporarily"
            ]
        },
        "features": {
            "title": "🔧 Feature Feedback", 
            "message": "We're always improving! What features would help?",
            "suggestions": [
                "• Tell us what you need most",
                "• Feature requests are prioritized",
                "• Many features come from user feedback",
                "• We release updates monthly"
            ]
        },
        "usage": {
            "title": "⏰ Usage Feedback",
            "message": "We can help you get more value from MyPoolr:",
            "suggestions": [
                "• Free training sessions available",
                "• Usage optimization tips",
                "• Pause instead of cancel",
                "• Lower tier might be better fit"
            ]
        },
        "alternative": {
            "title": "🤝 Alternative Feedback",
            "message": "We'd love to compete! What attracted you elsewhere?",
            "suggestions": [
                "• Tell us what features they have",
                "• We often match or beat competitors",
                "• Your feedback helps us improve",
                "• Consider giving us another chance"
            ]
        },
        "other": {
            "title": "📝 Other Feedback",
            "message": "Thank you for taking the time to share feedback.",
            "suggestions": [
                "• Your input helps us improve",
                "• We review all feedback carefully",
                "• Consider contacting support directly",
                "• We're always here to help"
            ]
        }
    }
    
    feedback = feedback_responses.get(feedback_type, feedback_responses["other"])
    
    feedback_text = f"""
{feedback['title']}

{feedback['message']}

{chr(10).join(feedback['suggestions'])}

*What's Next:*
• Your feedback has been recorded
• Our team will review it carefully
• We may follow up with questions
• Thank you for helping us improve

*Still Want to Cancel?*
Your cancellation is already processed, but we're here if you change your mind.

*Contact Us:*
If you'd like to discuss this further, our support team is available 24/7.
    """.strip()
    
    grid = button_manager.create_grid()
    
    if feedback_type == "expensive":
        grid.add_row([
            button_manager.create_button("💎 View Lower Tiers", "upgrade_tier", emoji="💎"),
            button_manager.create_button("⏸️ Pause Instead", "pause_subscription", emoji="⏸️")
        ])
    elif feedback_type == "features":
        grid.add_row([
            button_manager.create_button("📝 Request Feature", "feature_request", emoji="📝"),
            button_manager.create_button("🔄 Reactivate", "reactivate_subscription", emoji="🔄")
        ])
    else:
        grid.add_row([
            button_manager.create_button("🔄 Reactivate", "reactivate_subscription", emoji="🔄"),
            button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬")
        ])
    
    grid.add_row([
        button_manager.create_button("📊 Billing History", "billing_history", emoji="📊"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=feedback_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_resend_cancellation_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle resending cancellation receipt."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📧 *Resending Receipt...*\n\nSending your cancellation receipt again.",
        parse_mode="Markdown"
    )
    
    # Simulate email sending delay
    import asyncio
    await asyncio.sleep(2)
    
    resend_text = f"""
✅ *Receipt Resent Successfully*

Your cancellation receipt has been sent again to your email.

*Resend Details:*
• Sent to: {user.first_name.lower()}@example.com
• Time: Just now
• Reference: CANCEL-{user.id}-2024-RESEND
• Status: Delivered

*If you still don't receive it:*
• Check spam/junk folder thoroughly
• Email may take up to 10 minutes
• Verify your email address is correct
• Contact support for alternative delivery

*Receipt Contains:*
• Cancellation confirmation details
• Final billing information
• Data retention policy (90 days)
• Reactivation instructions

*Alternative Options:*
• Download receipt directly from billing history
• Request receipt via SMS
• Contact support for printed copy

Need any other assistance?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📧 Update Email", "update_email_address", emoji="📧"),
        button_manager.create_button("📱 SMS Receipt", "sms_receipt", emoji="📱")
    ])
    grid.add_row([
        button_manager.create_button("📊 Billing History", "billing_history", emoji="📊"),
        button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=resend_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_email_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle email preferences settings."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    email_prefs_text = """
📧 *Email Preferences*

Customize what emails you receive from MyPoolr.

*Current Settings:*

🔔 **Notifications**
• Payment reminders: ✅ Enabled
• Group invitations: ✅ Enabled
• Security alerts: ✅ Enabled
• System updates: ✅ Enabled

📊 **Reports & Receipts**
• Monthly reports: ✅ Enabled
• Payment receipts: ✅ Enabled
• Export confirmations: ✅ Enabled
• Billing statements: ✅ Enabled

📢 **Marketing & Updates**
• Feature announcements: ❌ Disabled
• Tips and tutorials: ✅ Enabled
• Promotional offers: ❌ Disabled
• Newsletter: ❌ Disabled

⏰ **Frequency Settings**
• Immediate: Critical alerts
• Daily digest: Non-urgent notifications
• Weekly summary: Activity reports

*Email Address:* user@example.com ✅ Verified

Customize your email preferences below:
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔔 Notifications", "email_notifications_settings", emoji="🔔"),
        button_manager.create_button("📊 Reports", "email_reports_settings", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("📢 Marketing", "email_marketing_settings", emoji="📢"),
        button_manager.create_button("⏰ Frequency", "email_frequency_settings", emoji="⏰")
    ])
    grid.add_row([
        button_manager.create_button("📧 Change Email", "update_email_address", emoji="📧"),
        button_manager.create_button("🔕 Unsubscribe All", "unsubscribe_all_emails", emoji="🔕")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "settings", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=email_prefs_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_email_reactivation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sending reactivation confirmation email."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📧 *Sending Confirmation...*\n\nPreparing your reactivation confirmation email.",
        parse_mode="Markdown"
    )
    
    # Simulate email sending delay
    import asyncio
    await asyncio.sleep(2)
    
    reactivation_email_text = f"""
✅ *Reactivation Confirmation Sent*

Your subscription reactivation confirmation has been sent successfully.

*Email Details:*
• Sent to: {user.first_name.lower()}@example.com
• Subject: Welcome Back - Subscription Reactivated
• Reference: REACTIVATE-{user.id}-2024
• Sent: Just now

*Email Contains:*
• Reactivation confirmation
• Tier details and features
• Billing information
• Next steps and tips

*What's Included:*
• Your new tier benefits
• Billing schedule and amount
• Feature access confirmation
• Getting started guide

*Welcome Back Package:*
• 7-day premium support
• Free optimization consultation
• Exclusive reactivation tips
• Priority feature requests

*Need Help Getting Started?*
Our team is ready to help you make the most of your subscription.

Enjoy your MyPoolr experience!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📊 View My Groups", "my_groups", emoji="📊"),
        button_manager.create_button("💎 Explore Features", "feature_details", emoji="💎")
    ])
    grid.add_row([
        button_manager.create_button("📧 Email Settings", "email_preferences", emoji="📧"),
        button_manager.create_button("💬 Get Help", "contact_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=reactivation_email_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_feature_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feature request submission."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    feature_request_text = """
📝 *Request a Feature*

Help us improve MyPoolr by suggesting new features!

*How Feature Requests Work:*
1. Submit your idea below
2. Our team reviews all requests
3. Popular requests get prioritized
4. You'll be notified when implemented

*Popular Recent Requests:*
• Multi-currency support ✅ (Implemented)
• Mobile app notifications ✅ (Implemented)
• Advanced analytics 🔄 (In development)
• Custom rotation schedules ✅ (Implemented)

*What Makes a Good Request:*
• Clear description of the feature
• Explain how it would help you
• Provide specific use cases
• Mention if others would benefit

*Feature Categories:*
• Payment & Billing improvements
• Group management enhancements
• Analytics & reporting features
• Mobile app functionality
• Integration with other services

*Your Voice Matters:*
Many of our best features came from user suggestions. We read every request and prioritize based on user needs.

Ready to share your idea?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("💰 Payment Features", "request_payment_feature", emoji="💰"),
        button_manager.create_button("👥 Group Features", "request_group_feature", emoji="👥")
    ])
    grid.add_row([
        button_manager.create_button("📊 Analytics Features", "request_analytics_feature", emoji="📊"),
        button_manager.create_button("📱 Mobile Features", "request_mobile_feature", emoji="📱")
    ])
    grid.add_row([
        button_manager.create_button("📝 Custom Request", "submit_custom_request", emoji="📝"),
        button_manager.create_button("👀 View Roadmap", "view_feature_roadmap", emoji="👀")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "cancellation_feedback", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=feature_request_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_prompt_new_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle prompting for new email address."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    # Set conversation state to expect email input
    if state_manager:
        state_manager.start_conversation(user_id, "awaiting_new_email")
    
    prompt_text = """
📧 *Enter New Email Address*

Please send your new email address as a message.

*Requirements:*
• Valid email format (user@domain.com)
• Must be accessible to you
• Will be used for all notifications
• Verification required

*What Happens Next:*
1. Send your new email as a message
2. We'll send a verification link
3. Click the link to confirm
4. Email updated instantly

*Security:*
• Verification sent to new email
• Confirmation sent to old email
• Change takes effect immediately
• You can update anytime

*Examples:*
• john.doe@gmail.com
• mary@company.com
• user123@outlook.com

*Privacy:*
Your email is never shared and only used for MyPoolr notifications.

Please type your new email address:
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("❌ Cancel", "update_email_address", emoji="❌"),
        button_manager.create_button("❓ Help", "email_help", emoji="❓")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=prompt_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_resend_billing_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle resending billing confirmation email."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📧 *Resending Confirmation...*\n\nSending your billing confirmation email again.",
        parse_mode="Markdown"
    )
    
    # Simulate email sending delay
    import asyncio
    await asyncio.sleep(2)
    
    resend_billing_text = f"""
✅ *Billing Confirmation Resent*

Your billing confirmation has been sent again successfully.

*Resend Details:*
• Sent to: {user.first_name.lower()}@example.com
• Time: Just now
• Reference: BILLING-{user.id}-2024-RESEND
• Status: Delivered

*Email Contains:*
• Updated billing date confirmation
• Next payment amount and date
• Payment method on file
• How to make future changes

*If You Still Don't Receive It:*
• Check spam/junk folder carefully
• Email may take up to 10 minutes
• Verify email address is correct
• Try whitelisting support@mypoolr.com

*Alternative Delivery:*
• SMS notification available
• In-app notification sent
• Download from billing history

*Need More Help?*
Our support team can assist with email delivery issues.

Is there anything else you need?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📧 Update Email", "update_email_address", emoji="📧"),
        button_manager.create_button("📱 SMS Notification", "sms_billing_confirmation", emoji="📱")
    ])
    grid.add_row([
        button_manager.create_button("📊 Billing History", "billing_history", emoji="📊"),
        button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=resend_billing_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_sms_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle SMS receipt delivery."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    sms_receipt_text = f"""
📱 *SMS Receipt Delivery*

Get your receipt via SMS text message.

*SMS Delivery Details:*
• Phone: +254-XXX-XXX-{str(user.id)[-4:]}
• Cost: Free
• Delivery: Within 5 minutes
• Format: Short summary + download link

*What You'll Receive:*
• Receipt reference number
• Transaction amount and date
• Download link for full receipt
• Support contact information

*SMS Content Example:*
"MyPoolr Receipt CANCEL-{user.id}: Subscription cancelled. Full receipt: bit.ly/receipt123. Support: +254-XXX-XXXX"

*Requirements:*
• Valid phone number on file
• SMS service available in your region
• Phone must be able to receive texts

*Privacy & Security:*
• SMS contains no sensitive information
• Download link expires in 24 hours
• Only basic transaction details included

Ready to send your receipt via SMS?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📱 Send SMS", "confirm_sms_receipt", emoji="📱"),
        button_manager.create_button("📞 Update Phone", "update_phone_number", emoji="📞")
    ])
    grid.add_row([
        button_manager.create_button("📧 Email Instead", "resend_cancellation_receipt", emoji="📧"),
        button_manager.create_button("📊 Billing History", "billing_history", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "resend_cancellation_receipt", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=sms_receipt_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_verify_current_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle verifying current email address."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📧 *Sending Verification...*\n\nSending verification email to your current address.",
        parse_mode="Markdown"
    )
    
    # Simulate email sending delay
    import asyncio
    await asyncio.sleep(2)
    
    verify_email_text = f"""
✅ *Verification Email Sent*

A verification email has been sent to your current email address.

*Verification Details:*
• Sent to: {user.first_name.lower()}@example.com
• Subject: Verify Your Email - MyPoolr
• Reference: VERIFY-{user.id}-2024
• Expires: In 24 hours

*Email Contains:*
• Verification link (click to confirm)
• Your account information
• Security tips
• Contact information

*Why Verify?*
• Confirms email is working
• Ensures you receive notifications
• Required for security features
• Validates account recovery access

*Next Steps:*
1. Check your email inbox
2. Click the verification link
3. Return here for confirmation
4. Email status will update automatically

*Didn't Receive It?*
• Check spam/junk folder
• Wait up to 10 minutes
• Ensure email address is correct

Your email verification helps keep your account secure!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔄 Resend Verification", "resend_email_verification", emoji="🔄"),
        button_manager.create_button("📧 Change Email", "update_email_address", emoji="📧")
    ])
    grid.add_row([
        button_manager.create_button("✅ Check Status", "check_verification_status", emoji="✅"),
        button_manager.create_button("💬 Need Help?", "email_verification_help", emoji="💬")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "update_email_address", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=verify_email_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_update_email_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle updating email address."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    email_update_text = f"""
📧 *Update Email Address*

Update your email address for important notifications and receipts.

*Current Email:* {user.first_name.lower()}@example.com
*Status:* Verified ✅

*Why Update Your Email?*
• Receive billing notifications
• Get security alerts
• Download receipts and reports
• Account recovery access

*What You'll Receive:*
• Billing confirmations
• Payment receipts
• Security notifications
• Feature updates
• Support communications

*How to Update:*
1. Send your new email address as a message
2. We'll send a verification link
3. Click the link to confirm
4. Email updated instantly

*Security Note:*
We'll send a confirmation to both your old and new email addresses for security.

Ready to update your email address?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📝 Send New Email", "prompt_new_email", emoji="📝"),
        button_manager.create_button("✅ Verify Current", "verify_current_email", emoji="✅")
    ])
    grid.add_row([
        button_manager.create_button("📧 Email Settings", "email_preferences", emoji="📧"),
        button_manager.create_button("🔒 Security Settings", "settings_security", emoji="🔒")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "billing_history", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=email_update_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_email_cancellation_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle emailing cancellation receipt."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    user = update.effective_user
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📧 *Sending Receipt...*\n\nPreparing your cancellation receipt.",
        parse_mode="Markdown"
    )
    
    # Simulate email sending delay
    import asyncio
    await asyncio.sleep(2)
    
    receipt_text = f"""
✅ *Receipt Sent*

Your cancellation receipt has been sent to your email.

*Receipt Details:*
• Sent to: {user.first_name.lower()}@example.com
• Reference: CANCEL-{user.id}-2024
• Date: Today's date
• Status: Confirmed

*Receipt Includes:*
• Cancellation confirmation
• Final billing details
• Data retention policy
• Reactivation instructions

*Didn't receive it?*
• Check your spam folder
• Verify email address in settings
• Contact support for resend

*Important:*
Keep this receipt for your records. It contains important information about your account status and data retention.

Need anything else?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("📧 Update Email", "update_email_address", emoji="📧"),
        button_manager.create_button("🔄 Resend Receipt", "resend_cancellation_receipt", emoji="🔄")
    ])
    grid.add_row([
        button_manager.create_button("💬 Contact Support", "billing_support", emoji="💬"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=receipt_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_process_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle processing subscription cancellation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "⏳ *Processing Cancellation...*\n\nPlease wait while we process your request.",
        parse_mode="Markdown"
    )
    
    # Simulate processing delay
    import asyncio
    await asyncio.sleep(3)
    
    cancellation_text = """
✅ *Subscription Cancelled*

Your subscription has been successfully cancelled.

*Cancellation Details:*
• Effective Date: March 15, 2024
• Remaining Access: 12 days
• Refund: Not applicable (end of billing period)
• Data Retention: 90 days

*What happens next:*
• Continue using premium features until March 15
• Automatic downgrade to Starter tier
• Groups limited to 1 group, 10 members
• Data export available until June 15

*We're sorry to see you go!*
If you change your mind, you can reactivate anytime before March 15 with no penalties.

*Feedback (Optional):*
Help us improve by sharing why you cancelled.

Thank you for using MyPoolr!
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🔄 Reactivate", "reactivate_subscription", emoji="🔄"),
        button_manager.create_button("📊 Export Data", "export_data", emoji="📊")
    ])
    grid.add_row([
        button_manager.create_button("💬 Share Feedback", "cancellation_feedback", emoji="💬"),
        button_manager.create_button("📧 Email Receipt", "email_cancellation_receipt", emoji="📧")
    ])
    grid.add_row([
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=cancellation_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_disable_auto_renewal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle disabling auto-renewal."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    
    renewal_text = """
🔄 *Auto-Renewal Settings*

*Current Status:* Auto-renewal ENABLED

*What is auto-renewal?*
Your subscription automatically renews each month so you don't lose access to premium features.

*If you disable auto-renewal:*
• Your subscription will end on March 15, 2024
• You'll receive reminders before expiration
• You can manually renew anytime
• No automatic charges

*Benefits of keeping auto-renewal:*
• Never lose access to your groups
• Uninterrupted service
• No manual renewal needed
• Same pricing guaranteed

*Current Subscription:*
• Tier: Advanced ($5/month)
• Next renewal: March 15, 2024
• Payment method: M-Pesa (***1234)

Would you like to disable auto-renewal?
    """.strip()
    
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("❌ Disable Auto-Renewal", "confirm_disable_renewal", emoji="❌"),
        button_manager.create_button("✅ Keep Auto-Renewal", "auto_renewal_settings", emoji="✅")
    ])
    grid.add_row([
        button_manager.create_button("💳 Update Payment Method", "update_payment_method", emoji="💳"),
        button_manager.create_button("📅 Change Billing Date", "change_billing_date", emoji="📅")
    ])
    grid.add_row([
        button_manager.create_button("⬅️ Back", "auto_renewal_settings", emoji="⬅️"),
        button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.callback_query.edit_message_text(
        text=renewal_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


def setup_callback_handlers(application) -> None:
    """Set up callback query handlers."""
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Callback handlers registered")