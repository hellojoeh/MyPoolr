"""Data consistency detection and auto-correction system."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from database import db_manager
from exceptions import DataConsistencyError, ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)


class ConsistencyIssueType(str, Enum):
    """Types of data consistency issues."""
    ORPHANED_RECORD = "orphaned_record"
    MISSING_REFERENCE = "missing_reference"
    INVALID_STATE = "invalid_state"
    CALCULATION_MISMATCH = "calculation_mismatch"
    DUPLICATE_RECORD = "duplicate_record"
    CONSTRAINT_VIOLATION = "constraint_violation"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"


class ConsistencyCheckSeverity(str, Enum):
    """Severity levels for consistency issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ConsistencyIssue:
    """Represents a data consistency issue."""
    issue_type: ConsistencyIssueType
    severity: ConsistencyCheckSeverity
    entity_type: str
    entity_id: str
    description: str
    details: Dict[str, Any]
    auto_correctable: bool = False
    correction_action: Optional[str] = None
    detected_at: datetime = datetime.utcnow()


class DataConsistencyChecker:
    """Comprehensive data consistency detection and correction system."""
    
    def __init__(self):
        self.db = db_manager
        self.issues: List[ConsistencyIssue] = []
    
    async def run_full_consistency_check(self) -> List[ConsistencyIssue]:
        """Run comprehensive consistency checks across all entities."""
        logger.info("Starting full data consistency check")
        
        self.issues = []
        
        # Run all consistency checks
        await self._check_mypoolr_consistency()
        await self._check_member_consistency()
        await self._check_transaction_consistency()
        await self._check_security_deposit_consistency()
        await self._check_rotation_consistency()
        await self._check_tier_consistency()
        await self._check_temporal_consistency()
        
        # Log summary
        logger.info(
            f"Consistency check completed. Found {len(self.issues)} issues: "
            f"Critical: {len([i for i in self.issues if i.severity == ConsistencyCheckSeverity.CRITICAL])}, "
            f"Error: {len([i for i in self.issues if i.severity == ConsistencyCheckSeverity.ERROR])}, "
            f"Warning: {len([i for i in self.issues if i.severity == ConsistencyCheckSeverity.WARNING])}"
        )
        
        return self.issues
    
    async def auto_correct_issues(self, issues: List[ConsistencyIssue] = None) -> Dict[str, Any]:
        """Automatically correct correctable consistency issues."""
        if issues is None:
            issues = self.issues
        
        correctable_issues = [issue for issue in issues if issue.auto_correctable]
        correction_results = {
            "attempted": len(correctable_issues),
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        for issue in correctable_issues:
            try:
                result = await self._apply_correction(issue)
                if result["success"]:
                    correction_results["successful"] += 1
                else:
                    correction_results["failed"] += 1
                correction_results["results"].append(result)
                
            except Exception as e:
                logger.error(f"Failed to correct issue {issue.entity_id}: {str(e)}")
                correction_results["failed"] += 1
                correction_results["results"].append({
                    "issue_id": issue.entity_id,
                    "success": False,
                    "error": str(e)
                })
        
        return correction_results
    
    async def _check_mypoolr_consistency(self):
        """Check MyPoolr entity consistency."""
        try:
            # Get all MyPoolr records
            result = self.db.service_client.table("mypoolr").select("*").execute()
            mypoolrs = result.data or []
            
            for mypoolr in mypoolrs:
                await self._validate_mypoolr_record(mypoolr)
                
        except Exception as e:
            logger.error(f"Error checking MyPoolr consistency: {str(e)}")
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="mypoolr",
                entity_id="unknown",
                description=f"Failed to check MyPoolr consistency: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _validate_mypoolr_record(self, mypoolr: Dict[str, Any]):
        """Validate individual MyPoolr record."""
        mypoolr_id = mypoolr.get("id")
        
        # Check required fields
        required_fields = ["name", "admin_id", "contribution_amount", "member_limit", "tier"]
        for field in required_fields:
            if not mypoolr.get(field):
                self.issues.append(ConsistencyIssue(
                    issue_type=ConsistencyIssueType.INVALID_STATE,
                    severity=ConsistencyCheckSeverity.ERROR,
                    entity_type="mypoolr",
                    entity_id=mypoolr_id,
                    description=f"Missing required field: {field}",
                    details={"field": field, "record": mypoolr}
                ))
        
        # Check contribution amount is positive
        contribution_amount = mypoolr.get("contribution_amount")
        if contribution_amount and float(contribution_amount) <= 0:
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="mypoolr",
                entity_id=mypoolr_id,
                description="Contribution amount must be positive",
                details={"contribution_amount": contribution_amount},
                auto_correctable=False
            ))
        
        # Check member limit is reasonable
        member_limit = mypoolr.get("member_limit")
        if member_limit and (member_limit < 2 or member_limit > 1000):
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.WARNING,
                entity_type="mypoolr",
                entity_id=mypoolr_id,
                description=f"Unusual member limit: {member_limit}",
                details={"member_limit": member_limit}
            ))
    
    async def _check_member_consistency(self):
        """Check Member entity consistency."""
        try:
            # Get all Member records
            result = self.db.service_client.table("member").select("*").execute()
            members = result.data or []
            
            for member in members:
                await self._validate_member_record(member)
                
        except Exception as e:
            logger.error(f"Error checking Member consistency: {str(e)}")
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="member",
                entity_id="unknown",
                description=f"Failed to check Member consistency: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _validate_member_record(self, member: Dict[str, Any]):
        """Validate individual Member record."""
        member_id = member.get("id")
        mypoolr_id = member.get("mypoolr_id")
        
        # Check if referenced MyPoolr exists
        if mypoolr_id:
            mypoolr_result = self.db.service_client.table("mypoolr").select("id").eq("id", mypoolr_id).execute()
            if not mypoolr_result.data:
                self.issues.append(ConsistencyIssue(
                    issue_type=ConsistencyIssueType.MISSING_REFERENCE,
                    severity=ConsistencyCheckSeverity.CRITICAL,
                    entity_type="member",
                    entity_id=member_id,
                    description=f"Member references non-existent MyPoolr: {mypoolr_id}",
                    details={"mypoolr_id": mypoolr_id, "member": member},
                    auto_correctable=False
                ))
        
        # Check security deposit amount
        security_deposit = member.get("security_deposit_amount")
        if security_deposit and float(security_deposit) < 0:
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="member",
                entity_id=member_id,
                description="Security deposit cannot be negative",
                details={"security_deposit_amount": security_deposit},
                auto_correctable=True,
                correction_action="set_zero_security_deposit"
            ))
        
        # Check rotation position
        rotation_position = member.get("rotation_position")
        if rotation_position and rotation_position < 1:
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="member",
                entity_id=member_id,
                description="Rotation position must be positive",
                details={"rotation_position": rotation_position}
            ))
    
    async def _check_transaction_consistency(self):
        """Check Transaction entity consistency."""
        try:
            # Get all Transaction records
            result = self.db.service_client.table("transaction").select("*").execute()
            transactions = result.data or []
            
            for transaction in transactions:
                await self._validate_transaction_record(transaction)
                
        except Exception as e:
            logger.error(f"Error checking Transaction consistency: {str(e)}")
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="transaction",
                entity_id="unknown",
                description=f"Failed to check Transaction consistency: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _validate_transaction_record(self, transaction: Dict[str, Any]):
        """Validate individual Transaction record."""
        transaction_id = transaction.get("id")
        
        # Check amount is positive
        amount = transaction.get("amount")
        if amount and float(amount) <= 0:
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.CONSTRAINT_VIOLATION,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="transaction",
                entity_id=transaction_id,
                description="Transaction amount must be positive",
                details={"amount": amount}
            ))
        
        # Check confirmation consistency
        sender_confirmed = transaction.get("sender_confirmed_at")
        recipient_confirmed = transaction.get("recipient_confirmed_at")
        confirmation_status = transaction.get("confirmation_status")
        
        if confirmation_status == "completed" and (not sender_confirmed or not recipient_confirmed):
            self.issues.append(ConsistencyIssue(
                issue_type=ConsistencyIssueType.INVALID_STATE,
                severity=ConsistencyCheckSeverity.ERROR,
                entity_type="transaction",
                entity_id=transaction_id,
                description="Transaction marked completed but missing confirmations",
                details={
                    "confirmation_status": confirmation_status,
                    "sender_confirmed_at": sender_confirmed,
                    "recipient_confirmed_at": recipient_confirmed
                },
                auto_correctable=True,
                correction_action="fix_confirmation_status"
            ))
    
    async def _check_security_deposit_consistency(self):
        """Check security deposit calculations and consistency."""
        try:
            # Get all MyPoolr groups with members
            mypoolr_result = self.db.service_client.table("mypoolr").select("*").execute()
            mypoolrs = mypoolr_result.data or []
            
            for mypoolr in mypoolrs:
                await self._validate_security_deposits(mypoolr)
                
        except Exception as e:
            logger.error(f"Error checking security deposit consistency: {str(e)}")
    
    async def _validate_security_deposits(self, mypoolr: Dict[str, Any]):
        """Validate security deposits for a MyPoolr group."""
        mypoolr_id = mypoolr.get("id")
        contribution_amount = float(mypoolr.get("contribution_amount", 0))
        
        # Get members for this MyPoolr
        members_result = self.db.service_client.table("member").select("*").eq("mypoolr_id", mypoolr_id).execute()
        members = members_result.data or []
        
        for member in members:
            member_id = member.get("id")
            rotation_position = member.get("rotation_position", 1)
            security_deposit = float(member.get("security_deposit_amount", 0))
            
            # Calculate expected security deposit
            remaining_members = len(members) - rotation_position + 1
            expected_deposit = contribution_amount * remaining_members
            
            # Allow for small floating point differences
            if abs(security_deposit - expected_deposit) > 0.01:
                self.issues.append(ConsistencyIssue(
                    issue_type=ConsistencyIssueType.CALCULATION_MISMATCH,
                    severity=ConsistencyCheckSeverity.WARNING,
                    entity_type="member",
                    entity_id=member_id,
                    description=f"Security deposit mismatch. Expected: {expected_deposit}, Actual: {security_deposit}",
                    details={
                        "expected": expected_deposit,
                        "actual": security_deposit,
                        "rotation_position": rotation_position,
                        "contribution_amount": contribution_amount
                    },
                    auto_correctable=True,
                    correction_action="recalculate_security_deposit"
                ))
    
    async def _check_rotation_consistency(self):
        """Check rotation schedule consistency."""
        # Implementation for rotation consistency checks
        pass
    
    async def _check_tier_consistency(self):
        """Check tier limits and consistency."""
        # Implementation for tier consistency checks
        pass
    
    async def _check_temporal_consistency(self):
        """Check temporal consistency (timestamps, sequences, etc.)."""
        try:
            # Check for future timestamps
            current_time = datetime.utcnow()
            
            # Check MyPoolr created_at timestamps
            result = self.db.service_client.table("mypoolr").select("id, created_at").execute()
            for record in result.data or []:
                created_at = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
                if created_at > current_time + timedelta(minutes=5):  # Allow 5 min clock skew
                    self.issues.append(ConsistencyIssue(
                        issue_type=ConsistencyIssueType.TEMPORAL_INCONSISTENCY,
                        severity=ConsistencyCheckSeverity.WARNING,
                        entity_type="mypoolr",
                        entity_id=record["id"],
                        description=f"Future timestamp detected: {created_at}",
                        details={"created_at": created_at.isoformat()}
                    ))
                    
        except Exception as e:
            logger.error(f"Error checking temporal consistency: {str(e)}")
    
    async def _apply_correction(self, issue: ConsistencyIssue) -> Dict[str, Any]:
        """Apply automatic correction for a consistency issue."""
        correction_actions = {
            "set_zero_security_deposit": self._correct_negative_security_deposit,
            "fix_confirmation_status": self._correct_confirmation_status,
            "recalculate_security_deposit": self._correct_security_deposit_calculation
        }
        
        action = correction_actions.get(issue.correction_action)
        if not action:
            return {
                "issue_id": issue.entity_id,
                "success": False,
                "error": f"No correction action available for: {issue.correction_action}"
            }
        
        try:
            result = await action(issue)
            logger.info(f"Successfully corrected issue {issue.entity_id}: {issue.description}")
            return {
                "issue_id": issue.entity_id,
                "success": True,
                "action": issue.correction_action,
                "result": result
            }
        except Exception as e:
            logger.error(f"Failed to correct issue {issue.entity_id}: {str(e)}")
            return {
                "issue_id": issue.entity_id,
                "success": False,
                "error": str(e)
            }
    
    async def _correct_negative_security_deposit(self, issue: ConsistencyIssue) -> Dict[str, Any]:
        """Correct negative security deposit by setting to zero."""
        result = self.db.service_client.table("member").update({
            "security_deposit_amount": 0
        }).eq("id", issue.entity_id).execute()
        
        return {"updated_deposit": 0}
    
    async def _correct_confirmation_status(self, issue: ConsistencyIssue) -> Dict[str, Any]:
        """Correct transaction confirmation status based on actual confirmations."""
        # Get current transaction state
        result = self.db.service_client.table("transaction").select("*").eq("id", issue.entity_id).execute()
        if not result.data:
            raise Exception("Transaction not found")
        
        transaction = result.data[0]
        sender_confirmed = transaction.get("sender_confirmed_at")
        recipient_confirmed = transaction.get("recipient_confirmed_at")
        
        # Determine correct status
        if sender_confirmed and recipient_confirmed:
            new_status = "completed"
        elif sender_confirmed or recipient_confirmed:
            new_status = "partially_confirmed"
        else:
            new_status = "pending"
        
        # Update status
        update_result = self.db.service_client.table("transaction").update({
            "confirmation_status": new_status
        }).eq("id", issue.entity_id).execute()
        
        return {"new_status": new_status}
    
    async def _correct_security_deposit_calculation(self, issue: ConsistencyIssue) -> Dict[str, Any]:
        """Recalculate and correct security deposit amount."""
        expected_deposit = issue.details.get("expected")
        
        result = self.db.service_client.table("member").update({
            "security_deposit_amount": expected_deposit
        }).eq("id", issue.entity_id).execute()
        
        return {"corrected_deposit": expected_deposit}


# Global consistency checker instance
consistency_checker = DataConsistencyChecker()