"""Handler modules for MyPoolr Telegram Bot."""

from telegram.ext import Application

from .commands import setup_command_handlers
from .callbacks import setup_callback_handlers
from .conversations import setup_conversation_handlers


def setup_handlers(application: Application) -> None:
    """Set up all bot handlers."""
    setup_command_handlers(application)
    setup_callback_handlers(application)
    setup_conversation_handlers(application)