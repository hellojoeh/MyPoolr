"""Tier management API endpoints."""

from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from models.mypoolr import TierLevel
from services.tier_management import (
    TierManagementService, 
    TierUpgradeRequest, 
    TierValidationError,
    TierFeatures,
    TierPricing
)
from services.tier_upgrade_service import (
    TierUpgradeDowngradeService,
    FeatureUnlockResult,
    DowngradeImpact
)
from database import DatabaseManager

router = APIRouter(prefix="/tier", tags=["tier"])


class TierInfoResponse(BaseModel):
    """Response model for tier information."""
    
    tier: TierLevel
    name: str
    description: str
    features: TierFeatures
    pricing: TierPricing


class AdminTierResponse(BaseModel):
    """Response model for admin's current tier."""
    
    admin_id: int
    current_tier: TierLevel
    features: TierFeatures
    subscription_active: bool
    expires_at: str = None


class TierUpgradeResponse(BaseModel):
    """Response model for tier upgrade request."""
    
    upgrade_request_id: str
    target_tier: TierLevel
    amount: float
    currency: str
    features: TierFeatures


class TierValidationRequest(BaseModel):
    """Request model for tier validation."""
    
    admin_id: int
    action: str
    group_id: str = None


class TierValidationResponse(BaseModel):
    """Response model for tier validation."""
    
    allowed: bool
    current_tier: TierLevel
    required_tier: TierLevel = None
    message: str = None


def get_tier_service() -> TierManagementService:
    """Dependency to get tier management service."""
    db_manager = DatabaseManager()
    return TierManagementService(db_manager)


def get_tier_upgrade_service() -> TierUpgradeDowngradeService:
    """Dependency to get tier upgrade/downgrade service."""
    db_manager = DatabaseManager()
    return TierUpgradeDowngradeService(db_manager)


@router.get("/info", response_model=List[TierInfoResponse])
async def get_all_tiers(tier_service: TierManagementService = Depends(get_tier_service)):
    """Get information about all available tiers."""
    try:
        all_tiers = tier_service.get_all_tiers()
        
        tier_info = []
        for tier_level, config in all_tiers.items():
            tier_info.append(TierInfoResponse(
                tier=tier_level,
                name=config["name"],
                description=config["description"],
                features=config["features"],
                pricing=config["pricing"]
            ))
        
        return tier_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tier information: {str(e)}")


