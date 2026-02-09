"""Integration module for wiring all MyPoolr Circles components together."""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from config import settings
    from database import DatabaseManager
    from services.payment_interface import PaymentServiceRegistry
    from services.mpesa_service import MPesaSTKPushService, MPesaConfig
    from services.tier_management import TierManagementService
    from celery_app import celery_app
except ImportError as e:
    # Handle import errors gracefully for testing
    logging.warning(f"Import error in integration module: {e}")
    settings = None
    DatabaseManager = None
    PaymentServiceRegistry = None
    MPesaSTKPushService = None
    MPesaConfig = None
    TierManagementService = None
    celery_app = None


logger = logging.getLogger(__name__)


class IntegrationManager:
    """Manages integration between all system components."""
    
    def __init__(self):
        self.db_manager = DatabaseManager() if DatabaseManager else None
        self.payment_registry = PaymentServiceRegistry() if PaymentServiceRegistry else None
        self.tier_service = TierManagementService(self.db_manager) if TierManagementService and self.db_manager else None
        self.notification_service = None  # Will be initialized separately
        self._initialized = False
    
    async def initialize(self):
        """Initialize all integrated components."""
        if self._initialized:
            return
        
        logger.info("Initializing MyPoolr Circles integration...")
        
        # Initialize database connection
        await self._initialize_database()
        
        # Initialize payment services
        await self._initialize_payment_services()
        
        # Initialize notification system
        await self._initialize_notification_system()
        
        # Initialize background task monitoring
        await self._initialize_task_monitoring()
        
        self._initialized = True
        logger.info("MyPoolr Circles integration initialized successfully")
    
    async def _initialize_database(self):
        """Initialize database connections and verify schema."""
        try:
            # Test database connection
            health_check = await self.db_manager.client.table("mypoolr").select("id").limit(1).execute()
            logger.info("Database connection verified")
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
            logger.warning("Application will start but database operations may fail")
            # Don't raise - allow app to start even if tables don't exist yet
    
    async def _initialize_payment_services(self):
        """Initialize and register payment service providers."""
        try:
            # Initialize M-Pesa service if configured
            if all([
                os.getenv("MPESA_CONSUMER_KEY"),
                os.getenv("MPESA_CONSUMER_SECRET"),
                os.getenv("MPESA_BUSINESS_SHORTCODE"),
                os.getenv("MPESA_PASSKEY")
            ]):
                mpesa_config = MPesaConfig(
                    consumer_key=os.getenv("MPESA_CONSUMER_KEY"),
                    consumer_secret=os.getenv("MPESA_CONSUMER_SECRET"),
                    business_short_code=os.getenv("MPESA_BUSINESS_SHORTCODE"),
                    lipa_na_mpesa_passkey=os.getenv("MPESA_PASSKEY"),
                    environment=os.getenv("MPESA_ENVIRONMENT", "sandbox"),
                    callback_url=os.getenv("MPESA_CALLBACK_URL", "https://api.mypoolr.com/payment/mpesa/callback"),
                    timeout_url=os.getenv("MPESA_TIMEOUT_URL", "https://api.mypoolr.com/payment/mpesa/timeout")
                )
                
                mpesa_service = MPesaSTKPushService(mpesa_config)
                self.payment_registry.register_provider(mpesa_service, is_default=True)
                logger.info("M-Pesa payment service initialized")
            else:
                logger.warning("M-Pesa configuration incomplete, service not initialized")
            
            # TODO: Add other payment providers (Flutterwave, etc.)
            
        except Exception as e:
            logger.error(f"Payment services initialization failed: {e}")
            raise
    
    async def _initialize_notification_system(self):
        """Initialize notification system with templates."""
        try:
            # Import notification service here to avoid circular imports
            from services.notification_service import NotificationService
            self.notification_service = NotificationService(self.db_manager)
            
            # Load notification templates
            self.notification_service._load_templates()
            logger.info("Notification system initialized")
        except Exception as e:
            logger.error(f"Notification system initialization failed: {e}")
            raise
    
    async def _initialize_task_monitoring(self):
        """Initialize background task monitoring."""
        try:
            # Test Celery connection
            celery_app.control.ping(timeout=5)
            logger.info("Celery task queue connection verified")
        except Exception as e:
            logger.warning(f"Celery connection test failed: {e}")
    
    # Integration Methods for Business Logic
    
    async def handle_mypoolr_creation(self, mypoolr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MyPoolr creation with tier validation and notifications."""
        try:
            admin_id = mypoolr_data["admin_id"]
            
            # Validate tier limits
            can_create = await self.tier_service.validate_tier_limits(
                admin_id=admin_id,
                action="create_group"
            )
            
            if not can_create:
                current_tier = await self.tier_service.get_admin_tier(admin_id)
                tier_info = self.tier_service.get_tier_info(current_tier)
                
                return {
                    "success": False,
                    "error": "tier_limit_exceeded",
                    "message": f"Your {tier_info['name']} tier allows only {tier_info['features'].max_groups} groups",
                    "upgrade_required": True,
                    "current_tier": current_tier.value
                }
            
            # Create MyPoolr in database
            result = await self.db_manager.client.table("mypoolr").insert(mypoolr_data).execute()
            mypoolr = result.data[0]
            
            logger.info(f"MyPoolr created: {mypoolr['id']} by admin {admin_id}")
            
            return {
                "success": True,
                "mypoolr": mypoolr
            }
            
        except Exception as e:
            logger.error(f"MyPoolr creation failed: {e}")
            return {
                "success": False,
                "error": "creation_failed",
                "message": str(e)
            }
    
    async def handle_member_join(self, join_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle member joining with capacity validation and notifications."""
        try:
            mypoolr_id = join_data["mypoolr_id"]
            
            # Get MyPoolr details
            mypoolr_result = await self.db_manager.client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
            if not mypoolr_result.data:
                return {
                    "success": False,
                    "error": "mypoolr_not_found",
                    "message": "MyPoolr group not found"
                }
            
            mypoolr = mypoolr_result.data[0]
            
            # Validate member capacity
            can_add = await self.tier_service.validate_tier_limits(
                admin_id=mypoolr["admin_id"],
                action="add_member",
                group_id=mypoolr_id
            )
            
            if not can_add:
                admin_tier = await self.tier_service.get_admin_tier(mypoolr["admin_id"])
                tier_info = self.tier_service.get_tier_info(admin_tier)
                
                return {
                    "success": False,
                    "error": "member_limit_exceeded",
                    "message": f"This group has reached the {tier_info['features'].max_members_per_group} member limit for {tier_info['name']} tier",
                    "upgrade_required": True
                }
            
            # Add member to database
            result = await self.db_manager.client.table("members").insert(join_data).execute()
            member = result.data[0]
            
            # Send notifications asynchronously
            try:
                from tasks.notifications import send_member_joined_notifications
                send_member_joined_notifications.delay(mypoolr_id, member["id"])
            except ImportError:
                logger.warning("Could not import notification tasks")
            
            logger.info(f"Member {member['id']} joined MyPoolr {mypoolr_id}")
            
            return {
                "success": True,
                "member": member
            }
            
        except Exception as e:
            logger.error(f"Member join failed: {e}")
            return {
                "success": False,
                "error": "join_failed",
                "message": str(e)
            }
    
    async def handle_contribution_confirmation(self, confirmation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contribution confirmation with rotation advancement."""
        try:
            transaction_id = confirmation_data["transaction_id"]
            confirmer_type = confirmation_data["confirmer_type"]  # "sender" or "recipient"
            
            # Update transaction confirmation
            update_field = f"{confirmer_type}_confirmed_at"
            update_data = {
                update_field: datetime.utcnow().isoformat()
            }
            
            result = await self.db_manager.client.table("transactions").update(update_data).eq("id", transaction_id).execute()
            transaction = result.data[0]
            
            # Check if both parties have confirmed
            if transaction["sender_confirmed_at"] and transaction["recipient_confirmed_at"]:
                # Mark transaction as completed
                await self.db_manager.client.table("transactions").update({
                    "confirmation_status": "completed",
                    "completed_at": datetime.utcnow().isoformat()
                }).eq("id", transaction_id).execute()
                
                # Send confirmation notifications
                try:
                    from tasks.notifications import send_contribution_confirmed_notifications
                    send_contribution_confirmed_notifications.delay(transaction_id)
                except ImportError:
                    logger.warning("Could not import notification tasks")
                
                # Check if rotation should advance
                await self._check_rotation_advancement(transaction["mypoolr_id"])
                
                logger.info(f"Contribution confirmed: {transaction_id}")
                
                return {
                    "success": True,
                    "transaction": transaction,
                    "status": "completed"
                }
            else:
                logger.info(f"Partial confirmation for transaction: {transaction_id}")
                
                return {
                    "success": True,
                    "transaction": transaction,
                    "status": "partially_confirmed"
                }
            
        except Exception as e:
            logger.error(f"Contribution confirmation failed: {e}")
            return {
                "success": False,
                "error": "confirmation_failed",
                "message": str(e)
            }
    
    async def handle_tier_upgrade_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tier upgrade payment processing."""
        try:
            admin_id = payment_data["admin_id"]
            target_tier = payment_data["target_tier"]
            phone_number = payment_data["phone_number"]
            
            # Get payment provider
            provider = self.payment_registry.get_provider_for_country("KE")
            
            # Get tier pricing
            from models.mypoolr import TierLevel
            tier_enum = TierLevel(target_tier)
            pricing = self.tier_service.get_tier_pricing(tier_enum)
            
            # Create payment request
            from services.payment_interface import PaymentRequest
            payment_request = PaymentRequest(
                amount=pricing.monthly_price,
                currency=pricing.currency,
                phone_number=phone_number,
                reference=f"tier_upgrade_{admin_id}_{target_tier}",
                description=f"MyPoolr {target_tier.title()} Tier Upgrade"
            )
            
            # Initiate payment
            payment_response = await provider.initiate_payment(payment_request)
            
            # Store payment record
            payment_record = {
                "admin_id": admin_id,
                "target_tier": target_tier,
                "payment_id": payment_response.payment_id,
                "amount": float(payment_response.amount),
                "currency": payment_response.currency,
                "status": payment_response.status.value,
                "provider": provider.provider_name,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.db_manager.client.table("tier_payments").insert(payment_record).execute()
            
            logger.info(f"Tier upgrade payment initiated: {payment_response.payment_id}")
            
            return {
                "success": True,
                "payment_id": payment_response.payment_id,
                "status": payment_response.status.value,
                "checkout_url": payment_response.checkout_url,
                "expires_at": payment_response.expires_at.isoformat() if payment_response.expires_at else None
            }
            
        except Exception as e:
            logger.error(f"Tier upgrade payment failed: {e}")
            return {
                "success": False,
                "error": "payment_failed",
                "message": str(e)
            }
    
    async def handle_payment_callback(self, provider_name: str, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment callback and process tier upgrades."""
        try:
            # Get payment provider
            provider = self.payment_registry.get_provider(provider_name)
            
            # Process callback
            callback_response = await provider.handle_callback(callback_data)
            
            if callback_response.success:
                # Update payment record
                await self.db_manager.client.table("tier_payments").update({
                    "status": callback_response.status.value,
                    "completed_at": datetime.utcnow().isoformat()
                }).eq("payment_id", callback_response.payment_id).execute()
                
                # If payment completed, process tier upgrade
                if callback_response.status.value == "completed":
                    await self._process_completed_tier_payment(callback_response.payment_id)
                
                logger.info(f"Payment callback processed: {callback_response.payment_id}")
                
                return {
                    "success": True,
                    "payment_id": callback_response.payment_id,
                    "status": callback_response.status.value
                }
            else:
                logger.error(f"Payment callback processing failed: {callback_response.message}")
                return {
                    "success": False,
                    "error": "callback_failed",
                    "message": callback_response.message
                }
            
        except Exception as e:
            logger.error(f"Payment callback handling failed: {e}")
            return {
                "success": False,
                "error": "callback_error",
                "message": str(e)
            }
    
    async def handle_contribution_default(self, mypoolr_id: str, member_id: str, amount: float) -> Dict[str, Any]:
        """Handle contribution default with security deposit usage."""
        try:
            # Trigger default handling task
            try:
                from tasks.defaults import handle_contribution_default
                result = handle_contribution_default.delay(mypoolr_id, member_id, amount)
                
                logger.info(f"Default handling initiated for member {member_id} in MyPoolr {mypoolr_id}")
                
                return {
                    "success": True,
                    "task_id": result.id,
                    "message": "Default handling initiated"
                }
            except ImportError:
                logger.warning("Could not import default handling tasks")
                return {
                    "success": False,
                    "error": "task_import_failed",
                    "message": "Default handling tasks not available"
                }
            
        except Exception as e:
            logger.error(f"Default handling failed: {e}")
            return {
                "success": False,
                "error": "default_handling_failed",
                "message": str(e)
            }
    
    # Private helper methods
    
    async def _check_rotation_advancement(self, mypoolr_id: str):
        """Check if rotation should advance and trigger advancement."""
        try:
            # Get current rotation details
            rotation_result = await self.db_manager.client.table("rotations").select("*").eq(
                "mypoolr_id", mypoolr_id
            ).eq("status", "active").execute()
            
            if not rotation_result.data:
                return
            
            rotation = rotation_result.data[0]
            
            # Check if all contributions are confirmed
            pending_transactions = await self.db_manager.client.table("transactions").select("id").eq(
                "mypoolr_id", mypoolr_id
            ).eq("rotation_id", rotation["id"]).eq("confirmation_status", "pending").execute()
            
            if not pending_transactions.data:
                # All contributions confirmed, advance rotation
                try:
                    from tasks.rotation import advance_rotation_schedule
                    advance_rotation_schedule.delay(mypoolr_id, rotation["id"])
                    logger.info(f"Rotation advancement triggered for MyPoolr {mypoolr_id}")
                except ImportError:
                    logger.warning("Could not import rotation tasks")
            
        except Exception as e:
            logger.error(f"Rotation advancement check failed: {e}")
    
    async def _process_completed_tier_payment(self, payment_id: str):
        """Process completed tier upgrade payment."""
        try:
            # Get payment details
            payment_result = await self.db_manager.client.table("tier_payments").select("*").eq("payment_id", payment_id).execute()
            if not payment_result.data:
                return
            
            payment = payment_result.data[0]
            
            # Process tier upgrade
            from models.mypoolr import TierLevel
            target_tier = TierLevel(payment["target_tier"])
            
            success = await self.tier_service.process_tier_upgrade(
                admin_id=payment["admin_id"],
                target_tier=target_tier,
                payment_reference=payment_id
            )
            
            if success:
                logger.info(f"Tier upgrade completed for admin {payment['admin_id']} to {target_tier.value}")
            else:
                logger.error(f"Tier upgrade processing failed for payment {payment_id}")
            
        except Exception as e:
            logger.error(f"Tier payment processing failed: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system integration status."""
        try:
            status = {
                "integration_initialized": self._initialized,
                "database_connected": False,
                "payment_providers": [],
                "celery_workers": 0,
                "notification_system": False
            }
            
            # Check database
            try:
                await self.db_manager.client.table("mypoolr").select("id").limit(1).execute()
                status["database_connected"] = True
            except:
                pass
            
            # Check payment providers
            status["payment_providers"] = self.payment_registry.list_providers()
            
            # Check Celery workers
            try:
                inspect = celery_app.control.inspect()
                active_workers = inspect.active()
                status["celery_workers"] = len(active_workers) if active_workers else 0
            except:
                pass
            
            # Check notification system
            status["notification_system"] = len(self.notification_service.templates) > 0
            
            return status
            
        except Exception as e:
            logger.error(f"System status check failed: {e}")
            return {"error": str(e)}


# Global integration manager instance
integration_manager = IntegrationManager()


# Initialization function for FastAPI startup
async def initialize_integration():
    """Initialize integration manager."""
    await integration_manager.initialize()


# Cleanup function for FastAPI shutdown
async def cleanup_integration():
    """Cleanup integration resources."""
    logger.info("Cleaning up integration resources...")
    # Add any cleanup logic here