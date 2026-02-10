"""Integration API endpoints for wired component interactions."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from integration import integration_manager
from audit_logger import audit_logger


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integration", tags=["integration"])


# Request/Response Models
class MyPoolrCreationRequest(BaseModel):
    """Request model for MyPoolr creation."""
    admin_id: int = Field(..., description="Telegram user ID of admin")
    name: str = Field(..., description="MyPoolr group name")
    contribution_amount: float = Field(..., gt=0, description="Contribution amount")
    rotation_frequency: str = Field(..., description="Rotation frequency")
    member_limit: int = Field(..., gt=0, le=100, description="Maximum members")
    tier: str = Field(default="starter", description="Tier level")
    admin_name: Optional[str] = Field(None, description="Admin display name")
    admin_username: Optional[str] = Field(None, description="Admin username")
    country: Optional[str] = Field(default="KE", description="Country code")


class MemberJoinRequest(BaseModel):
    """Request model for member joining."""
    mypoolr_id: str = Field(..., description="MyPoolr group ID")
    telegram_id: int = Field(..., description="Telegram user ID")
    name: str = Field(..., description="Member name")
    phone_number: str = Field(..., description="Phone number")
    security_deposit_amount: float = Field(..., gt=0, description="Security deposit amount")


class ContributionConfirmationRequest(BaseModel):
    """Request model for contribution confirmation."""
    transaction_id: str = Field(..., description="Transaction ID")
    confirmer_type: str = Field(..., pattern="^(sender|recipient)$", description="Who is confirming")
    confirmer_id: int = Field(..., description="Telegram user ID of confirmer")


class TierUpgradePaymentRequest(BaseModel):
    """Request model for tier upgrade payment."""
    admin_id: int = Field(..., description="Telegram user ID of admin")
    target_tier: str = Field(..., description="Target tier level")
    phone_number: str = Field(..., description="Phone number for payment")
    payment_method: str = Field(default="mpesa", description="Payment method")


class DefaultHandlingRequest(BaseModel):
    """Request model for default handling."""
    mypoolr_id: str = Field(..., description="MyPoolr group ID")
    member_id: str = Field(..., description="Defaulting member ID")
    amount: float = Field(..., gt=0, description="Default amount")
    reason: str = Field(default="missed_deadline", description="Default reason")


# Integration Endpoints

@router.get("/status")
async def get_integration_status():
    """Get comprehensive integration system status."""
    try:
        status = await integration_manager.get_system_status()
        return {
            "success": True,
            "status": status,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Failed to get integration status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/mypoolr/create")
async def create_mypoolr_integrated(request: MyPoolrCreationRequest):
    """Create MyPoolr with integrated tier validation and notifications."""
    try:
        # Log the creation attempt
        await audit_logger.log_system_action(
            action="mypoolr_creation_attempt",
            component="integration_api",
            details={"admin_id": request.admin_id, "name": request.name}
        )
        
        # Convert request to dict
        mypoolr_data = request.dict()
        mypoolr_data["created_at"] = "2024-01-01T00:00:00Z"
        mypoolr_data["status"] = "active"
        
        # Handle creation through integration manager
        result = await integration_manager.handle_mypoolr_creation(mypoolr_data)
        
        if not result["success"]:
            if result.get("upgrade_required"):
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": result["error"],
                        "message": result["message"],
                        "upgrade_required": True,
                        "current_tier": result.get("current_tier")
                    }
                )
            else:
                raise HTTPException(status_code=400, detail=result)
        
        # Log successful creation
        await audit_logger.log_system_action(
            action="mypoolr_created",
            component="integration_api",
            details={"mypoolr_id": result["mypoolr"]["id"], "admin_id": request.admin_id}
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated MyPoolr creation failed: {e}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=f"Creation failed: {str(e)}")


@router.post("/member/join")
async def join_member_integrated(request: MemberJoinRequest):
    """Join member with integrated capacity validation and notifications."""
    try:
        # Log the join attempt
        await audit_logger.log_system_action(
            action="member_join_attempt",
            component="integration_api",
            details={"mypoolr_id": request.mypoolr_id, "telegram_id": request.telegram_id}
        )
        
        # Convert request to dict
        join_data = request.dict()
        join_data["joined_at"] = "2024-01-01T00:00:00Z"
        join_data["status"] = "active"
        join_data["security_deposit_status"] = "pending"
        
        # Handle join through integration manager
        result = await integration_manager.handle_member_join(join_data)
        
        if not result["success"]:
            if result.get("upgrade_required"):
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": result["error"],
                        "message": result["message"],
                        "upgrade_required": True
                    }
                )
            else:
                raise HTTPException(status_code=400, detail=result)
        
        # Log successful join
        await audit_logger.log_system_action(
            action="member_joined",
            component="integration_api",
            details={"member_id": result["member"]["id"], "mypoolr_id": request.mypoolr_id}
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated member join failed: {e}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=f"Join failed: {str(e)}")


@router.post("/contribution/confirm")
async def confirm_contribution_integrated(request: ContributionConfirmationRequest):
    """Confirm contribution with integrated rotation advancement."""
    try:
        # Log the confirmation attempt
        await audit_logger.log_system_action(
            action="contribution_confirmation_attempt",
            component="integration_api",
            details={
                "transaction_id": request.transaction_id,
                "confirmer_type": request.confirmer_type,
                "confirmer_id": request.confirmer_id
            }
        )
        
        # Convert request to dict
        confirmation_data = request.dict()
        
        # Handle confirmation through integration manager
        result = await integration_manager.handle_contribution_confirmation(confirmation_data)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        # Log successful confirmation
        await audit_logger.log_system_action(
            action="contribution_confirmed",
            component="integration_api",
            details={
                "transaction_id": request.transaction_id,
                "status": result["status"]
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated contribution confirmation failed: {e}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=f"Confirmation failed: {str(e)}")


@router.post("/tier/upgrade/payment")
async def initiate_tier_upgrade_payment(request: TierUpgradePaymentRequest):
    """Initiate tier upgrade payment with integrated payment processing."""
    try:
        # Log the upgrade attempt
        await audit_logger.log_system_action(
            action="tier_upgrade_payment_attempt",
            component="integration_api",
            details={
                "admin_id": request.admin_id,
                "target_tier": request.target_tier,
                "payment_method": request.payment_method
            }
        )
        
        # Convert request to dict
        payment_data = request.dict()
        
        # Handle payment through integration manager
        result = await integration_manager.handle_tier_upgrade_payment(payment_data)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        # Log successful payment initiation
        await audit_logger.log_system_action(
            action="tier_upgrade_payment_initiated",
            component="integration_api",
            details={
                "admin_id": request.admin_id,
                "payment_id": result["payment_id"],
                "target_tier": request.target_tier
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tier upgrade payment initiation failed: {e}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=f"Payment initiation failed: {str(e)}")


@router.post("/payment/callback/{provider}")
async def handle_payment_callback(provider: str, callback_data: dict):
    """Handle payment callback with integrated tier upgrade processing."""
    try:
        # Log the callback
        await audit_logger.log_system_action(
            action="payment_callback_received",
            component="integration_api",
            details={"provider": provider, "callback_keys": list(callback_data.keys())}
        )
        
        # Handle callback through integration manager
        result = await integration_manager.handle_payment_callback(provider, callback_data)
        
        if not result["success"]:
            # Log callback processing failure
            await audit_logger.log_system_action(
                action="payment_callback_failed",
                component="integration_api",
                details={"provider": provider, "error": result.get("error")}
            )
            raise HTTPException(status_code=400, detail=result)
        
        # Log successful callback processing
        await audit_logger.log_system_action(
            action="payment_callback_processed",
            component="integration_api",
            details={
                "provider": provider,
                "payment_id": result["payment_id"],
                "status": result["status"]
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment callback handling failed: {e}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=f"Callback handling failed: {str(e)}")


@router.post("/default/handle")
async def handle_default_integrated(request: DefaultHandlingRequest):
    """Handle contribution default with integrated security deposit processing."""
    try:
        # Log the default handling attempt
        await audit_logger.log_system_action(
            action="default_handling_attempt",
            component="integration_api",
            details={
                "mypoolr_id": request.mypoolr_id,
                "member_id": request.member_id,
                "amount": request.amount,
                "reason": request.reason
            }
        )
        
        # Handle default through integration manager
        result = await integration_manager.handle_contribution_default(
            request.mypoolr_id,
            request.member_id,
            request.amount
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        # Log successful default handling initiation
        await audit_logger.log_system_action(
            action="default_handling_initiated",
            component="integration_api",
            details={
                "mypoolr_id": request.mypoolr_id,
                "member_id": request.member_id,
                "task_id": result["task_id"]
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated default handling failed: {e}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=f"Default handling failed: {str(e)}")


# Health and monitoring endpoints

@router.get("/health")
async def integration_health_check():
    """Check integration system health."""
    try:
        status = await integration_manager.get_system_status()
        
        # Determine overall health
        is_healthy = (
            status.get("integration_initialized", False) and
            status.get("database_connected", False) and
            len(status.get("payment_providers", [])) > 0
        )
        
        return {
            "healthy": is_healthy,
            "status": status,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Integration health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }


@router.get("/metrics")
async def get_integration_metrics():
    """Get integration system metrics."""
    try:
        # This would collect metrics from various components
        # For now, return basic status
        status = await integration_manager.get_system_status()
        
        return {
            "metrics": {
                "components_initialized": status.get("integration_initialized", False),
                "database_connections": 1 if status.get("database_connected", False) else 0,
                "payment_providers_count": len(status.get("payment_providers", [])),
                "celery_workers_count": status.get("celery_workers", 0),
                "notification_templates_loaded": status.get("notification_system", False)
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to get integration metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics collection failed: {str(e)}")