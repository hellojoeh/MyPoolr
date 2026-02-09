"""Validate backend setup without external dependencies."""

import sys
import os
from pathlib import Path


def validate_structure():
    """Validate directory structure."""
    required_files = [
        "main.py",
        "config.py", 
        "database.py",
        "celery_app.py",
        "requirements.txt",
        "models/__init__.py",
        "models/base.py",
        "models/mypoolr.py",
        "models/member.py", 
        "models/transaction.py",
        "api/__init__.py",
        "api/mypoolr.py",
        "api/member.py",
        "api/transaction.py",
        "tasks/__init__.py",
        "tasks/rotation.py",
        "tasks/reminders.py",
        "tasks/defaults.py",
        "tests/__init__.py",
        "tests/test_api.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing files:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    else:
        print("✅ All required files present")
        return True


def validate_imports():
    """Validate that modules can be imported."""
    try:
        # Test basic imports
        from models import MyPoolr, Member, Transaction
        from config import Settings
        print("✅ Model imports successful")
        
        # Test enum imports
        from models.mypoolr import RotationFrequency, TierLevel
        from models.member import MemberStatus, SecurityDepositStatus
        from models.transaction import TransactionType, ConfirmationStatus
        print("✅ Enum imports successful")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def main():
    """Run validation."""
    print("Validating MyPoolr Circles Backend Setup...")
    print("=" * 50)
    
    structure_ok = validate_structure()
    imports_ok = validate_imports()
    
    print("=" * 50)
    if structure_ok and imports_ok:
        print("✅ Backend setup validation PASSED")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure .env file with Supabase credentials")
        print("3. Run the application: python main.py")
        return 0
    else:
        print("❌ Backend setup validation FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())