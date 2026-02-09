"""Main FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import db_manager
from api import mypoolr, member, transaction, tier, payment, integration
from error_handlers import setup_error_handling
from system_recovery import recovery_manager
from audit_logger import audit_logger
from monitoring import system_monitor
from integration import integration_manager, initialize_integration, cleanup_integration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MyPoolr Circles API")
    
    try:
        # Initialize integration manager first
        await initialize_integration()
        
        # Initialize recovery system
        await recovery_manager.initialize_recovery_system()
        
        # Start audit logger
        await audit_logger.start()
        
        # Start monitoring
        await system_monitor.start_monitoring()
        
        # Run initial health check
        health_status = await recovery_manager.health_check()
        logger.info(f"Initial health check: {health_status['overall_status']}")
        
        # Log startup
        await audit_logger.log_system_action(
            action="application_startup",
            component="main_app",
            details={"health_status": health_status}
        )
        
        logger.info("MyPoolr Circles API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        await audit_logger.log_error_event(e)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MyPoolr Circles API")
    
    try:
        # Log shutdown
        await audit_logger.log_system_action(
            action="application_shutdown",
            component="main_app"
        )
        
        # Cleanup integration
        await cleanup_integration()
        
        # Stop audit logger
        await audit_logger.stop()
        
        # Stop monitoring
        await system_monitor.stop_monitoring()
        
        logger.info("MyPoolr Circles API shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="MyPoolr Circles API",
    description="Backend API for MyPoolr Circles savings group management with crypto-grade resilience",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# Set up comprehensive error handling
error_handler = setup_error_handling(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(mypoolr.router)
app.include_router(member.router)
app.include_router(transaction.router)
app.include_router(tier.router)
app.include_router(payment.router)
app.include_router(integration.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "MyPoolr Circles API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Run comprehensive health check
        health_status = await recovery_manager.health_check()
        
        # Log health check
        await audit_logger.log_system_action(
            action="health_check",
            component="health_endpoint",
            details=health_status
        )
        
        status_code = 200 if health_status["overall_status"] == "healthy" else 503
        
        return {
            "status": health_status["overall_status"],
            "timestamp": health_status["timestamp"],
            "components": health_status["components"],
            "recovery_state": health_status["recovery_state"]
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/system/recovery/status")
async def recovery_status():
    """Get system recovery status."""
    try:
        return {
            "recovery_state": recovery_manager.recovery_state.value,
            "component_status": {k: v.value for k, v in recovery_manager.component_status.items()},
            "last_snapshot": recovery_manager.last_snapshot.timestamp.isoformat() if recovery_manager.last_snapshot else None
        }
    except Exception as e:
        logger.error(f"Failed to get recovery status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/system/recovery/trigger")
async def trigger_recovery():
    """Manually trigger system recovery."""
    try:
        # Log recovery trigger
        await audit_logger.log_system_action(
            action="manual_recovery_trigger",
            component="recovery_endpoint"
        )
        
        result = await recovery_manager.detect_and_recover_failures()
        return result
        
    except Exception as e:
        logger.error(f"Manual recovery trigger failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/consistency/check")
async def consistency_check():
    """Run data consistency check."""
    try:
        from data_consistency import consistency_checker
        
        # Log consistency check
        await audit_logger.log_system_action(
            action="consistency_check",
            component="consistency_endpoint"
        )
        
        issues = await consistency_checker.run_full_consistency_check()
        
        return {
            "total_issues": len(issues),
            "issues_by_severity": {
                "critical": len([i for i in issues if i.severity.value == "critical"]),
                "error": len([i for i in issues if i.severity.value == "error"]),
                "warning": len([i for i in issues if i.severity.value == "warning"]),
                "info": len([i for i in issues if i.severity.value == "info"])
            },
            "auto_correctable": len([i for i in issues if i.auto_correctable]),
            "issues": [
                {
                    "type": issue.issue_type.value,
                    "severity": issue.severity.value,
                    "entity_type": issue.entity_type,
                    "entity_id": issue.entity_id,
                    "description": issue.description,
                    "auto_correctable": issue.auto_correctable
                }
                for issue in issues
            ]
        }
        
    except Exception as e:
        logger.error(f"Consistency check failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/monitoring/status")
async def monitoring_status():
    """Get comprehensive monitoring status."""
    try:
        status = system_monitor.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/monitoring/metrics")
async def get_metrics():
    """Get current system metrics."""
    try:
        metrics = await system_monitor.collect_metrics()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to collect metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/monitoring/alerts")
async def get_alerts():
    """Get recent system alerts."""
    try:
        alerts = system_monitor.get_recent_alerts(hours=24)
        return {
            "total_alerts": len(alerts),
            "alerts": [
                {
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold
                }
                for alert in alerts
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/isolation/status")
async def isolation_status():
    """Get failure isolation status."""
    try:
        from failure_isolation import failure_isolation_manager
        status = failure_isolation_manager.get_isolation_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get isolation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/system/isolation/remove/{component}")
async def remove_isolation(component: str):
    """Remove isolation from a component."""
    try:
        from failure_isolation import failure_isolation_manager
        
        # Log isolation removal request
        await audit_logger.log_system_action(
            action="isolation_removal_requested",
            component="isolation_endpoint",
            details={"component": component}
        )
        
        result = await failure_isolation_manager.remove_isolation(component, reason="manual_admin")
        return result
        
    except Exception as e:
        logger.error(f"Failed to remove isolation: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


# Integration endpoints
@app.get("/system/integration/status")
async def integration_status():
    """Get integration system status."""
    try:
        status = await integration_manager.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get integration status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Telegram Bot Webhook Endpoints
@app.post("/webhook/telegram/notification")
async def telegram_notification_webhook(notification_data: dict):
    """Send notification to Telegram bot."""
    try:
        # This would integrate with the Telegram bot's webhook handler
        # For now, we'll log the notification
        logger.info(f"Telegram notification webhook: {notification_data}")
        
        # In production, this would send HTTP request to bot's webhook endpoint
        # or use a message queue for reliable delivery
        
        return {
            "success": True,
            "message": "Notification webhook processed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Telegram notification webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/telegram/system")
async def telegram_system_webhook(webhook_data: dict):
    """Send system webhook to Telegram bot."""
    try:
        # This would integrate with the Telegram bot's system webhook handler
        logger.info(f"Telegram system webhook: {webhook_data}")
        
        # In production, this would send HTTP request to bot's webhook endpoint
        
        return {
            "success": True,
            "message": "System webhook processed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Telegram system webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integration/mypoolr/create")
async def create_mypoolr_integrated(mypoolr_data: dict):
    """Create MyPoolr with integrated tier validation and notifications."""
    try:
        result = await integration_manager.handle_mypoolr_creation(mypoolr_data)
        
        if not result["success"]:
            if result.get("upgrade_required"):
                raise HTTPException(status_code=402, detail=result)
            else:
                raise HTTPException(status_code=400, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated MyPoolr creation failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integration/member/join")
async def join_member_integrated(join_data: dict):
    """Join member with integrated capacity validation and notifications."""
    try:
        result = await integration_manager.handle_member_join(join_data)
        
        if not result["success"]:
            if result.get("upgrade_required"):
                raise HTTPException(status_code=402, detail=result)
            else:
                raise HTTPException(status_code=400, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated member join failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integration/contribution/confirm")
async def confirm_contribution_integrated(confirmation_data: dict):
    """Confirm contribution with integrated rotation advancement."""
    try:
        result = await integration_manager.handle_contribution_confirmation(confirmation_data)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated contribution confirmation failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integration/tier/upgrade/payment")
async def initiate_tier_upgrade_payment(payment_data: dict):
    """Initiate tier upgrade payment with integrated payment processing."""
    try:
        result = await integration_manager.handle_tier_upgrade_payment(payment_data)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tier upgrade payment initiation failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integration/payment/callback/{provider}")
async def handle_payment_callback(provider: str, callback_data: dict):
    """Handle payment callback with integrated tier upgrade processing."""
    try:
        result = await integration_manager.handle_payment_callback(provider, callback_data)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment callback handling failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integration/default/handle")
async def handle_default_integrated(default_data: dict):
    """Handle contribution default with integrated security deposit processing."""
    try:
        mypoolr_id = default_data["mypoolr_id"]
        member_id = default_data["member_id"]
        amount = default_data["amount"]
        
        result = await integration_manager.handle_contribution_default(mypoolr_id, member_id, amount)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Integrated default handling failed: {str(e)}")
        await audit_logger.log_error_event(e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )