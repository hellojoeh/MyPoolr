#!/usr/bin/env python3
"""Simple test runner for security deposit tests."""

import sys
import os
from decimal import Decimal

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we need to test
from services.security_deposit import (
    SecurityDepositCalculator,
    calculate_deposit_for_position,
    validate_no_loss_guarantee
)
from models.mypoolr import MyPoolr, RotationFrequency, TierLevel
from models.member import Member, SecurityDepositStatus, MemberStatus


def test_basic_security_deposit_calculation():
    """Test basic security deposit calculation."""
    print("Testing basic security deposit calculation...")
    
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
    expected_pos_1 = Decimal('4000.00')
    assert deposit_pos_1 == expected_pos_1, f"Expected {expected_pos_1}, got {deposit_pos_1}"
    
    # Member at position 3 should cover 2 remaining members
    deposit_pos_3 = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 3)
    expected_pos_3 = Decimal('2000.00')
    assert deposit_pos_3 == expected_pos_3, f"Expected {expected_pos_3}, got {deposit_pos_3}"
    
    # Member at position 5 (last) should cover 0 remaining members
    deposit_pos_5 = SecurityDepositCalculator.calculate_security_deposit(mypoolr, 5)
    expected_pos_5 = Decimal('0.00')
    assert deposit_pos_5 == expected_pos_5, f"Expected {expected_pos_5}, got {deposit_pos_5}"
    
    print("✓ Basic security deposit calculation test passed")


def test_security_deposit_with_multiplier():
    """Test security deposit calculation with multiplier."""
    print("Testing security deposit calculation with multiplier...")
    
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
    assert deposit == expected, f"Expected {expected}, got {deposit}"
    
    print("✓ Security deposit with multiplier test passed")


def test_maximum_loss_scenario():
    """Test maximum loss scenario calculation."""
    print("Testing maximum loss scenario calculation...")
    
    mypoolr = MyPoolr(
        name="Test Group",
        admin_id=12345,
        contribution_amount=Decimal('500'),
        rotation_frequency=RotationFrequency.WEEKLY,
        member_limit=6
    )
    
    # Member at position 1 could cause loss for 5 remaining rotations
    max_loss_pos_1 = SecurityDepositCalculator.calculate_maximum_loss_scenario(mypoolr, 1)
    expected_pos_1 = Decimal('2500')  # 5 * 500
    assert max_loss_pos_1 == expected_pos_1, f"Expected {expected_pos_1}, got {max_loss_pos_1}"
    
    # Member at position 4 could cause loss for 2 remaining rotations
    max_loss_pos_4 = SecurityDepositCalculator.calculate_maximum_loss_scenario(mypoolr, 4)
    expected_pos_4 = Decimal('1000')  # 2 * 500
    assert max_loss_pos_4 == expected_pos_4, f"Expected {expected_pos_4}, got {max_loss_pos_4}"
    
    # Member at position 6 (last) cannot cause loss
    max_loss_pos_6 = SecurityDepositCalculator.calculate_maximum_loss_scenario(mypoolr, 6)
    expected_pos_6 = Decimal('0')
    assert max_loss_pos_6 == expected_pos_6, f"Expected {expected_pos_6}, got {max_loss_pos_6}"
    
    print("✓ Maximum loss scenario test passed")


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing convenience functions...")
    
    # Test calculate_deposit_for_position
    deposit = calculate_deposit_for_position(
        contribution_amount=Decimal('750'),
        member_position=2,
        total_members=5,
        security_multiplier=1.2
    )
    
    # Position 2 covers 3 remaining members: 750 * 3 * 1.2 = 2700
    expected = Decimal('2700.00')
    assert deposit == expected, f"Expected {expected}, got {deposit}"
    
    # Test validate_no_loss_guarantee with valid deposits
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
    assert result is True, "No-loss guarantee validation should pass"
    
    print("✓ Convenience functions test passed")


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("Testing error handling...")
    
    mypoolr = MyPoolr(
        name="Test Group",
        admin_id=12345,
        contribution_amount=Decimal('1000'),
        rotation_frequency=RotationFrequency.MONTHLY,
        member_limit=5
    )
    
    # Test invalid position (0)
    try:
        SecurityDepositCalculator.calculate_security_deposit(mypoolr, 0)
        assert False, "Should have raised ValueError for position 0"
    except ValueError as e:
        assert "Member position must be >= 1" in str(e)
    
    # Test invalid position (> member_limit)
    try:
        SecurityDepositCalculator.calculate_security_deposit(mypoolr, 6)
        assert False, "Should have raised ValueError for position > member_limit"
    except ValueError as e:
        assert "exceeds total members" in str(e)
    
    print("✓ Error handling test passed")


def run_all_tests():
    """Run all tests."""
    print("Running security deposit calculation tests...\n")
    
    try:
        test_basic_security_deposit_calculation()
        test_security_deposit_with_multiplier()
        test_maximum_loss_scenario()
        test_convenience_functions()
        test_error_handling()
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)