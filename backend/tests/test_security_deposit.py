"""Unit tests for security deposit calculation engine."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from decimal import Decimal
from uuid import uuid4
from pydantic import ValidationError

from backend.services.security_deposit import (
    SecurityDepositCalculator,
    SecurityDepositValidator,
    calculate_deposit_for_position,
    validate_no_loss_guarantee
)
from backend.models.mypoolr import MyPoolr, RotationFrequency, TierLevel
from backend.models.member import Member, SecurityDepositStatus, MemberStatus


class TestSecurityDepositCalculator:
    """Test cases for SecurityDepositCalculator."""
    
    def test_calculate_security_deposit_basic(self):
        """Test basic security deposit calculation."""
        mypoolr = MyPoolr(
            name="Test Group",
            admin_id=12345,
            contribution_amount=Decimal('1000'),
            rotation_frequency=RotationFrequency.MONTHLY,
            member_limit=5,
            security_deposit_multiplier=1.0
        )
        
        # Member at position 1 (first to receive) should cover 4 remaining members
        deposit_pos_1 = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 1)
        assert deposit_pos_1 == Decimal('4000.00')
        
        # Member at position 3 should cover 2 remaining members
        deposit_pos_3 = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 3)
        assert deposit_pos_3 == Decimal('2000.00')
        
        # Member at position 5 (last) should cover 0 remaining members
        deposit_pos_5 = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 5)
        assert deposit_pos_5 == Decimal('0.00')
    
    def test_calculate_security_deposit_with_multiplier(self):
        """Test security deposit calculation with multiplier."""
        mypoolr = MyPoolr(
            name="Test Group",
            admin_id=12345,
            contribution_amount=Decimal('1000'),
            rotation_frequency=RotationFrequency.MONTHLY,
            member_limit=4,
            security_deposit_multiplier=1.5
        )
        
        # Member at position 1 with 1.5x multiplier
        deposit = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 1)
        expected = Decimal('1000') * 3 * Decimal('1.5')  # 3 remaining * 1000 * 1.5
        assert deposit == expected
    
    def test_calculate_security_deposit_invalid_position(self):
        """Test security deposit calculation with invalid positions."""
        mypoolr = MyPoolr(
            name="Test Group",
            admin_id=12345,
            contribution_amount=Decimal('1000'),
            rotation_frequency=RotationFrequency.MONTHLY,
            member_limit=5
        )
        
        # Position 0 should raise error
        with pytest.raises(ValueError, match="Member position must be >= 1"):
            SecurityDepositCalculator.calculate_security_deposit(mypoolr, 0)
        
        # Position > member_limit should raise error
        with pytest.raises(ValueError, match="exceeds total members"):
            SecurityDepositCalculator.calculate_security_deposit(mypoolr, 6)
    
    def test_calculate_maximum_loss_scenario(self):
        """Test maximum loss scenario calculation."""
        mypoolr = MyPoolr(
            name="Test Group",
            admin_id=12345,
            contribution_amount=Decimal('500'),
            rotation_frequency=RotationFrequency.WEEKLY,
            member_limit=6
        )
        
        # Member at position 1 could cause loss for 5 remaining rotations
        max_loss_pos_1 = SecurityDepositCalculator.calculate_maximum_loss_scenario(mypoolr, 1)
        assert max_loss_pos_1 == Decimal('2500')  # 5 * 500
        
        # Member at position 4 could cause loss for 2 remaining rotations
        max_loss_pos_4 = SecurityDepositCalculator.calculate_maximum_loss_scenario(mypoolr, 4)
        assert max_loss_pos_4 == Decimal('1000')  # 2 * 500
        
        # Member at position 6 (last) cannot cause loss
        max_loss_pos_6 = SecurityDepositCalculator.calculate_maximum_loss_scenario(mypoolr, 6)
        assert max_loss_pos_6 == Decimal('0')
    
    def test_validate_deposit_sufficiency_sufficient(self):
        """Test deposit sufficiency validation with sufficient deposits."""
        mypoolr = MyPoolr(
            name="Test Group",
            admin_id=12345,
            contribution_amount=Decimal('1000'),
            rotation_frequency=RotationFrequency.MONTHLY,
            member_limit=3
        )
        
        members = [
            Member(
                mypoolr_id=mypoolr.id,
                telegram_id=1001,
                name="Member 1",
                phone_number="1234567890",
                rotation_position=1,
                security_deposit_amount=Decimal('2000')  # Covers 2 remaining * 1000
            ),
            Member(
                mypoolr_id=mypoolr.id,
                telegram_id=1002,
                name="Member 2",
                phone_number="1234567891",
                rotation_position=2,
                security_deposit_amount=Decimal('1000')  # Covers 1 remaining * 1000
            ),
            Member(
                mypoolr_id=mypoolr.id,
                telegram_id=1003,
                name="Member 3",
                phone_number="1234567892",
                rotation_position=3,
                security_deposit_amount=Decimal('0')  # Last member, no coverage needed
            )
        ]
        
        result = SecurityDepositCalculator.validate_deposit_sufficiency(mypoolr, members)
        
        assert result['is_sufficient'] is True
        assert result['potential_shortfall'] == Decimal('0')
        assert len(result['member_analysis']) == 3
        
        # Check individual member analysis
        for analysis in result['member_analysis']:
            assert analysis['is_sufficient'] is True
            assert analysis['coverage_gap'] == Decimal('0')
    
    def test_validate_deposit_sufficiency_insufficient(self):
        """Test deposit sufficiency validation with insufficient deposits."""
        mypoolr = MyPoolr(
            name="Test Group",
            admin_id=12345,
            contribution_amount=Decimal('1000'),
            rotation_frequency=RotationFrequency.MONTHLY,
            member_limit=3
        )
        
        members = [
            Member(
                mypoolr_id=mypoolr.id,
                telegram_id=1001,
                name="Member 1",
                phone_number="1234567890",
                rotation_position=1,
                security_deposit_amount=Decimal('1500')  # Insufficient: needs 2000
            ),
            Member(
                mypoolr_id=mypoolr.id,
                telegram_id=1002,
                name="Member 2",
                phone_number="1234567891",
                rotation_position=2,
                security_deposit_amount=Decimal('500')   # Insufficient: needs 1000
            )
        ]
        
        result = SecurityDepositCalculator.validate_deposit_sufficiency(mypoolr, members)
        
        assert result['is_sufficient'] is False
        assert result['potential_shortfall'] == Decimal('1000')  # 500 + 500 shortfall
        
        # Check that shortfalls are correctly identified
        member_1_analysis = next(a for a in result['member_analysis'] if a['position'] == 1)
        assert member_1_analysis['coverage_gap'] == Decimal('500')
        
        member_2_analysis = next(a for a in result['member_analysis'] if a['position'] == 2)
        assert member_2_analysis['coverage_gap'] == Decimal('500')


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_calculate_deposit_for_position(self):
        """Test quick deposit calculation function."""
        deposit = calculate_deposit_for_position(
            contribution_amount=Decimal('750'),
            member_position=2,
            total_members=5,
            security_multiplier=1.2
        )
        
        # Position 2 covers 3 remaining members: 750 * 3 * 1.2 = 2700
        expected = Decimal('2700.00')
        assert deposit == expected
    
    def test_calculate_deposit_for_position_invalid(self):
        """Test quick deposit calculation with invalid position."""
        with pytest.raises(ValueError, match="Invalid member position"):
            calculate_deposit_for_position(
                contribution_amount=Decimal('1000'),
                member_position=0,
                total_members=5
            )
        
        with pytest.raises(ValueError, match="Invalid member position"):
            calculate_deposit_for_position(
                contribution_amount=Decimal('1000'),
                member_position=6,
                total_members=5
            )
    
    def test_validate_no_loss_guarantee_valid(self):
        """Test no-loss guarantee validation with valid deposits."""
        members_data = [
            {
                'rotation_position': 1,
                'security_deposit_amount': '3000'  # Covers 3 remaining * 1000
            },
            {
                'rotation_position': 2,
                'security_deposit_amount': '2000'  # Covers 2 remaining * 1000
            },
            {
                'rotation_position': 3,
                'security_deposit_amount': '1000'  # Covers 1 remaining * 1000
            },
            {
                'rotation_position': 4,
                'security_deposit_amount': '0'     # Last member, no coverage needed
            }
        ]
        
        result = validate_no_loss_guarantee(members_data, Decimal('1000'))
        assert result is True
    
    def test_validate_no_loss_guarantee_invalid(self):
        """Test no-loss guarantee validation with insufficient deposits."""
        members_data = [
            {
                'rotation_position': 1,
                'security_deposit_amount': '2000'  # Insufficient: needs 3000
            },
            {
                'rotation_position': 2,
                'security_deposit_amount': '2000'  # Covers 2 remaining * 1000
            },
            {
                'rotation_position': 3,
                'security_deposit_amount': '1000'  # Covers 1 remaining * 1000
            },
            {
                'rotation_position': 4,
                'security_deposit_amount': '0'     # Last member, no coverage needed
            }
        ]
        
        result = validate_no_loss_guarantee(members_data, Decimal('1000'))
        assert result is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_single_member_group(self):
        """Test that single member groups are not allowed."""
        with pytest.raises(ValidationError):
            MyPoolr(
                name="Solo Group",
                admin_id=12345,
                contribution_amount=Decimal('1000'),
                rotation_frequency=RotationFrequency.MONTHLY,
                member_limit=1
            )
    
    def test_very_large_amounts(self):
        """Test calculations with large monetary amounts."""
        mypoolr = MyPoolr(
            name="High Value Group",
            admin_id=12345,
            contribution_amount=Decimal('999999.99'),
            rotation_frequency=RotationFrequency.MONTHLY,
            member_limit=10,
            security_deposit_multiplier=2.0
        )
        
        # Should handle large amounts without overflow
        deposit = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 1)
        expected = Decimal('999999.99') * 9 * 2  # 9 remaining * amount * 2x multiplier
        assert deposit == expected
    
    def test_fractional_contributions(self):
        """Test calculations with fractional contribution amounts."""
        mypoolr = MyPoolr(
            name="Fractional Group",
            admin_id=12345,
            contribution_amount=Decimal('33.33'),
            rotation_frequency=RotationFrequency.WEEKLY,
            member_limit=3,
            security_deposit_multiplier=1.1
        )
        
        deposit = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 1)
        # Should round up to ensure sufficient coverage
        expected_base = Decimal('33.33') * 2 * Decimal('1.1')  # 66.66 * 1.1 = 73.326
        expected = expected_base.quantize(Decimal('0.01'), rounding='ROUND_UP')
        assert deposit == expected