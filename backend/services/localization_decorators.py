"""Decorators and utilities for localization."""

import functools
import logging
from typing import Callable, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from models.localization import LocalizationContext
from .localization_service import LocalizationService

logger = logging.getLogger(__name__)


def localized_response(
    message_keys: Optional[Dict[str, str]] = None,
    context_extractor: Optional[Callable] = None
):
    """
    Decorator to automatically localize response messages.
    
    Args:
        message_keys: Mapping of response fields to message keys
        context_extractor: Function to extract LocalizationContext from request
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get localization service
            localization_service = kwargs.get('localization_service')
            if not localization_service or not message_keys:
                return await func(*args, **kwargs)
            
            # Extract context
            context = None
            if context_extractor:
                try:
                    context = context_extractor(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error extracting localization context: {e}")
                    context = LocalizationContext()
            else:
                context = LocalizationContext()
            
            # Execute original function
            result = await func(*args, **kwargs)
            
            # Localize response if it's a dictionary
            if isinstance(result, dict):
                localized_result = result.copy()
                
                for field, message_key in message_keys.items():
                    if field in result:
                        # Get localized message
                        localized_message = await localization_service.get_message(
                            message_key, 
                            context,
                            placeholders=result.get(f"{field}_placeholders")
                        )
                        localized_result[field] = localized_message
                
                return localized_result
            
            return result
        
        return wrapper
    return decorator


class LocalizationHelper:
    """Helper class for common localization operations."""
    
    def __init__(self, localization_service: LocalizationService):
        self.service = localization_service
    
    async def localize_error_response(
        self,
        error_key: str,
        context: Optional[LocalizationContext] = None,
        placeholders: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ) -> Dict[str, Any]:
        """Create a localized error response."""
        message = await self.service.get_message(error_key, context, placeholders)
        
        return {
            "error": True,
            "message": message,
            "status_code": status_code,
            "error_key": error_key
        }
    
    async def localize_success_response(
        self,
        success_key: str,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[LocalizationContext] = None,
        placeholders: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a localized success response."""
        message = await self.service.get_message(success_key, context, placeholders)
        
        response = {
            "success": True,
            "message": message,
            "message_key": success_key
        }
        
        if data:
            response["data"] = data
        
        return response
    
    async def localize_notification(
        self,
        notification_key: str,
        context: Optional[LocalizationContext] = None,
        placeholders: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a localized notification."""
        message = await self.service.get_message(notification_key, context, placeholders)
        
        return {
            "message": message,
            "message_key": notification_key,
            "locale": context.locale_code if context else "en_US"
        }
    
    async def format_monetary_amount(
        self,
        amount: Decimal,
        context: Optional[LocalizationContext] = None
    ) -> str:
        """Format monetary amount with proper currency and locale."""
        return await self.service.format_currency(amount, context)
    
    async def format_datetime(
        self,
        dt: datetime,
        format_type: str = "short",
        context: Optional[LocalizationContext] = None
    ) -> str:
        """Format datetime according to locale."""
        return await self.service.format_date(dt, format_type, context)
    
    async def get_ui_messages(
        self,
        keys: List[str],
        context: Optional[LocalizationContext] = None
    ) -> Dict[str, str]:
        """Get multiple UI messages for frontend."""
        return await self.service.get_messages_batch(keys, context)


# Common context extractors
def extract_locale_from_request(request, **kwargs) -> LocalizationContext:
    """Extract localization context from FastAPI request."""
    # Extract from headers
    accept_language = getattr(request.headers, 'accept-language', 'en-US')
    user_agent = getattr(request.headers, 'user-agent', '')
    
    # Extract from user state (if available)
    user_id = getattr(request.state, 'user_id', None)
    country_code = getattr(request.state, 'country_code', None)
    timezone = getattr(request.state, 'timezone', None)
    
    # Parse locale from Accept-Language header (simplified)
    locale_code = "en_US"
    if accept_language:
        # Simple parsing - in production you'd use a proper parser
        lang_parts = accept_language.split(',')[0].strip().split('-')
        if len(lang_parts) >= 2:
            locale_code = f"{lang_parts[0]}_{lang_parts[1].upper()}"
        elif len(lang_parts) == 1:
            locale_code = f"{lang_parts[0]}_US"  # Default country
    
    return LocalizationContext(
        locale_code=locale_code,
        user_id=user_id,
        country_code=country_code,
        timezone=timezone
    )


def extract_locale_from_country(country_code: str, **kwargs) -> LocalizationContext:
    """Extract localization context from country code."""
    # Map country codes to common locales
    country_locale_map = {
        "US": "en_US",
        "KE": "en_KE",
        "TZ": "sw_TZ",
        "UG": "en_UG",
        "NG": "en_NG",
        "FR": "fr_FR",
        "SA": "ar_SA"
    }
    
    locale_code = country_locale_map.get(country_code.upper(), "en_US")
    
    return LocalizationContext(
        locale_code=locale_code,
        country_code=country_code.upper()
    )


# Utility functions
def get_user_locale(user_preferences: Dict[str, Any], country_code: Optional[str] = None) -> str:
    """Determine user locale from preferences and country."""
    # Check user explicit preference
    if "locale" in user_preferences:
        return user_preferences["locale"]
    
    # Check user language preference
    if "language" in user_preferences and country_code:
        return f"{user_preferences['language']}_{country_code.upper()}"
    
    # Fall back to country default
    if country_code:
        context = extract_locale_from_country(country_code)
        return context.locale_code
    
    return "en_US"


def detect_rtl_locale(locale_code: str) -> bool:
    """Detect if locale uses right-to-left text direction."""
    rtl_languages = ["ar", "he", "fa", "ur"]
    language_code = locale_code.split("_")[0].lower()
    return language_code in rtl_languages


def get_currency_for_country(country_code: str) -> str:
    """Get currency code for country."""
    currency_map = {
        "US": "USD",
        "KE": "KES",
        "TZ": "TZS",
        "UG": "UGX",
        "NG": "NGN",
        "FR": "EUR",
        "SA": "SAR"
    }
    
    return currency_map.get(country_code.upper(), "USD")


def get_timezone_for_country(country_code: str) -> str:
    """Get primary timezone for country."""
    timezone_map = {
        "US": "America/New_York",
        "KE": "Africa/Nairobi",
        "TZ": "Africa/Dar_es_Salaam",
        "UG": "Africa/Kampala",
        "NG": "Africa/Lagos",
        "FR": "Europe/Paris",
        "SA": "Asia/Riyadh"
    }
    
    return timezone_map.get(country_code.upper(), "UTC")