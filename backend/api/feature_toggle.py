"""API endpoints for feature toggle management."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from models.feature_toggle import (
    FeatureDefinition, CountryConfig, FeatureToggle, FeatureUsage,
    FeatureScope, ToggleStatus, FeatureContext
)
from services.feature_toggle_service import FeatureToggleService
from database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-toggles", tags=["feature-toggles"])


# Request/Response models
class FeatureCheckRequest(BaseModel):
    """Request to check if a feature is enabled."""
    feature_name: str
    user_id: Optional[int] = None
    mypoolr_id: Optional[UUID] = None
    country_code: Optional[str] = None
    tier: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FeatureCheckResponse(BaseModel):
    """Response for feature check."""
    feature_name: str
    enabled: bool
    context: Dict[str, Any]


class UpdateToggleRequest(BaseModel):
    """Request to update a feature toggle."""
    feature_name: str
    scope: FeatureScope
    scope_value: Optional[str] = None
    status: ToggleStatus
    conditions: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class FeatureListResponse(BaseModel):
    """Response with list of enabled features."""
    enabled_features: Set[str]
    context: Dict[str, Any]


class UsageStatsResponse(BaseModel):
    """Response with feature usage statistics."""
    feature_name: Optional[str]
    country_code: Optional[str]
    stats: List[Dict[str, Any]]


# Dependency to get feature toggle service
async def get_feature_service() -> FeatureToggleService:
    """Get feature toggle service instance."""
    return FeatureToggleService(db_manager.service_client)


@router.post("/check", response_model=FeatureCheckResponse)
async def check_feature(
    request: FeatureCheckRequest,
    feature_service: FeatureToggleService = Depends(get_feature_service)
):
    """Check if a specific feature is enabled for the given context."""
    try:
        context = FeatureContext(
            user_id=request.user_id,
            mypoolr_id=request.mypoolr_id,
            country_code=request.country_code,
            tier=request.tier,
            metadata=request.metadata
        )
        
        is_enabled = await feature_service.is_feature_enabled(request.feature_name, context)
        
        return FeatureCheckResponse(
            feature_name=request.feature_name,
            enabled=is_enabled,
            context=context.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error checking feature {request.feature_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check feature status"
        )


@router.post("/list", response_model=FeatureListResponse)
async def list_enabled_features(
    request: FeatureCheckRequest,
    feature_service: FeatureToggleService = Depends(get_feature_service)
):
    """Get all enabled features for the given context."""
    try:
        context = FeatureContext(
            user_id=request.user_id,
            mypoolr_id=request.mypoolr_id,
            country_code=request.country_code,
            tier=request.tier,
            metadata=request.metadata
        )
        
        enabled_features = await feature_service.get_enabled_features(context)
        
        return FeatureListResponse(
            enabled_features=enabled_features,
            context=context.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error listing enabled features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list enabled features"
        )


@router.put("/toggle")
async def update_feature_toggle(
    request: UpdateToggleRequest,
    feature_service: FeatureToggleService = Depends(get_feature_service)
):
    """Update or create a feature toggle."""
    try:
        success = await feature_service.update_feature_toggle(
            feature_name=request.feature_name,
            scope=request.scope,
            scope_value=request.scope_value,
            status=request.status,
            conditions=request.conditions,
            expires_at=request.expires_at
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update feature toggle"
            )
        
        return {"message": "Feature toggle updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feature toggle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feature toggle"
        )


@router.get("/country/{country_code}", response_model=CountryConfig)
async def get_country_config(
    country_code: str,
    feature_service: FeatureToggleService = Depends(get_feature_service)
):
    """Get configuration for a specific country."""
    try:
        config = await feature_service.get_country_config(country_code.upper())
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Country configuration not found for {country_code}"
            )
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting country config for {country_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get country configuration"
        )


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    feature_name: Optional[str] = None,
    country_code: Optional[str] = None,
    days: int = Field(default=30, ge=1, le=365),
    feature_service: FeatureToggleService = Depends(get_feature_service)
):
    """Get feature usage statistics."""
    try:
        stats = await feature_service.get_feature_usage_stats(
            feature_name=feature_name,
            country_code=country_code,
            days=days
        )
        
        return UsageStatsResponse(
            feature_name=feature_name,
            country_code=country_code,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage statistics"
        )


@router.get("/definitions", response_model=List[FeatureDefinition])
async def get_feature_definitions(
    feature_service: FeatureToggleService = Depends(get_feature_service)
):
    """Get all feature definitions."""
    try:
        result = db_manager.service_client.table("feature_definition").select("*").execute()
        
        if not result.data:
            return []
        
        return [FeatureDefinition(**feature_data) for feature_data in result.data]
        
    except Exception as e:
        logger.error(f"Error getting feature definitions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feature definitions"
        )


@router.get("/toggles", response_model=List[FeatureToggle])
async def get_feature_toggles(
    feature_name: Optional[str] = None,
    scope: Optional[FeatureScope] = None,
    scope_value: Optional[str] = None,
    feature_service: FeatureToggleService = Depends(get_feature_service)
):
    """Get feature toggles with optional filtering."""
    try:
        query = db_manager.service_client.table("feature_toggle").select("*")
        
        if feature_name:
            query = query.eq("feature_name", feature_name)
        
        if scope:
            query = query.eq("scope", scope.value)
        
        if scope_value:
            query = query.eq("scope_value", scope_value)
        
        result = query.execute()
        
        if not result.data:
            return []
        
        return [FeatureToggle(**toggle_data) for toggle_data in result.data]
        
    except Exception as e:
        logger.error(f"Error getting feature toggles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feature toggles"
        )