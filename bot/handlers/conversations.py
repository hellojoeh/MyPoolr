"""Conversation handlers for MyPoolr Telegram Bot."""

from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from loguru import logger

from .mypoolr_creation import (
    start_mypoolr_creation,
    handle_country_selection,
    handle_name_entry,
    handle_amount_entry,
    handle_frequency_selection,
    handle_tier_selection,
    handle_member_limit_entry,
    handle_creation_confirmation,
    cancel_creation,
    SELECTING_COUNTRY,
    ENTERING_NAME,
    ENTERING_AMOUNT,
    SELECTING_FREQUENCY,
    SELECTING_TIER,
    ENTERING_MEMBER_LIMIT,
    CONFIRMING_DETAILS
)


def setup_conversation_handlers(application) -> None:
    """Set up conversation handlers for multi-step workflows."""
    
    # MyPoolr Creation Conversation Handler
    mypoolr_creation_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_mypoolr_creation, pattern="^start_mypoolr_creation$")
        ],
        states={
            SELECTING_COUNTRY: [
                CallbackQueryHandler(handle_country_selection, pattern="^country:"),
                CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
            ],
            ENTERING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_entry),
                CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
            ],
            ENTERING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount_entry),
                CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
            ],
            SELECTING_FREQUENCY: [
                CallbackQueryHandler(handle_frequency_selection, pattern="^frequency:"),
                CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
            ],
            SELECTING_TIER: [
                CallbackQueryHandler(handle_tier_selection, pattern="^tier:"),
                CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
            ],
            ENTERING_MEMBER_LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_member_limit_entry),
                CallbackQueryHandler(handle_member_limit_entry, pattern="^members:"),
                CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
            ],
            CONFIRMING_DETAILS: [
                CallbackQueryHandler(handle_creation_confirmation, pattern="^confirm_create$"),
                CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")
        ],
        name="mypoolr_creation",
        persistent=False  # Disable persistence for now
    )
    
    # Add conversation handler to application
    application.add_handler(mypoolr_creation_handler)
    
    logger.info("Conversation handlers setup complete")