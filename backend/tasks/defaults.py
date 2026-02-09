"""Default handling and security deposit tasks with comprehensive consequence management."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from celery_app import celery_app, exponential_backoff_retry
from database import db_manager
from monitoring import task_monitor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=5)
@task_monitor
@exponential_backoff_retry(max_retries=5, base_delay=120)
def handle_contribution_deadline(self, mypoolr_id: str, member_id: str):
    """Process contribution deadline and defaults - legacy task for compatibility."""
    try:
        # Redirect to the new comprehensive default handler
        return handle_contribution_default(mypoolr_id, member_id, "deadline_missed")
        
    except Exception as exc:
        logger.error(f"Failed to handle contribution deadline: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=5)
@task_monitor
@exponential_backoff_retry(max_retries=5, base_delay=120)
def handle_contribution_default(self, mypoolr_id: str, member_id: str, reason: str = "missed_contribution"):
    """Comprehensive default handling with security deposit usage and consequence management."""
    try:
        # Get member details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", member_id
        ).execute()
        
        if not member_result.data:
            raise Exception(f"Member {member_id} not found")
        
        member = member_result.data[0]
        
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", mypoolr_id
        ).execute()
        
        if not mypoolr_result.data:
            raise Exception(f"MyPoolr {mypoolr_id} not found")
        
        mypoolr = mypoolr_result.data[0]
        
        # Check if member has sufficient security deposit
        if member["security_deposit_status"] != "confirmed":
            raise Exception(f"Member {member_id} does not have confirmed security deposit")
        
        contribution_amount = Decimal(str(mypoolr["contribution_amount"]))
        security_deposit = Decimal(str(member["security_deposit_amount"]))
        
        if security_deposit < contribution_amount:
            raise Exception(f"Insufficient security deposit for member {member_id}")
        
        # Use security deposit to cover contribution
        coverage_result = use_security_deposit_for_contribution.delay(
            mypoolr_id, member_id, str(contribution_amount), reason
        )
        
        # Apply default consequences
        consequences_result = apply_default_consequences.delay(
            mypoolr_id, member_id, reason
        )
        
        # Update member status
        update_data = {
            "status": "suspended",
            "security_deposit_status": "used",
            "is_locked_in": True  # Prevent leaving until resolved
        }
        
        db_manager.client.table("member").update(update_data).eq(
            "id", member_id
        ).execute()
        
        # Log default handling
        default_record = {
            "mypoolr_id": mypoolr_id,
            "member_id": member_id,
            "default_type": "contribution_missed",
            "reason": reason,
            "amount_covered": str(contribution_amount),
            "security_deposit_used": str(contribution_amount),
            "handled_at": datetime.utcnow().isoformat(),
            "status": "processed"
        }
        
        # In production, store in defaults table
        # db_manager.client.table("defaults").insert(default_record).execute()
        
        # Notify admin and member
        notify_default_handled.delay(mypoolr_id, member_id, default_record)
        
        return {
            "status": "default_handled",
            "member_id": member_id,
            "amount_covered": str(contribution_amount),
            "consequences_applied": True,
            "handled_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to handle contribution default for member {member_id}: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
@exponential_backoff_retry(max_retries=3, base_delay=60)
def use_security_deposit_for_contribution(self, mypoolr_id: str, member_id: str, amount: str, reason: str):
    """Use member's security deposit to cover missed contribution."""
    try:
        contribution_amount = Decimal(amount)
        
        # Get current rotation recipient
        mypoolr_result = db_manager.client.table("mypoolr").select(
            "*, member(*)"
        ).eq("id", mypoolr_id).execute()
        
        if not mypoolr_result.data:
            raise Exception(f"MyPoolr {mypoolr_id} not found")
        
        mypoolr = mypoolr_result.data[0]
        members = mypoolr.get("member", [])
        
        # Find current recipient
        current_position = mypoolr.get("current_rotation_position", 0)
        recipient = None
        
        for member in members:
            if member["rotation_position"] == current_position + 1:
                recipient = member
                break
        
        if not recipient:
            raise Exception(f"No recipient found for current rotation position")
        
        # Create transaction record for security deposit usage
        transaction_data = {
            "mypoolr_id": mypoolr_id,
            "from_member_id": member_id,
            "to_member_id": recipient["id"],
            "amount": str(contribution_amount),
            "transaction_type": "default_coverage",
            "confirmation_status": "both_confirmed",  # Auto-confirmed since using security deposit
            "sender_confirmed_at": datetime.utcnow().isoformat(),
            "recipient_confirmed_at": datetime.utcnow().isoformat(),
            "metadata": {
                "covered_by": "security_deposit",
                "reason": reason,
                "auto_processed": True
            },
            "notes": f"Contribution covered by security deposit due to {reason}"
        }
        
        transaction_result = db_manager.client.table("transaction").insert(
            transaction_data
        ).execute()
        
        # Update member's security deposit amount
        member_result = db_manager.client.table("member").select("*").eq(
            "id", member_id
        ).execute()
        
        if member_result.data:
            current_deposit = Decimal(str(member_result.data[0]["security_deposit_amount"]))
            new_deposit = current_deposit - contribution_amount
            
            db_manager.client.table("member").update({
                "security_deposit_amount": str(new_deposit)
            }).eq("id", member_id).execute()
        
        logger.info(f"Used security deposit of {contribution_amount} for member {member_id}")
        
        return {
            "status": "deposit_used",
            "member_id": member_id,
            "recipient_id": recipient["id"],
            "amount_used": str(contribution_amount),
            "transaction_id": transaction_result.data[0]["id"] if transaction_result.data else None
        }
        
    except Exception as exc:
        logger.error(f"Failed to use security deposit: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
@exponential_backoff_retry(max_retries=3, base_delay=60)
def apply_default_consequences(self, mypoolr_id: str, member_id: str, reason: str):
    """Apply consequences for member default: rotation removal and replenishment requirements."""
    try:
        # Get member and MyPoolr details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", member_id
        ).execute()
        
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", mypoolr_id
        ).execute()
        
        if not member_result.data or not mypoolr_result.data:
            raise Exception("Member or MyPoolr not found")
        
        member = member_result.data[0]
        mypoolr = mypoolr_result.data[0]
        
        consequences = []
        
        # 1. Remove from future rotations (but keep in group for replenishment)
        if member["rotation_position"] > mypoolr["current_rotation_position"]:
            # Member hasn't received their turn yet - remove from rotation
            update_data = {
                "rotation_position": -1,  # Mark as removed from rotation
                "status": "suspended"
            }
            
            db_manager.client.table("member").update(update_data).eq(
                "id", member_id
            ).execute()
            
            consequences.append("removed_from_rotation")
            
            # Adjust rotation positions of other members
            adjust_rotation_positions.delay(mypoolr_id, member["rotation_position"])
        
        # 2. Calculate replenishment requirement
        contribution_amount = Decimal(str(mypoolr["contribution_amount"]))
        current_deposit = Decimal(str(member["security_deposit_amount"]))
        
        # Calculate required deposit for re-eligibility
        required_deposit = calculate_required_security_deposit(mypoolr, member["rotation_position"])
        replenishment_needed = required_deposit - current_deposit
        
        if replenishment_needed > 0:
            # Create replenishment requirement
            replenishment_data = {
                "mypoolr_id": mypoolr_id,
                "member_id": member_id,
                "amount_required": str(replenishment_needed),
                "reason": f"Security deposit replenishment after {reason}",
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }
            
            # In production, store in replenishment_requirements table
            # db_manager.client.table("replenishment_requirements").insert(replenishment_data).execute()
            
            consequences.append("replenishment_required")
        
        # 3. Set lock-in status to prevent leaving
        db_manager.client.table("member").update({
            "is_locked_in": True
        }).eq("id", member_id).execute()
        
        consequences.append("locked_in")
        
        # 4. Create consequence record
        consequence_record = {
            "mypoolr_id": mypoolr_id,
            "member_id": member_id,
            "default_reason": reason,
            "consequences_applied": consequences,
            "replenishment_amount": str(replenishment_needed) if replenishment_needed > 0 else "0",
            "applied_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        logger.info(f"Applied default consequences for member {member_id}: {consequences}")
        
        return {
            "status": "consequences_applied",
            "member_id": member_id,
            "consequences": consequences,
            "replenishment_needed": str(replenishment_needed) if replenishment_needed > 0 else "0"
        }
        
    except Exception as exc:
        logger.error(f"Failed to apply default consequences: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
def adjust_rotation_positions(self, mypoolr_id: str, removed_position: int):
    """Adjust rotation positions after member removal."""
    try:
        # Get all members with positions after the removed member
        members_result = db_manager.client.table("member").select("*").eq(
            "mypoolr_id", mypoolr_id
        ).gt("rotation_position", removed_position).execute()
        
        # Shift positions down by 1
        for member in members_result.data:
            new_position = member["rotation_position"] - 1
            
            db_manager.client.table("member").update({
                "rotation_position": new_position
            }).eq("id", member["id"]).execute()
        
        logger.info(f"Adjusted rotation positions after removing position {removed_position}")
        
        return {
            "status": "positions_adjusted",
            "removed_position": removed_position,
            "members_adjusted": len(members_result.data)
        }
        
    except Exception as exc:
        logger.error(f"Failed to adjust rotation positions: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
def monitor_default_deadlines(self, mypoolr_id: str):
    """Monitor all pending contributions for deadline violations."""
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select(
            "*, member(*)"
        ).eq("id", mypoolr_id).execute()
        
        if not mypoolr_result.data:
            raise Exception(f"MyPoolr {mypoolr_id} not found")
        
        mypoolr = mypoolr_result.data[0]
        members = mypoolr.get("member", [])
        
        # Calculate current rotation deadline
        frequency_hours = {
            "daily": 24,
            "weekly": 168,
            "monthly": 720
        }.get(mypoolr["rotation_frequency"], 24)
        
        # Assume rotation started at the beginning of current period
        # In production, this would be tracked more precisely
        current_time = datetime.utcnow()
        deadline = current_time + timedelta(hours=frequency_hours)
        
        defaults_detected = []
        
        # Check each member's contribution status
        for member in members:
            if member["status"] != "active":
                continue
                
            # Skip current recipient
            if member["rotation_position"] == mypoolr["current_rotation_position"] + 1:
                continue
            
            # Check for recent confirmed contributions
            transaction_result = db_manager.client.table("transaction").select("*").eq(
                "mypoolr_id", mypoolr_id
            ).eq("from_member_id", member["id"]).eq(
                "transaction_type", "contribution"
            ).eq("confirmation_status", "both_confirmed").execute()
            
            # Check if contribution was made within deadline window
            has_recent_contribution = False
            if transaction_result.data:
                for transaction in transaction_result.data:
                    created_at = datetime.fromisoformat(transaction["created_at"])
                    if created_at >= current_time - timedelta(hours=frequency_hours):
                        has_recent_contribution = True
                        break
            
            # If no recent contribution and deadline passed, trigger default
            if not has_recent_contribution and current_time > deadline:
                handle_contribution_default.delay(mypoolr_id, member["id"], "deadline_violation")
                defaults_detected.append({
                    "member_id": member["id"],
                    "member_name": member["name"],
                    "deadline": deadline.isoformat()
                })
        
        return {
            "status": "monitoring_complete",
            "mypoolr_id": mypoolr_id,
            "defaults_detected": len(defaults_detected),
            "deadline": deadline.isoformat(),
            "defaults": defaults_detected
        }
        
    except Exception as exc:
        logger.error(f"Failed to monitor default deadlines: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=3)
@task_monitor
def notify_default_handled(self, mypoolr_id: str, member_id: str, default_record: Dict[str, Any]):
    """Send notifications about default handling to admin and member."""
    try:
        # Get member and MyPoolr details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", member_id
        ).execute()
        
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", mypoolr_id
        ).execute()
        
        if not member_result.data or not mypoolr_result.data:
            raise Exception("Member or MyPoolr not found")
        
        member = member_result.data[0]
        mypoolr = mypoolr_result.data[0]
        
        # Admin notification
        admin_message = (
            f"🚨 DEFAULT HANDLED: {member['name']} missed their contribution in {mypoolr['name']}. "
            f"Security deposit of {default_record['amount_covered']} was used to cover the contribution. "
            f"Member has been suspended and requires replenishment for re-eligibility."
        )
        
        # Member notification
        member_message = (
            f"❌ Your contribution was missed in {mypoolr['name']}. "
            f"Your security deposit of {default_record['amount_covered']} was used to cover it. "
            f"You are now suspended and must replenish your security deposit to continue participating."
        )
        
        # Log notifications (in production, send to Telegram)
        logger.warning(f"Default notification to admin {mypoolr['admin_id']}: {admin_message}")
        logger.warning(f"Default notification to member {member_id}: {member_message}")
        
        return {
            "status": "notifications_sent",
            "admin_notified": True,
            "member_notified": True,
            "handled_at": default_record["handled_at"]
        }
        
    except Exception as exc:
        logger.error(f"Failed to send default notifications: {exc}")
        raise exc


def calculate_required_security_deposit(mypoolr: Dict[str, Any], rotation_position: int) -> Decimal:
    """Calculate required security deposit for a member position."""
    contribution_amount = Decimal(str(mypoolr["contribution_amount"]))
    member_count = mypoolr.get("member_limit", 10)  # Fallback to limit
    
    # Security deposit should cover remaining rotations after member's turn
    remaining_rotations = max(0, member_count - rotation_position)
    base_deposit = contribution_amount * remaining_rotations
    
    # Apply multiplier
    multiplier = mypoolr.get("security_deposit_multiplier", 1.0)
    return base_deposit * Decimal(str(multiplier))


@celery_app.task(bind=True, max_retries=3)
@task_monitor
def process_replenishment_request(self, mypoolr_id: str, member_id: str, amount: str):
    """Process security deposit replenishment and restore member eligibility."""
    try:
        replenishment_amount = Decimal(amount)
        
        # Get member details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", member_id
        ).execute()
        
        if not member_result.data:
            raise Exception(f"Member {member_id} not found")
        
        member = member_result.data[0]
        
        # Update security deposit
        current_deposit = Decimal(str(member["security_deposit_amount"]))
        new_deposit = current_deposit + replenishment_amount
        
        # Check if replenishment is sufficient
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", mypoolr_id
        ).execute()
        
        if mypoolr_result.data:
            required_deposit = calculate_required_security_deposit(
                mypoolr_result.data[0], 
                member["rotation_position"]
            )
            
            if new_deposit >= required_deposit:
                # Restore member eligibility
                update_data = {
                    "security_deposit_amount": str(new_deposit),
                    "security_deposit_status": "confirmed",
                    "status": "active",
                    "is_locked_in": False
                }
                
                # If they were removed from rotation, they need manual re-addition
                if member["rotation_position"] == -1:
                    update_data["status"] = "pending"  # Requires admin approval for rotation re-entry
                
                db_manager.client.table("member").update(update_data).eq(
                    "id", member_id
                ).execute()
                
                logger.info(f"Member {member_id} replenishment successful, eligibility restored")
                
                return {
                    "status": "replenishment_successful",
                    "member_id": member_id,
                    "amount_replenished": str(replenishment_amount),
                    "new_deposit": str(new_deposit),
                    "eligibility_restored": True
                }
            else:
                # Partial replenishment
                db_manager.client.table("member").update({
                    "security_deposit_amount": str(new_deposit)
                }).eq("id", member_id).execute()
                
                remaining_needed = required_deposit - new_deposit
                
                return {
                    "status": "partial_replenishment",
                    "member_id": member_id,
                    "amount_replenished": str(replenishment_amount),
                    "new_deposit": str(new_deposit),
                    "still_needed": str(remaining_needed)
                }
        
    except Exception as exc:
        logger.error(f"Failed to process replenishment: {exc}")
        raise exc