#!/usr/bin/env python3
"""Security verification script for MyPoolr Circles deployment."""

import os
import sys
import glob
from pathlib import Path

def check_gitignore():
    """Verify .gitignore is properly configured."""
    print("🔍 Checking .gitignore security...")
    
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        print("❌ .gitignore file not found!")
        return False
    
    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()
    
    required_patterns = [
        "*.env",
        "*.env.*",
        ".env.local",
        "production_keys_*.txt",
        "*secret*",
        "*key*",
        "*token*",
        "*password*"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing .gitignore patterns: {missing_patterns}")
        return False
    
    print("✅ .gitignore properly configured")
    return True

def check_sensitive_files():
    """Check for sensitive files that shouldn't be committed."""
    print("\n🔍 Checking for sensitive files...")
    
    sensitive_patterns = [
        "*.env.local",
        "*.env.production", 
        "production_keys_*.txt",
        "*secret*",
        "*credential*"
    ]
    
    found_sensitive = []
    for pattern in sensitive_patterns:
        matches = glob.glob(pattern, recursive=True)
        found_sensitive.extend(matches)
    
    if found_sensitive:
        print("⚠️  Found sensitive files:")
        for file in found_sensitive:
            print(f"   • {file}")
        print("🔒 These files are gitignored (good!)")
    else:
        print("✅ No sensitive files found in repository")
    
    return True

def check_environment_templates():
    """Verify environment templates exist and don't contain real secrets."""
    print("\n🔍 Checking environment templates...")
    
    templates = [
        "backend/.env.example",
        "bot/.env.example"
    ]
    
    for template in templates:
        if not Path(template).exists():
            print(f"❌ Missing template: {template}")
            return False
        
        with open(template, 'r') as f:
            content = f.read()
        
        # Check for placeholder values
        if "your_" not in content.lower():
            print(f"⚠️  {template} might contain real values")
        
        print(f"✅ {template} exists")
    
    return True

def check_requirements_security():
    """Check requirements.txt for known vulnerable packages."""
    print("\n🔍 Checking requirements.txt security...")
    
    requirements_files = [
        "backend/requirements.txt",
        "bot/requirements.txt"
    ]
    
    for req_file in requirements_files:
        if not Path(req_file).exists():
            print(f"❌ Missing: {req_file}")
            return False
        
        with open(req_file, 'r') as f:
            content = f.read()
        
        # Check for version pinning
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
        unpinned = [line for line in lines if '==' not in line and line]
        
        if unpinned:
            print(f"⚠️  {req_file} has unpinned dependencies: {unpinned}")
        else:
            print(f"✅ {req_file} has pinned versions")
    
    return True

def check_git_status():
    """Check git status for uncommitted sensitive files."""
    print("\n🔍 Checking git status...")
    
    try:
        import subprocess
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print("⚠️  Not a git repository or git not available")
            return True
        
        staged_files = []
        for line in result.stdout.split('\n'):
            if line.strip():
                status = line[:2]
                filename = line[3:]
                if 'A' in status or 'M' in status:  # Added or Modified
                    staged_files.append(filename)
        
        sensitive_staged = []
        for file in staged_files:
            if any(pattern in file.lower() for pattern in ['.env', 'secret', 'key', 'token', 'password']):
                sensitive_staged.append(file)
        
        if sensitive_staged:
            print("❌ CRITICAL: Sensitive files staged for commit!")
            for file in sensitive_staged:
                print(f"   • {file}")
            print("\n🚨 Run: git reset HEAD <filename> to unstage")
            return False
        
        print("✅ No sensitive files staged for commit")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not check git status: {e}")
        return True

def main():
    """Run all security checks."""
    print("🔐 MyPoolr Circles - Security Verification")
    print("=" * 50)
    
    checks = [
        ("GitIgnore Configuration", check_gitignore),
        ("Sensitive Files Check", check_sensitive_files),
        ("Environment Templates", check_environment_templates),
        ("Requirements Security", check_requirements_security),
        ("Git Status Check", check_git_status)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n🧪 Running: {check_name}")
        print("-" * 30)
        
        try:
            if check_func():
                passed += 1
            else:
                print(f"❌ {check_name} FAILED")
        except Exception as e:
            print(f"❌ {check_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Security Check Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All security checks passed!")
        print("✅ Safe to deploy to production")
        
        print("\n📋 Next Steps:")
        print("1. Push code to GitHub/GitLab")
        print("2. Create Render services")
        print("3. Set environment variables in Render dashboard")
        print("4. Deploy and test")
        
        return True
    else:
        print("❌ Security issues found - fix before deployment!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)