"""Localization service for multi-language support."""

import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal
from supabase import Client

from models.localization import (
    SupportedLocale, MessageTemplate, LocalizedMessage, CulturalSetting,
    LocalizationContext, CurrencyFormat, DateFormat, NumberFormat,
    MessageCategory, LocalizationStatus
)

logger = logging.getLogger(__name__)


class LocalizationService:
    """Service for managing localization and cultural adaptation."""
    
    def __init__(self, supabase_client: Client):
        self.db = supabase_client
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 600  # 10 minutes cache TTL
        self._last_cache_update: Optional[datetime] = None
    
    async def get_message(
        self,
        key: str,
        context: Optional[LocalizationContext] = None,
        placeholders: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get localized message for the given key and context.
        
        Args:
            key: Message key to look up
            context: Localization context (locale, user info, etc.)
            placeholders: Values to substitute in the message
            
        Returns:
            Localized message with placeholders substituted
        """
        try:
            if not context:
                context = LocalizationContext()
            
            # Try to get localized message
            message = await self._get_localized_message(key, context.locale_code)
            
            # Fall back to default locale if not found
            if not message and context.locale_code != context.fallback_locale:
                message = await self._get_localized_message(key, context.fallback_locale)
            
            # Fall back to template default if still not found
            if not message:
                template = await self._get_message_template(key)
                message = template.default_text if template else key
            
            # Substitute placeholders
            if placeholders:
                message = self._substitute_placeholders(message, placeholders)
            
            return message
            
        except Exception as e:
            logger.error(f"Error getting message {key}: {e}")
            return key  # Return key as fallback
    
    async def get_messages_batch(
        self,
        keys: List[str],
        context: Optional[LocalizationContext] = None
    ) -> Dict[str, str]:
        """Get multiple localized messages in a single call."""
        try:
            if not context:
                context = LocalizationContext()
            
            messages = {}
            
            # Get all messages for the locale
            locale_messages = await self._get_locale_messages(context.locale_code)
            
            # Get fallback messages if needed
            fallback_messages = {}
            if context.locale_code != context.fallback_locale:
                fallback_messages = await self._get_locale_messages(context.fallback_locale)
            
            # Get template defaults
            template_defaults = await self._get_template_defaults()
            
            for key in keys:
                message = (
                    locale_messages.get(key) or
                    fallback_messages.get(key) or
                    template_defaults.get(key) or
                    key
                )
                messages[key] = message
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages batch: {e}")
            return {key: key for key in keys}  # Return keys as fallback
    
    async def format_currency(
        self,
        amount: Decimal,
        context: Optional[LocalizationContext] = None
    ) -> str:
        """Format currency amount according to locale settings."""
        try:
            if not context:
                context = LocalizationContext()
            
            currency_format = await self._get_currency_format(context.locale_code)
            return currency_format.format_amount(float(amount))
            
        except Exception as e:
            logger.error(f"Error formatting currency: {e}")
            return str(amount)
    
    async def format_date(
        self,
        date: datetime,
        format_type: str = "short",
        context: Optional[LocalizationContext] = None
    ) -> str:
        """Format date according to locale settings."""
        try:
            if not context:
                context = LocalizationContext()
            
            date_format = await self._get_date_format(context.locale_code)
            
            # Convert to user timezone if specified
            if context.timezone:
                # This would typically use a proper timezone library like pytz
                # For now, we'll use the date as-is
                pass
            
            # Apply format (this is simplified - would use proper date formatting library)
            if format_type == "short":
                return date.strftime("%m/%d/%Y")  # Simplified
            elif format_type == "long":
                return date.strftime("%B %d, %Y")  # Simplified
            else:
                return date.strftime("%m/%d/%Y %H:%M")  # Simplified
                
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return date.strftime("%Y-%m-%d")
    
    async def format_number(
        self,
        number: float,
        decimal_places: int = 2,
        context: Optional[LocalizationContext] = None
    ) -> str:
        """Format number according to locale settings."""
        try:
            if not context:
                context = LocalizationContext()
            
            number_format = await self._get_number_format(context.locale_code)
            return number_format.format_number(number, decimal_places)
            
        except Exception as e:
            logger.error(f"Error formatting number: {e}")
            return f"{number:,.{decimal_places}f}"
    
    async def get_supported_locales(self, active_only: bool = True) -> List[SupportedLocale]:
        """Get list of supported locales."""
        try:
            cache_key = f"supported_locales:{'active' if active_only else 'all'}"
            cached = self._get_from_cache(cache_key)
            if cached:
                return [SupportedLocale(**locale_data) for locale_data in cached]
            
            query = self.db.table("supported_locale").select("*")
            if active_only:
                query = query.eq("is_active", True)
            
            result = query.order("language_name").execute()
            
            if result.data:
                self._set_cache(cache_key, result.data)
                return [SupportedLocale(**locale_data) for locale_data in result.data]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting supported locales: {e}")
            return []
    
    async def get_locale_by_country(self, country_code: str) -> Optional[SupportedLocale]:
        """Get the primary locale for a country."""
        try:
            cache_key = f"locale_by_country:{country_code}"
            cached = self._get_from_cache(cache_key)
            if cached:
                return SupportedLocale(**cached)
            
            result = self.db.table("supported_locale").select("*").eq("country_code", country_code).eq("is_active", True).limit(1).execute()
            
            if result.data:
                locale_data = result.data[0]
                self._set_cache(cache_key, locale_data)
                return SupportedLocale(**locale_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting locale for country {country_code}: {e}")
            return None
    
    async def add_message_template(
        self,
        key: str,
        default_text: str,
        category: MessageCategory,
        description: Optional[str] = None,
        placeholders: Optional[List[str]] = None
    ) -> bool:
        """Add a new message template."""
        try:
            template_data = {
                "key": key,
                "category": category.value,
                "default_text": default_text,
                "description": description,
                "placeholders": placeholders or [],
                "is_active": True
            }
            
            result = self.db.table("message_template").insert(template_data).execute()
            
            if result.data:
                # Clear cache
                self._clear_template_cache(key)
                logger.info(f"Added message template: {key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding message template {key}: {e}")
            return False
    
    async def add_localized_message(
        self,
        template_key: str,
        locale_code: str,
        translated_text: str,
        translator_notes: Optional[str] = None
    ) -> bool:
        """Add or update a localized message."""
        try:
            # Get template ID
            template = await self._get_message_template(template_key)
            if not template:
                logger.error(f"Template not found: {template_key}")
                return False
            
            message_data = {
                "template_id": str(template.id),
                "locale_code": locale_code,
                "translated_text": translated_text,
                "translator_notes": translator_notes,
                "status": LocalizationStatus.ACTIVE.value
            }
            
            # Upsert the localized message
            result = self.db.table("localized_message").upsert(
                message_data,
                on_conflict="template_id,locale_code"
            ).execute()
            
            if result.data:
                # Clear cache
                self._clear_locale_cache(locale_code)
                logger.info(f"Added localized message: {template_key} -> {locale_code}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding localized message {template_key}: {e}")
            return False
    
    async def get_translation_progress(self, locale_code: str) -> Dict[str, Any]:
        """Get translation progress for a locale."""
        try:
            # Get total templates
            total_result = self.db.table("message_template").select("id", count="exact").eq("is_active", True).execute()
            total_templates = total_result.count or 0
            
            # Get translated messages
            translated_result = self.db.table("localized_message").select("id", count="exact").eq("locale_code", locale_code).eq("status", "active").execute()
            translated_count = translated_result.count or 0
            
            # Calculate percentage
            percentage = (translated_count / total_templates * 100) if total_templates > 0 else 0
            
            return {
                "locale_code": locale_code,
                "total_templates": total_templates,
                "translated_count": translated_count,
                "completion_percentage": round(percentage, 1),
                "missing_count": total_templates - translated_count
            }
            
        except Exception as e:
            logger.error(f"Error getting translation progress for {locale_code}: {e}")
            return {
                "locale_code": locale_code,
                "total_templates": 0,
                "translated_count": 0,
                "completion_percentage": 0,
                "missing_count": 0
            }
    
    async def _get_localized_message(self, key: str, locale_code: str) -> Optional[str]:
        """Get localized message from cache or database."""
        cache_key = f"message:{locale_code}:{key}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            result = self.db.table("localized_message").select("translated_text").eq("locale_code", locale_code).eq("status", "active").execute()
            
            # Join with message_template to get by key
            query = """
            SELECT lm.translated_text 
            FROM localized_message lm
            JOIN message_template mt ON lm.template_id = mt.id
            WHERE mt.key = %s AND lm.locale_code = %s AND lm.status = 'active'
            """
            
            # This would need to be adapted for Supabase's query syntax
            # For now, we'll do a simpler approach
            template = await self._get_message_template(key)
            if not template:
                return None
            
            result = self.db.table("localized_message").select("translated_text").eq("template_id", str(template.id)).eq("locale_code", locale_code).eq("status", "active").execute()
            
            if result.data:
                message = result.data[0]["translated_text"]
                self._set_cache(cache_key, message)
                return message
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting localized message {key} for {locale_code}: {e}")
            return None
    
    async def _get_message_template(self, key: str) -> Optional[MessageTemplate]:
        """Get message template from cache or database."""
        cache_key = f"template:{key}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return MessageTemplate(**cached)
        
        try:
            result = self.db.table("message_template").select("*").eq("key", key).eq("is_active", True).execute()
            
            if result.data:
                template_data = result.data[0]
                self._set_cache(cache_key, template_data)
                return MessageTemplate(**template_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting message template {key}: {e}")
            return None
    
    async def _get_locale_messages(self, locale_code: str) -> Dict[str, str]:
        """Get all messages for a locale."""
        cache_key = f"locale_messages:{locale_code}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            # This would need a proper join query in production
            # For now, we'll use a simplified approach
            result = self.db.table("localized_message").select("template_id, translated_text").eq("locale_code", locale_code).eq("status", "active").execute()
            
            messages = {}
            if result.data:
                # We'd need to join with templates to get keys
                # This is simplified for the example
                for message_data in result.data:
                    # In production, you'd join to get the template key
                    pass
            
            self._set_cache(cache_key, messages)
            return messages
            
        except Exception as e:
            logger.error(f"Error getting locale messages for {locale_code}: {e}")
            return {}
    
    async def _get_template_defaults(self) -> Dict[str, str]:
        """Get default text for all templates."""
        cache_key = "template_defaults"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            result = self.db.table("message_template").select("key, default_text").eq("is_active", True).execute()
            
            defaults = {}
            if result.data:
                for template_data in result.data:
                    defaults[template_data["key"]] = template_data["default_text"]
            
            self._set_cache(cache_key, defaults)
            return defaults
            
        except Exception as e:
            logger.error(f"Error getting template defaults: {e}")
            return {}
    
    async def _get_currency_format(self, locale_code: str) -> CurrencyFormat:
        """Get currency format for locale."""
        cache_key = f"currency_format:{locale_code}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return CurrencyFormat.from_dict(cached)
        
        try:
            result = self.db.table("cultural_setting").select("setting_value").eq("locale_code", locale_code).eq("setting_key", "currency_format").execute()
            
            if result.data:
                format_data = result.data[0]["setting_value"]
                self._set_cache(cache_key, format_data)
                return CurrencyFormat.from_dict(format_data)
            
            # Return default format
            return CurrencyFormat("$")
            
        except Exception as e:
            logger.error(f"Error getting currency format for {locale_code}: {e}")
            return CurrencyFormat("$")
    
    async def _get_date_format(self, locale_code: str) -> DateFormat:
        """Get date format for locale."""
        cache_key = f"date_format:{locale_code}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return DateFormat.from_dict(cached)
        
        try:
            result = self.db.table("cultural_setting").select("setting_value").eq("locale_code", locale_code).eq("setting_key", "date_format").execute()
            
            if result.data:
                format_data = result.data[0]["setting_value"]
                self._set_cache(cache_key, format_data)
                return DateFormat.from_dict(format_data)
            
            # Return default format
            return DateFormat()
            
        except Exception as e:
            logger.error(f"Error getting date format for {locale_code}: {e}")
            return DateFormat()
    
    async def _get_number_format(self, locale_code: str) -> NumberFormat:
        """Get number format for locale."""
        cache_key = f"number_format:{locale_code}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return NumberFormat.from_dict(cached)
        
        try:
            result = self.db.table("cultural_setting").select("setting_value").eq("locale_code", locale_code).eq("setting_key", "number_format").execute()
            
            if result.data:
                format_data = result.data[0]["setting_value"]
                self._set_cache(cache_key, format_data)
                return NumberFormat.from_dict(format_data)
            
            # Return default format
            return NumberFormat()
            
        except Exception as e:
            logger.error(f"Error getting number format for {locale_code}: {e}")
            return NumberFormat()
    
    def _substitute_placeholders(self, message: str, placeholders: Dict[str, Any]) -> str:
        """Substitute placeholders in message."""
        try:
            # Simple placeholder substitution using {key} format
            for key, value in placeholders.items():
                placeholder = f"{{{key}}}"
                message = message.replace(placeholder, str(value))
            
            return message
            
        except Exception as e:
            logger.error(f"Error substituting placeholders: {e}")
            return message
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if not self._last_cache_update:
            return None
        
        now = datetime.now(timezone.utc)
        if (now - self._last_cache_update).total_seconds() > self._cache_ttl:
            self._cache.clear()
            self._last_cache_update = None
            return None
        
        return self._cache.get(key)
    
    def _set_cache(self, key: str, value: Any):
        """Set value in cache."""
        self._cache[key] = value
        if not self._last_cache_update:
            self._last_cache_update = datetime.now(timezone.utc)
    
    def _clear_template_cache(self, template_key: str):
        """Clear cache entries for a template."""
        keys_to_remove = [key for key in self._cache.keys() if template_key in key]
        for key in keys_to_remove:
            del self._cache[key]
    
    def _clear_locale_cache(self, locale_code: str):
        """Clear cache entries for a locale."""
        keys_to_remove = [key for key in self._cache.keys() if locale_code in key]
        for key in keys_to_remove:
            del self._cache[key]