@router.get("/info/{tier}", response_model=TierInfoResponse)
async def get_tier_info(tier: TierLevel, tier_service: TierManagementService = Depends(get_tier_service)):
    """Get information about a specific tier."""
    try:
        config = tier_service.get_tier_info(tier)
        
        return TierInfoResponse(
            tier=tier,
            name=config["name"],
            description=config["description"],
            features=config["features"],
            pricing=config["pricing"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tier information: {str(e)}")


@router.get("/admin/{admin_id}", response_model=AdminTierResponse)
async def get_admin_tier(admin_id: int, tier_service: TierManagementService = Depends(get_tier_service)):
    """Get admin's current tier and subscription status."""
    try:
        current_tier = await tier_service.get_admin_tier(admin_id)
        features = tier_service.get_tier_features(current_tier)
        subscription_active = not await tier_service.check_subscription_expiry(admin_id)
        
        return AdminTierResponse(
            admin_id=admin_id,
            current_tier=current_tier,
            features=features,
            subscription_active=subscription_active
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get admin tier: {str(e)}")


@router.post("/validate", response_model=TierValidationResponse)
async def validate_tier_action(
    request: TierValidationRequest, 
    tier_service: TierManagementService = Depends(get_tier_service)
):
    """Validate if admin can perform an action based on tier limits."""
    try:
        current_tier = await tier_service.get_admin_tier(request.admin_id)
        
        # Check if action is allowed
        allowed = await tier_service.validate_tier_limits(
            request.admin_id, 
            request.action,
            group_id=request.group_id
        )
        
        response = TierValidationResponse(
            allowed=allowed,
            current_tier=current_tier
        )
        
        if not allowed:
            # Determine required tier for the action
            if request.action == "create_group":
                features = tier_service.get_tier_features(current_tier)
                if features.max_groups == 1:
                    response.required_tier = TierLevel.ESSENTIAL
                    response.message = "Upgrade to Essential tier to create more groups"
                elif features.max_groups <= 3:
                    response.required_tier = TierLevel.ADVANCED
                    response.message = "Upgrade to Advanced tier to create more groups"
                else:
                    response.required_tier = TierLevel.EXTENDED
                    response.message = "Upgrade to Extended tier for unlimited groups"
            
            elif request.action in ["access_analytics", "export_data"]:
                response.required_tier = TierLevel.ESSENTIAL
                response.message = f"Upgrade to Essential tier to access {request.action.replace('_', ' ')}"
            
            elif request.action in ["bulk_operations", "custom_schedules"]:
                response.required_tier = TierLevel.ADVANCED
                response.message = f"Upgrade to Advanced tier to access {request.action.replace('_', ' ')}"
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate tier action: {str(e)}")


@router.post("/upgrade", response_model=TierUpgradeResponse)
async def request_tier_upgrade(
    request: TierUpgradeRequest, 
    tier_service: TierManagementService = Depends(get_tier_service)
):
    """Request a tier upgrade."""
    try:
        upgrade_info = await tier_service.create_tier_upgrade_request(request)
        
        return TierUpgradeResponse(
            upgrade_request_id=upgrade_info["upgrade_request_id"],
            target_tier=upgrade_info["target_tier"],
            amount=float(upgrade_info["amount"]),
            currency=upgrade_info["currency"],
            features=upgrade_info["features"]
        )
        
    except TierValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create upgrade request: {str(e)}")


@router.post("/upgrade/{admin_id}/confirm")
async def confirm_tier_upgrade(
    admin_id: int,
    target_tier: TierLevel,
    payment_reference: str,
    tier_service: TierManagementService = Depends(get_tier_service)
):
    """Confirm tier upgrade after successful payment."""
    try:
        success = await tier_service.process_tier_upgrade(admin_id, target_tier, payment_reference)
        
        if success:
            return {"message": "Tier upgrade successful", "new_tier": target_tier}
        else:
            raise HTTPException(status_code=500, detail="Failed to process tier upgrade")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm tier upgrade: {str(e)}")


@router.post("/downgrade/{admin_id}")
async def handle_tier_downgrade(
    admin_id: int,
    tier_service: TierManagementService = Depends(get_tier_service)
):
    """Handle tier downgrade when subscription expires."""
    try:
        new_tier = await tier_service.handle_tier_downgrade(admin_id)
        
        return {
            "message": "Tier downgraded due to subscription expiry",
            "new_tier": new_tier,
            "features": tier_service.get_tier_features(new_tier)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle tier downgrade: {str(e)}")


@router.post("/upgrade/{admin_id}/process")
async def process_immediate_upgrade(
    admin_id: int,
    target_tier: TierLevel,
    payment_reference: str,
    upgrade_service: TierUpgradeDowngradeService = Depends(get_tier_upgrade_service)
):
    """Process immediate tier upgrade with feature unlocking."""
    try:
        result = await upgrade_service.process_immediate_upgrade(admin_id, target_tier, payment_reference)
        
        if result.success:
            return {
                "message": "Tier upgrade successful",
                "target_tier": target_tier,
                "unlocked_features": result.unlocked_features
            }
        else:
            raise HTTPException(status_code=400, detail={"errors": result.errors})
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process tier upgrade: {str(e)}")


@router.get("/downgrade/{admin_id}/impact")
async def assess_downgrade_impact(
    admin_id: int,
    target_tier: TierLevel,
    upgrade_service: TierUpgradeDowngradeService = Depends(get_tier_upgrade_service)
):
    """Assess the impact of downgrading to a target tier."""
    try:
        impact = await upgrade_service.assess_downgrade_impact(admin_id, target_tier)
        
        return {
            "target_tier": target_tier,
            "impact": impact.dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assess downgrade impact: {str(e)}")


@router.post("/downgrade/{admin_id}/process")
async def process_graceful_downgrade(
    admin_id: int,
    target_tier: TierLevel,
    preserve_data: bool = True,
    upgrade_service: TierUpgradeDowngradeService = Depends(get_tier_upgrade_service)
):
    """Process graceful tier downgrade with data preservation."""
    try:
        result = await upgrade_service.process_graceful_downgrade(admin_id, target_tier, preserve_data)
        
        if result.success:
            return {
                "message": "Tier downgrade successful",
                "target_tier": target_tier,
                "disabled_features": result.unlocked_features,  # Actually disabled features
                "data_preserved": preserve_data
            }
        else:
            raise HTTPException(status_code=400, detail={"errors": result.errors})
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process tier downgrade: {str(e)}")


@router.post("/subscription/{admin_id}/expire")
async def handle_subscription_expiry(
    admin_id: int,
    upgrade_service: TierUpgradeDowngradeService = Depends(get_tier_upgrade_service)
):
    """Handle subscription expiry with automatic downgrade."""
    try:
        result = await upgrade_service.handle_subscription_expiry(admin_id)
        
        if result.success:
            return {
                "message": "Subscription expiry handled successfully",
                "disabled_features": result.unlocked_features
            }
        else:
            raise HTTPException(status_code=400, detail={"errors": result.errors})
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle subscription expiry: {str(e)}")