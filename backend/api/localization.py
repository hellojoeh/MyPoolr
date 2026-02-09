"""API endpoints for localization management."""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, Field

from models.localization import (
    SupportedLocale, MessageTemplate, LocalizedMessage,
    LocalizationContext, MessageCategory
)
from services.localization_service import LocalizationService
from services.localization_decorators import (
    LocalizationHelper, extract_locale_from_request
)
from database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/localization", tags=["localization"])


# Request/Response models
class MessageRequest(BaseModel):
    """Request to get a localized message."""
    key: str
    locale_code: Optional[str] = None
    placeholders: Optional[Dict[str, Any]] = None


class MessagesRequest(BaseModel):
    """Request to get multiple localized messages."""
    keys: List[str]
    locale_code: Optional[str] = None


class MessageResponse(BaseModel):
    """Response with localized message."""
    key: str
    message: str
    locale_code: str


class MessagesResponse(BaseModel):
    """Response with multiple localized messages."""
    messages: Dict[str, str]
    locale_code: str


class FormatCurrencyRequest(BaseModel):
    """Request to format currency."""
    amount: Decimal
    locale_code: Optional[str] = None


class FormatDateRequest(BaseModel):
    """Request to format date."""
    date: datetime
    format_type: str = Field(default="short", regex="^(short|long|time)$")
    locale_code: Optional[str] = None


class AddTemplateRequest(BaseModel):
    """Request to add message template."""
    key: str
    default_text: str
    category: MessageCategory
    description: Optional[str] = None
    placeholders: Optional[List[str]] = None


class AddTranslationRequest(BaseModel):
    """Request to add translation."""
    template_key: str
    locale_code: str
    translated_text: str
    translator_notes: Optional[str] = None


class TranslationProgressResponse(BaseModel):
    """Response with translation progress."""
    locale_code: str
    total_templates: int
    translated_count: int
    completion_percentage: float
    missing_count: int


# Dependency to get localization service
async def get_localization_service() -> LocalizationService:
    """Get localization service instance."""
    return LocalizationService(db_manager.service_client)


# Dependency to get localization helper
async def get_localization_helper(
    service: LocalizationService = Depends(get_localization_service)
) -> LocalizationHelper:
    """Get localization helper instance."""
    return LocalizationHelper(service)


# Dependency to extract locale context
async def get_locale_context(
    accept_language: Optional[str] = Header(None),
    x_country_code: Optional[str] = Header(None),
    x_user_timezone: Optional[str] = Header(None)
) -> LocalizationContext:
    """Extract localization context from headers."""
    # Parse locale from Accept-Language header
    locale_code = "en_US"
    if accept_language:
        lang_parts = accept_language.split(',')[0].strip().split('-')
        if len(lang_parts) >= 2:
            locale_code = f"{lang_parts[0]}_{lang_parts[1].upper()}"
        elif len(lang_parts) == 1 and x_country_code:
            locale_code = f"{lang_parts[0]}_{x_country_code.upper()}"
    
    return LocalizationContext(
        locale_code=locale_code,
        country_code=x_country_code,
        timezone=x_user_timezone
    )


@router.post("/message", response_model=MessageResponse)
async def get_message(
    request: MessageRequest,
    context: LocalizationContext = Depends(get_locale_context),
    service: LocalizationService = Depends(get_localization_service)
):
    """Get a localized message."""
    try:
        # Use request locale if provided, otherwise use context
        if request.locale_code:
            context.locale_code = request.locale_code
        
        message = await service.get_message(
            request.key,
            context,
            request.placeholders
        )
        
        return MessageResponse(
            key=request.key,
            message=message,
            locale_code=context.locale_code
        )
        
    except Exception as e:
        logger.error(f"Error getting message {request.key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get localized message"
        )


@router.post("/messages", response_model=MessagesResponse)
async def get_messages(
    request: MessagesRequest,
    context: LocalizationContext = Depends(get_locale_context),
    service: LocalizationService = Depends(get_localization_service)
):
    """Get multiple localized messages."""
    try:
        # Use request locale if provided, otherwise use context
        if request.locale_code:
            context.locale_code = request.locale_code
        
        messages = await service.get_messages_batch(request.keys, context)
        
        return MessagesResponse(
            messages=messages,
            locale_code=context.locale_code
        )
        
    except Exception as e:
        logger.error(f"Error getting messages batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get localized messages"
        )


