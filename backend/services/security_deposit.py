"""Security deposit calculation engine for MyPoolr Circles.

This module implements bulletproof security deposit calculations that ensure
no member can ever lose money, regardless of when other members default.
"""

import logging
from decimal import Decimal, ROUND_UP
from typing import List, Dict, Any, Optional
from uuid import UUID

from models.mypoolr import MyPoolr, RotationFrequency, TierLevel
from models.member import Member, SecurityDepositStatus
from database import db_manager

logger = logging.getLogger(__name__)


class SecurityDepositCalculator:
    """Handles all security deposit calculations and validations."""
    
    @staticmethod
    def calculate_security_deposit(
        mypoolr: MyPoolr, 
        member_position: int,
        total_members: Optional[int] = None
    ) -> Decimal:
        """
        Calculate bulletproof security deposit amount for a member.
        
        The formula ensures no member can lose money regardless of when others default.
        For member at position N in rotation:
        - Must cover (total_members - N) * contribution_amount
        - This covers worst case where they receive payout and disappear
        
        Args:
            mypoolr: The MyPoolr group configuration
            member_position: Position in rotation (1-based)
            total_members: Total number of members (if None, uses member_limit)
            
        Returns:
            Decimal: Required security deposit amount
            
        Raises:
            ValueError: If inputs are invalid
        """
        if member_position < 1:
            raise ValueError("Member position must be >= 1")
        
        if total_members is None:
            total_members = mypoolr.member_limit
        
        if member_position > total_members:
            raise ValueError(f"Member position {member_position} exceeds total members {total_members}")
        
        # Calculate remaining members after this member's turn
        remaining_members = total_members - member_position
        
        # Base deposit covers all remaining contributions
        base_deposit = mypoolr.contribution_amount * remaining_members
        
        # Apply security multiplier for extra protection
        final_deposit = base_deposit * Decimal(str(mypoolr.security_deposit_multiplier))
        
        # Round up to ensure sufficient coverage
        return final_deposit.quantize(Decimal('0.01'), rounding=ROUND_UP)
    
    @staticmethod
    def calculate_maximum_loss_scenario(mypoolr: MyPoolr, member_position: int) -> Decimal:
        """
        Calculate the maximum possible loss for other members if this member defaults.
        
        This represents the worst-case scenario where the member receives their
        payout and then disappears without making any future contributions.
        
        Args:
            mypoolr: The MyPoolr group configuration
            member_position: Position in rotation (1-based)
            
        Returns:
            Decimal: Maximum possible loss amount
        """
        if member_position < 1 or member_position > mypoolr.member_limit:
            raise ValueError(f"Invalid member position: {member_position}")
        
        # If member is last in rotation, they can't cause loss to others
        if member_position == mypoolr.member_limit:
            return Decimal('0')
        
        # Maximum loss is all contributions they would have made after receiving payout
        remaining_rotations = mypoolr.member_limit - member_position
        max_loss = mypoolr.contribution_amount * remaining_rotations
        
        return max_loss
    
    @staticmethod
    def validate_deposit_sufficiency(
        mypoolr: MyPoolr, 
        members: List[Member]
    ) -> Dict[str, Any]:
        """
        Validate that all security deposits are sufficient to prevent losses.
        
        This function performs comprehensive validation to ensure the no-loss
        guarantee can be maintained under all possible default scenarios.
        
        Args:
            mypoolr: The MyPoolr group configuration
            members: List of all members in the group
            
        Returns:
            Dict containing validation results:
            - is_sufficient: bool
            - total_coverage: Decimal
            - potential_shortfall: Decimal
            - member_analysis: List of per-member analysis
        """
        if not members:
            return {
                'is_sufficient': True,
                'total_coverage': Decimal('0'),
                'potential_shortfall': Decimal('0'),
                'member_analysis': []
            }
        
        total_coverage = Decimal('0')
        potential_shortfall = Decimal('0')
        member_analysis = []
        
        for member in members:
            # Calculate required deposit for this member
            required_deposit = SecurityDepositCalculator.calculate_security_deposit(
                mypoolr, member.rotation_position, len(members)
            )
            
            # Calculate maximum loss this member could cause
            max_loss = SecurityDepositCalculator.calculate_maximum_loss_scenario(
                mypoolr, member.rotation_position
            )
            
            # Check if their deposit covers their potential loss
            coverage_gap = max(Decimal('0'), max_loss - member.security_deposit_amount)
            
            member_analysis.append({
                'member_id': str(member.id),
                'position': member.rotation_position,
                'deposit_amount': member.security_deposit_amount,
                'required_deposit': required_deposit,
                'max_potential_loss': max_loss,
                'coverage_gap': coverage_gap,
                'is_sufficient': coverage_gap == 0
            })
            
            total_coverage += member.security_deposit_amount
            potential_shortfall += coverage_gap
        
        return {
            'is_sufficient': potential_shortfall == 0,
            'total_coverage': total_coverage,
            'potential_shortfall': potential_shortfall,
            'member_analysis': member_analysis
        }
    
    @staticmethod
    def calculate_deposit_for_new_member(
        mypoolr_id: UUID,
        preferred_position: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate security deposit for a new member joining a MyPoolr group.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            preferred_position: Preferred rotation position (if None, assigns next available)
            
        Returns:
            Dict containing:
            - deposit_amount: Decimal
            - assigned_position: int
            - calculation_details: Dict
        """
        # Get MyPoolr and existing members
        mypoolr_data = db_manager.get_mypoolr_by_id(str(mypoolr_id))
        if not mypoolr_data:
            raise ValueError(f"MyPoolr {mypoolr_id} not found")
        
        existing_members = db_manager.get_members_by_mypoolr(str(mypoolr_id))
        
        # Convert to model objects
        mypoolr = MyPoolr(**mypoolr_data)
        members = [Member(**member_data) for member_data in existing_members]
        
        # Check if group is full
        if len(members) >= mypoolr.member_limit:
            raise ValueError("MyPoolr group is at capacity")
        
        # Determine position for new member
        occupied_positions = {member.rotation_position for member in members}
        
        if preferred_position and preferred_position not in occupied_positions:
            assigned_position = preferred_position
        else:
            # Find next available position
            for pos in range(1, mypoolr.member_limit + 1):
                if pos not in occupied_positions:
                    assigned_position = pos
                    break
            else:
                raise ValueError("No available positions (this shouldn't happen)")
        
        # Calculate deposit for this position
        deposit_amount = SecurityDepositCalculator.calculate_security_deposit(
            mypoolr, assigned_position, len(members) + 1
        )
        
        # Calculate maximum loss this member could cause
        max_loss = SecurityDepositCalculator.calculate_maximum_loss_scenario(
            mypoolr, assigned_position
        )
        
        return {
            'deposit_amount': deposit_amount,
            'assigned_position': assigned_position,
            'calculation_details': {
                'contribution_amount': mypoolr.contribution_amount,
                'security_multiplier': mypoolr.security_deposit_multiplier,
                'remaining_members_after_position': (len(members) + 1) - assigned_position,
                'max_potential_loss': max_loss,
                'total_members_after_join': len(members) + 1
            }
        }
    
    @staticmethod
    def recalculate_all_deposits(mypoolr_id: UUID) -> Dict[str, Any]:
        """
        Recalculate security deposits for all members in a group.
        
        This should be called when group configuration changes or members
        are added/removed to ensure all deposits remain sufficient.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            
        Returns:
            Dict containing recalculation results and recommendations
        """
        # Get current data
        mypoolr_data = db_manager.get_mypoolr_by_id(str(mypoolr_id))
        if not mypoolr_data:
            raise ValueError(f"MyPoolr {mypoolr_id} not found")
        
        existing_members = db_manager.get_members_by_mypoolr(str(mypoolr_id))
        
        # Convert to model objects
        mypoolr = MyPoolr(**mypoolr_data)
        members = [Member(**member_data) for member_data in existing_members]
        
        # Calculate new deposits for all members
        recalculation_results = []
        
        for member in members:
            new_deposit = SecurityDepositCalculator.calculate_security_deposit(
                mypoolr, member.rotation_position, len(members)
            )
            
            difference = new_deposit - member.security_deposit_amount
            
            recalculation_results.append({
                'member_id': str(member.id),
                'position': member.rotation_position,
                'current_deposit': member.security_deposit_amount,
                'required_deposit': new_deposit,
                'difference': difference,
                'needs_adjustment': difference != 0
            })
        
        # Validate overall sufficiency
        validation_result = SecurityDepositCalculator.validate_deposit_sufficiency(
            mypoolr, members
        )
        
        return {
            'mypoolr_id': str(mypoolr_id),
            'total_members': len(members),
            'recalculation_results': recalculation_results,
            'validation_result': validation_result,
            'requires_member_action': any(
                result['needs_adjustment'] for result in recalculation_results
            )
        }


class SecurityDepositValidator:
    """Validates security deposit operations and prevents insufficient coverage."""
    
    @staticmethod
    def validate_member_departure(member_id: UUID) -> Dict[str, Any]:
        """
        Validate if a member can safely leave without compromising group security.
        
        Args:
            member_id: UUID of the member wanting to leave
            
        Returns:
            Dict containing validation results and any restrictions
        """
        # This would need to be implemented with actual database queries
        # For now, return a basic structure
        return {
            'can_leave': False,
            'restrictions': [],
            'required_actions': []
        }
    
    @staticmethod
    def validate_payout_eligibility(member_id: UUID) -> Dict[str, Any]:
        """
        Validate if a member is eligible to receive their rotation payout.
        
        Args:
            member_id: UUID of the member
            
        Returns:
            Dict containing eligibility status and requirements
        """
        return {
            'is_eligible': False,
            'requirements_met': [],
            'pending_requirements': []
        }


# Convenience functions for common operations
def calculate_deposit_for_position(
    contribution_amount: Decimal,
    member_position: int,
    total_members: int,
    security_multiplier: float = 1.0
) -> Decimal:
    """
    Quick calculation of security deposit for given parameters.
    
    Args:
        contribution_amount: Amount each member contributes per rotation
        member_position: Position in rotation (1-based)
        total_members: Total number of members in group
        security_multiplier: Security multiplier for extra protection
        
    Returns:
        Decimal: Required security deposit amount
    """
    if member_position < 1 or member_position > total_members:
        raise ValueError("Invalid member position")
    
    remaining_members = total_members - member_position
    base_deposit = contribution_amount * remaining_members
    final_deposit = base_deposit * Decimal(str(security_multiplier))
    
    return final_deposit.quantize(Decimal('0.01'), rounding=ROUND_UP)


def validate_no_loss_guarantee(
    members_data: List[Dict[str, Any]],
    contribution_amount: Decimal
) -> bool:
    """
    Validate that the no-loss guarantee is maintained for all members.
    
    Args:
        members_data: List of member data dictionaries
        contribution_amount: Contribution amount per rotation
        
    Returns:
        bool: True if no-loss guarantee is maintained
    """
    for member_data in members_data:
        position = member_data['rotation_position']
        deposit = Decimal(str(member_data['security_deposit_amount']))
        
        # Calculate maximum loss this member could cause
        remaining_rotations = len(members_data) - position
        max_loss = contribution_amount * remaining_rotations
        
        # Check if deposit covers potential loss
        if deposit < max_loss:
            return False
    
    return True