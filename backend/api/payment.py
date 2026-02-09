"""Payment API endpoints."""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from services.payment_interface import (
    PaymentServiceRegistry,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
    PaymentServiceError
)
from services.mpesa_service import MPesaSTKPushService, MPesaConfig
from database import DatabaseManager

router = APIRouter(prefix="/payment", tags=["payment"])


class PaymentInitiationRequest(BaseModel):
    """Request model for payment initiation."""
    
    admin_id: int = Field(..., description="Admin ID requesting payment")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="KES", description="Currency code")
    phone_number: str = Field(..., description="Customer phone number")
    description: str = Field(..., description="Payment description")
    provider: str = Field(default="mpesa", description="Payment provider")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PaymentInitiationResponse(BaseModel):
    """Response model for payment initiation."""
    
    payment_id: str = Field(..., description="Payment ID")
    status: PaymentStatus = Field(..., description="Payment status")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    provider: str = Field(..., description="Payment provider")
    expires_at: str = None
    message: str = Field(default="Payment initiated successfully")


class PaymentStatusResponse(BaseModel):
    """Response model for payment status."""
    
    payment_id: str = Field(..., description="Payment ID")
    status: PaymentStatus = Field(..., description="Payment status")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    reference: str = Field(..., description="Payment reference")
    provider_reference: str = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentCallbackResponse(BaseModel):
    """Response model for payment callbacks."""
    
    success: bool = Field(..., description="Whether callback was processed")
    message: str = Field(default="Callback processed successfully")


# Global payment service registry
payment_registry = PaymentServiceRegistry()


def get_payment_registry() -> PaymentServiceRegistry:
    """Dependency to get payment service registry."""
    return payment_registry


def initialize_payment_services():
    """Initialize payment services with configuration."""
    # Initialize M-Pesa service (you would get these from environment variables)
    mpesa_config = MPesaConfig(
        consumer_key="your_consumer_key",
        consumer_secret="your_consumer_secret",
        business_short_code="174379",  # Test shortcode
        lipa_na_mpesa_passkey="your_passkey",
        environment="sandbox",
        callback_url="https://your-domain.com/api/payment/callback/mpesa",
        timeout_url="https://your-domain.com/api/payment/timeout/mpesa"
    )
    
    mpesa_service = MPesaSTKPushService(mpesa_config)
    payment_registry.register_provider(mpesa_service, is_default=True)


