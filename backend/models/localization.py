"""Localization models for multi-language support."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID

from .base import BaseModel


class MessageCategory(str, Enum):
    """Categories for message templates."""
    UI = "ui"
    NOTIFICATION = "notification"
    ERROR = "error"
    VALIDATION = "validation"
    HELP = "help"


class LocalizationStatus(str, Enum):
    """Status of localized messages."""
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class SupportedLocale(BaseModel):
    """Supported locale configuration."""
    
    id: UUID
    locale_code: str
    language_code: str
    country_code: Optional[str] = None
    language_name: str
    native_name: str
    rtl: bool = False
    is_active: bool = True
    completion_percentage: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class MessageTemplate(BaseModel):
    """Template for messages that can be localized."""
    
    id: UUID
    key: str
    category: MessageCategory
    default_text: str
    description: Optional[str] = None
    placeholders: List[str] = []
    context_info: Dict[str, Any] = {}
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


class LocalizedMessage(BaseModel):
    """Localized version of a message template."""
    
    id: UUID
    template_id: UUID
    locale_code: str
    translated_text: str
    status: LocalizationStatus = LocalizationStatus.ACTIVE
    translator_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class CulturalSetting(BaseModel):
    """Cultural settings for different locales."""
    
    id: UUID
    locale_code: str
    setting_key: str
    setting_value: Dict[str, Any]
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class LocalizationContext:
    """Context for localization operations."""
    
    def __init__(
        self,
        locale_code: str = "en_US",
        user_id: Optional[int] = None,
        country_code: Optional[str] = None,
        timezone: Optional[str] = None,
        fallback_locale: str = "en_US"
    ):
        self.locale_code = locale_code
        self.user_id = user_id
        self.country_code = country_code
        self.timezone = timezone
        self.fallback_locale = fallback_locale
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "locale_code": self.locale_code,
            "user_id": self.user_id,
            "country_code": self.country_code,
            "timezone": self.timezone,
            "fallback_locale": self.fallback_locale
        }


class CurrencyFormat:
    """Currency formatting configuration."""
    
    def __init__(
        self,
        symbol: str,
        position: str = "before",  # "before" or "after"
        decimal_places: int = 2,
        thousands_separator: str = ",",
        decimal_separator: str = "."
    ):
        self.symbol = symbol
        self.position = position
        self.decimal_places = decimal_places
        self.thousands_separator = thousands_separator
        self.decimal_separator = decimal_separator
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurrencyFormat":
        """Create CurrencyFormat from dictionary."""
        return cls(
            symbol=data.get("symbol", "$"),
            position=data.get("position", "before"),
            decimal_places=data.get("decimal_places", 2),
            thousands_separator=data.get("thousands_separator", ","),
            decimal_separator=data.get("decimal_separator", ".")
        )
    
    def format_amount(self, amount: float) -> str:
        """Format amount according to currency settings."""
        # Format number with separators
        formatted_number = f"{amount:,.{self.decimal_places}f}"
        
        # Replace separators if different from default
        if self.thousands_separator != ",":
            formatted_number = formatted_number.replace(",", "TEMP")
            formatted_number = formatted_number.replace(".", self.decimal_separator)
            formatted_number = formatted_number.replace("TEMP", self.thousands_separator)
        elif self.decimal_separator != ".":
            formatted_number = formatted_number.replace(".", self.decimal_separator)
        
        # Add currency symbol
        if self.position == "before":
            return f"{self.symbol}{formatted_number}"
        else:
            return f"{formatted_number} {self.symbol}"


class DateFormat:
    """Date formatting configuration."""
    
    def __init__(
        self,
        short: str = "MM/dd/yyyy",
        long: str = "MMMM d, yyyy",
        time: str = "h:mm a"
    ):
        self.short = short
        self.long = long
        self.time = time
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DateFormat":
        """Create DateFormat from dictionary."""
        return cls(
            short=data.get("short", "MM/dd/yyyy"),
            long=data.get("long", "MMMM d, yyyy"),
            time=data.get("time", "h:mm a")
        )


class NumberFormat:
    """Number formatting configuration."""
    
    def __init__(
        self,
        thousands_separator: str = ",",
        decimal_separator: str = ".",
        grouping: List[int] = None
    ):
        self.thousands_separator = thousands_separator
        self.decimal_separator = decimal_separator
        self.grouping = grouping or [3]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NumberFormat":
        """Create NumberFormat from dictionary."""
        return cls(
            thousands_separator=data.get("thousands_separator", ","),
            decimal_separator=data.get("decimal_separator", "."),
            grouping=data.get("grouping", [3])
        )
    
    def format_number(self, number: float, decimal_places: int = 2) -> str:
        """Format number according to locale settings."""
        formatted = f"{number:,.{decimal_places}f}"
        
        # Replace separators if different from default
        if self.thousands_separator != ",":
            formatted = formatted.replace(",", "TEMP")
            formatted = formatted.replace(".", self.decimal_separator)
            formatted = formatted.replace("TEMP", self.thousands_separator)
        elif self.decimal_separator != ".":
            formatted = formatted.replace(".", self.decimal_separator)
        
        return formatted