@router.post("/format/currency")
async def format_currency(
    request: FormatCurrencyRequest,
    context: LocalizationContext = Depends(get_locale_context),
    service: LocalizationService = Depends(get_localization_service)
):
    """Format currency amount according to locale."""
    try:
        # Use request locale if provided, otherwise use context
        if request.locale_code:
            context.locale_code = request.locale_code
        
        formatted = await service.format_currency(request.amount, context)
        
        return {
            "amount": request.amount,
            "formatted": formatted,
            "locale_code": context.locale_code
        }
        
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to format currency"
        )


@router.post("/format/date")
async def format_date(
    request: FormatDateRequest,
    context: LocalizationContext = Depends(get_locale_context),
    service: LocalizationService = Depends(get_localization_service)
):
    """Format date according to locale."""
    try:
        # Use request locale if provided, otherwise use context
        if request.locale_code:
            context.locale_code = request.locale_code
        
        formatted = await service.format_date(
            request.date,
            request.format_type,
            context
        )
        
        return {
            "date": request.date,
            "formatted": formatted,
            "format_type": request.format_type,
            "locale_code": context.locale_code
        }
        
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to format date"
        )


@router.get("/locales", response_model=List[SupportedLocale])
async def get_supported_locales(
    active_only: bool = True,
    service: LocalizationService = Depends(get_localization_service)
):
    """Get list of supported locales."""
    try:
        locales = await service.get_supported_locales(active_only)
        return locales
        
    except Exception as e:
        logger.error(f"Error getting supported locales: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get supported locales"
        )


@router.get("/locale/country/{country_code}", response_model=SupportedLocale)
async def get_locale_by_country(
    country_code: str,
    service: LocalizationService = Depends(get_localization_service)
):
    """Get primary locale for a country."""
    try:
        locale = await service.get_locale_by_country(country_code.upper())
        
        if not locale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No locale found for country {country_code}"
            )
        
        return locale
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting locale for country {country_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get locale for country"
        )


@router.post("/template")
async def add_message_template(
    request: AddTemplateRequest,
    service: LocalizationService = Depends(get_localization_service)
):
    """Add a new message template."""
    try:
        success = await service.add_message_template(
            key=request.key,
            default_text=request.default_text,
            category=request.category,
            description=request.description,
            placeholders=request.placeholders
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add message template"
            )
        
        return {"message": "Message template added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add message template"
        )


@router.post("/translation")
async def add_translation(
    request: AddTranslationRequest,
    service: LocalizationService = Depends(get_localization_service)
):
    """Add or update a translation."""
    try:
        success = await service.add_localized_message(
            template_key=request.template_key,
            locale_code=request.locale_code,
            translated_text=request.translated_text,
            translator_notes=request.translator_notes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add translation"
            )
        
        return {"message": "Translation added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding translation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add translation"
        )


@router.get("/progress/{locale_code}", response_model=TranslationProgressResponse)
async def get_translation_progress(
    locale_code: str,
    service: LocalizationService = Depends(get_localization_service)
):
    """Get translation progress for a locale."""
    try:
        progress = await service.get_translation_progress(locale_code)
        return TranslationProgressResponse(**progress)
        
    except Exception as e:
        logger.error(f"Error getting translation progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get translation progress"
        )


@router.get("/templates", response_model=List[MessageTemplate])
async def get_message_templates(
    category: Optional[MessageCategory] = None,
    service: LocalizationService = Depends(get_localization_service)
):
    """Get message templates."""
    try:
        query = db_manager.service_client.table("message_template").select("*").eq("is_active", True)
        
        if category:
            query = query.eq("category", category.value)
        
        result = query.order("key").execute()
        
        if not result.data:
            return []
        
        return [MessageTemplate(**template_data) for template_data in result.data]
        
    except Exception as e:
        logger.error(f"Error getting message templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get message templates"
        )