@router.get("/providers")
async def get_payment_providers(registry: PaymentServiceRegistry = Depends(get_payment_registry)):
    """Get list of available payment providers."""
    try:
        providers = []
        for provider_name in registry.list_providers():
            provider = registry.get_provider(provider_name)
            providers.append({
                "name": provider.provider_name,
                "supported_currencies": provider.supported_currencies,
                "supported_countries": provider.supported_countries
            })
        
        return {
            "providers": providers,
            "supported_currencies": registry.get_supported_currencies(),
            "supported_countries": registry.get_supported_countries()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment providers: {str(e)}")


@router.post("/initiate", response_model=PaymentInitiationResponse)
async def initiate_payment(
    request: PaymentInitiationRequest,
    registry: PaymentServiceRegistry = Depends(get_payment_registry)
):
    """Initiate a payment with the specified provider."""
    try:
        # Get payment provider
        provider = registry.get_provider(request.provider)
        
        # Create payment request
        payment_request = PaymentRequest(
            amount=request.amount,
            currency=request.currency,
            phone_number=request.phone_number,
            reference=f"tier_upgrade_{request.admin_id}_{int(datetime.utcnow().timestamp())}",
            description=request.description,
            metadata=request.metadata
        )
        
        # Initiate payment
        payment_response = await provider.initiate_payment(payment_request)
        
        # Store payment record in database
        db_manager = DatabaseManager()
        payment_data = {
            "payment_id": payment_response.payment_id,
            "admin_id": request.admin_id,
            "provider": request.provider,
            "amount": float(payment_response.amount),
            "currency": payment_response.currency,
            "status": payment_response.status.value,
            "reference": payment_response.reference,
            "provider_reference": payment_response.provider_reference,
            "phone_number": request.phone_number,
            "description": request.description,
            "expires_at": payment_response.expires_at.isoformat() if payment_response.expires_at else None,
            "metadata": payment_response.metadata,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await db_manager.client.table("payments").insert(payment_data).execute()
        
        return PaymentInitiationResponse(
            payment_id=payment_response.payment_id,
            status=payment_response.status,
            amount=float(payment_response.amount),
            currency=payment_response.currency,
            provider=request.provider,
            expires_at=payment_response.expires_at.isoformat() if payment_response.expires_at else None
        )
        
    except PaymentServiceError as e:
        raise HTTPException(status_code=400, detail=f"Payment initiation failed: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate payment: {str(e)}")


@router.get("/status/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: str,
    provider: str = "mpesa",
    registry: PaymentServiceRegistry = Depends(get_payment_registry)
):
    """Get payment status from provider."""
    try:
        # Get payment provider
        payment_provider = registry.get_provider(provider)
        
        # Query payment status
        payment_response = await payment_provider.query_payment_status(payment_id)
        
        # Update payment record in database
        db_manager = DatabaseManager()
        await db_manager.client.table("payments").update({
            "status": payment_response.status.value,
            "provider_reference": payment_response.provider_reference,
            "metadata": payment_response.metadata,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("payment_id", payment_id).execute()
        
        return PaymentStatusResponse(
            payment_id=payment_response.payment_id,
            status=payment_response.status,
            amount=float(payment_response.amount),
            currency=payment_response.currency,
            reference=payment_response.reference,
            provider_reference=payment_response.provider_reference,
            metadata=payment_response.metadata
        )
        
    except PaymentServiceError as e:
        raise HTTPException(status_code=400, detail=f"Payment status query failed: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment status: {str(e)}")


@router.post("/callback/mpesa", response_model=PaymentCallbackResponse)
async def handle_mpesa_callback(
    request: Request,
    registry: PaymentServiceRegistry = Depends(get_payment_registry)
):
    """Handle M-Pesa payment callback."""
    try:
        # Get callback data
        callback_data = await request.json()
        
        # Get M-Pesa provider
        provider = registry.get_provider("mpesa")
        
        # Process callback
        callback_response = await provider.handle_callback(callback_data)
        
        if callback_response.success:
            # Update payment record in database
            db_manager = DatabaseManager()
            await db_manager.client.table("payments").update({
                "status": callback_response.status.value,
                "completed_at": datetime.utcnow().isoformat() if callback_response.status == PaymentStatus.COMPLETED else None,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("payment_id", callback_response.payment_id).execute()
            
            # If payment is completed, trigger tier upgrade
            if callback_response.status == PaymentStatus.COMPLETED:
                await _process_successful_payment(callback_response.payment_id)
        
        return PaymentCallbackResponse(
            success=callback_response.success,
            message=callback_response.message
        )
        
    except PaymentServiceError as e:
        raise HTTPException(status_code=400, detail=f"Callback processing failed: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process callback: {str(e)}")


@router.post("/timeout/mpesa")
async def handle_mpesa_timeout(request: Request):
    """Handle M-Pesa payment timeout."""
    try:
        # Get timeout data
        timeout_data = await request.json()
        
        # Extract payment ID
        checkout_request_id = timeout_data.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
        
        if checkout_request_id:
            # Update payment record as expired
            db_manager = DatabaseManager()
            await db_manager.client.table("payments").update({
                "status": PaymentStatus.EXPIRED.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("payment_id", checkout_request_id).execute()
        
        return {"message": "Timeout processed successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process timeout: {str(e)}")


async def _process_successful_payment(payment_id: str):
    """Process successful payment and trigger tier upgrade."""
    try:
        db_manager = DatabaseManager()
        
        # Get payment details
        payment_result = await db_manager.client.table("payments").select("*").eq("payment_id", payment_id).single().execute()
        
        if not payment_result.data:
            return
        
        payment = payment_result.data
        admin_id = payment["admin_id"]
        
        # Get corresponding tier upgrade request
        upgrade_result = await db_manager.client.table("tier_upgrade_requests").select("*").eq("admin_id", admin_id).eq("status", "pending").single().execute()
        
        if upgrade_result.data:
            upgrade_request = upgrade_result.data
            target_tier = upgrade_request["target_tier"]
            
            # Import here to avoid circular imports
            from services.tier_upgrade_service import TierUpgradeDowngradeService
            from models.mypoolr import TierLevel
            
            upgrade_service = TierUpgradeDowngradeService(db_manager)
            result = await upgrade_service.process_immediate_upgrade(
                admin_id, 
                TierLevel(target_tier), 
                payment_id
            )
            
            if result.success:
                print(f"Tier upgrade successful for admin {admin_id} to {target_tier}")
                print(f"Unlocked features: {result.unlocked_features}")
            else:
                print(f"Tier upgrade failed for admin {admin_id}: {result.errors}")
    
    except Exception as e:
        print(f"Error processing successful payment {payment_id}: {e}")


# Initialize payment services on module load
initialize_payment_services()