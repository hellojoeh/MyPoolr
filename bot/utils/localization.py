"""Localization utilities for Telegram bot."""

import logging
import aiohttp
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class BotLocalizationService:
    """Localization service for Telegram bot."""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_message(
        self,
        key: str,
        locale_code: Optional[str] = None,
        placeholders: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> str:
        """Get localized message from backend."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Prepare request data
            request_data = {
                "key": key,
                "placeholders": placeholders or {}
            }
            
            if locale_code:
                request_data["locale_code"] = locale_code
            
            # Prepare headers
            headers = {}
            if locale_code:
                headers["Accept-Language"] = locale_code.replace("_", "-")
            
            # Make request to backend
            async with self.session.post(
                f"{self.backend_url}/localization/message",
                json=request_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["message"]
                else:
                    logger.error(f"Failed to get message {key}: {response.status}")
                    return key  # Return key as fallback
        
        except Exception as e:
            logger.error(f"Error getting localized message {key}: {e}")
            return key  # Return key as fallback
    
    async def get_messages_batch(
        self,
        keys: List[str],
        locale_code: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, str]:
        """Get multiple localized messages."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Prepare request data
            request_data = {"keys": keys}
            if locale_code:
                request_data["locale_code"] = locale_code
            
            # Prepare headers
            headers = {}
            if locale_code:
                headers["Accept-Language"] = locale_code.replace("_", "-")
            
            # Make request to backend
            async with self.session.post(
                f"{self.backend_url}/localization/messages",
                json=request_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["messages"]
                else:
                    logger.error(f"Failed to get messages batch: {response.status}")
                    return {key: key for key in keys}  # Return keys as fallback
        
        except Exception as e:
            logger.error(f"Error getting messages batch: {e}")
            return {key: key for key in keys}  # Return keys as fallback
    
    async def format_currency(
        self,
        amount: Decimal,
        locale_code: Optional[str] = None
    ) -> str:
        """Format currency amount."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Prepare request data
            request_data = {"amount": str(amount)}
            if locale_code:
                request_data["locale_code"] = locale_code
            
            # Prepare headers
            headers = {}
            if locale_code:
                headers["Accept-Language"] = locale_code.replace("_", "-")
            
            # Make request to backend
            async with self.session.post(
                f"{self.backend_url}/localization/format/currency",
                json=request_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["formatted"]
                else:
                    logger.error(f"Failed to format currency: {response.status}")
                    return str(amount)  # Return raw amount as fallback
        
        except Exception as e:
            logger.error(f"Error formatting currency: {e}")
            return str(amount)  # Return raw amount as fallback
    
    async def get_user_locale(self, user_id: int, country_code: Optional[str] = None) -> str:
        """Get user's preferred locale."""
        try:
            # Check cache first
            cache_key = f"user_locale:{user_id}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            # In a real implementation, you'd get this from user preferences
            # For now, we'll use country-based detection
            if country_code:
                locale_code = self._get_locale_for_country(country_code)
            else:
                locale_code = "en_US"  # Default
            
            # Cache the result
            self._cache[cache_key] = locale_code
            return locale_code
        
        except Exception as e:
            logger.error(f"Error getting user locale: {e}")
            return "en_US"  # Default fallback
    
    def _get_locale_for_country(self, country_code: str) -> str:
        """Map country code to locale."""
        country_locale_map = {
            "US": "en_US",
            "KE": "en_KE",
            "TZ": "sw_TZ",
            "UG": "en_UG",
            "NG": "en_NG",
            "FR": "fr_FR",
            "SA": "ar_SA"
        }
        
        return country_locale_map.get(country_code.upper(), "en_US")


class LocalizedBot:
    """Mixin class for adding localization to bot handlers."""
    
    def __init__(self, localization_service: BotLocalizationService):
        self.localization = localization_service
    
    async def get_localized_text(
        self,
        key: str,
        user_id: int,
        placeholders: Optional[Dict[str, Any]] = None,
        country_code: Optional[str] = None
    ) -> str:
        """Get localized text for user."""
        locale_code = await self.localization.get_user_locale(user_id, country_code)
        return await self.localization.get_message(key, locale_code, placeholders, user_id)
    
    async def get_localized_texts(
        self,
        keys: List[str],
        user_id: int,
        country_code: Optional[str] = None
    ) -> Dict[str, str]:
        """Get multiple localized texts for user."""
        locale_code = await self.localization.get_user_locale(user_id, country_code)
        return await self.localization.get_messages_batch(keys, locale_code, user_id)
    
    async def format_amount(
        self,
        amount: Decimal,
        user_id: int,
        country_code: Optional[str] = None
    ) -> str:
        """Format currency amount for user."""
        locale_code = await self.localization.get_user_locale(user_id, country_code)
        return await self.localization.format_currency(amount, locale_code)


# Common message keys for bot
class MessageKeys:
    """Common message keys used in the bot."""
    
    # Welcome and menu
    WELCOME_TITLE = "welcome.title"
    WELCOME_SUBTITLE = "welcome.subtitle"
    MENU_CREATE_GROUP = "menu.create_group"
    MENU_JOIN_GROUP = "menu.join_group"
    MENU_MY_GROUPS = "menu.my_groups"
    MENU_SETTINGS = "menu.settings"
    MENU_HELP = "menu.help"
    
    # Group creation
    CREATE_GROUP_NAME = "create.group_name"
    CREATE_CONTRIBUTION_AMOUNT = "create.contribution_amount"
    CREATE_ROTATION_FREQUENCY = "create.rotation_frequency"
    CREATE_MEMBER_LIMIT = "create.member_limit"
    CREATE_SUCCESS = "create.success"
    
    # Member management
    MEMBER_INVITE_LINK = "member.invite_link"
    MEMBER_JOIN_SUCCESS = "member.join_success"
    MEMBER_SECURITY_DEPOSIT = "member.security_deposit"
    MEMBER_ROTATION_POSITION = "member.rotation_position"
    
    # Contributions
    CONTRIBUTION_REQUEST = "contribution.request"
    CONTRIBUTION_AMOUNT_DUE = "contribution.amount_due"
    CONTRIBUTION_CONFIRM_SENT = "contribution.confirm_sent"
    CONTRIBUTION_CONFIRM_RECEIVED = "contribution.confirm_received"
    CONTRIBUTION_COMPLETED = "contribution.completed"
    
    # Notifications
    NOTIFICATION_ROTATION_START = "notification.rotation_start"
    NOTIFICATION_CONTRIBUTION_REMINDER = "notification.contribution_reminder"
    NOTIFICATION_PAYMENT_RECEIVED = "notification.payment_received"
    NOTIFICATION_DEFAULT_WARNING = "notification.default_warning"
    
    # Errors
    ERROR_INVALID_AMOUNT = "error.invalid_amount"
    ERROR_GROUP_FULL = "error.group_full"
    ERROR_INSUFFICIENT_TIER = "error.insufficient_tier"
    ERROR_PAYMENT_FAILED = "error.payment_failed"
    ERROR_NETWORK_ERROR = "error.network_error"
    
    # Validation
    VALIDATION_REQUIRED_FIELD = "validation.required_field"
    VALIDATION_MIN_AMOUNT = "validation.min_amount"
    VALIDATION_MAX_MEMBERS = "validation.max_members"
    VALIDATION_INVALID_PHONE = "validation.invalid_phone"
    
    # Help
    HELP_HOW_IT_WORKS = "help.how_it_works"
    HELP_SECURITY_DEPOSIT = "help.security_deposit"
    HELP_ROTATION_SCHEDULE = "help.rotation_schedule"
    HELP_CONTACT_SUPPORT = "help.contact_support"


# Utility functions
def detect_user_country(user_data: Dict[str, Any]) -> Optional[str]:
    """Detect user's country from Telegram user data."""
    # This would typically use user's language code or other indicators
    language_code = user_data.get("language_code", "en")
    
    # Simple mapping based on language code
    language_country_map = {
        "en": "US",  # Default to US for English
        "sw": "KE",  # Swahili -> Kenya
        "fr": "FR",  # French -> France
        "ar": "SA",  # Arabic -> Saudi Arabia
    }
    
    return language_country_map.get(language_code)


def get_rtl_locales() -> List[str]:
    """Get list of right-to-left locales."""
    return ["ar_SA", "he_IL", "fa_IR", "ur_PK"]


def is_rtl_locale(locale_code: str) -> bool:
    """Check if locale uses right-to-left text direction."""
    return locale_code in get_rtl_locales()


# Example usage in bot handlers
async def example_handler_with_localization(update, context, localization: BotLocalizationService):
    """Example of how to use localization in bot handlers."""
    user_id = update.effective_user.id
    country_code = detect_user_country(update.effective_user.to_dict())
    
    # Get localized welcome message
    welcome_text = await localization.get_message(
        MessageKeys.WELCOME_TITLE,
        locale_code=await localization.get_user_locale(user_id, country_code),
        user_id=user_id
    )
    
    # Format currency amount
    amount = Decimal("1000.50")
    formatted_amount = await localization.format_currency(
        amount,
        locale_code=await localization.get_user_locale(user_id, country_code)
    )
    
    # Send localized message
    await update.message.reply_text(f"{welcome_text}\n\nAmount: {formatted_amount}")