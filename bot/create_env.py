#!/usr/bin/env python3
"""
Create virtual environment and install dependencies for MyPoolr Bot
"""

import subprocess
import sys
import os
import venv
from pathlib import Path


def run_command(command, description, cwd=None):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        print(f"✅ {description} completed")
        if result.stdout.strip():
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False


def create_virtual_environment():
    """Create a virtual environment."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    print("🔄 Creating virtual environment...")
    try:
        venv.create("venv", with_pip=True)
        print("✅ Virtual environment created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False


def get_python_executable():
    """Get the Python executable path for the virtual environment."""
    if os.name == 'nt':  # Windows
        return Path("venv/Scripts/python.exe")
    else:  # Unix/Linux/Mac
        return Path("venv/bin/python")


def get_pip_executable():
    """Get the pip executable path for the virtual environment."""
    if os.name == 'nt':  # Windows
        return Path("venv/Scripts/pip.exe")
    else:  # Unix/Linux/Mac
        return Path("venv/bin/pip")


def install_dependencies():
    """Install dependencies in the virtual environment."""
    python_path = get_python_executable()
    
    if not python_path.exists():
        print(f"❌ Python not found at {python_path}")
        return False
    
    # Upgrade pip first using python -m pip
    if not run_command(f'"{python_path}" -m pip install --upgrade pip', "Upgrading pip"):
        print("⚠️  Pip upgrade failed, continuing with installation...")
    
    # Install requirements
    if not run_command(f'"{python_path}" -m pip install -r requirements.txt', "Installing dependencies"):
        return False
    
    return True


def test_installation():
    """Test if the installation was successful."""
    python_path = get_python_executable()
    
    if not python_path.exists():
        print(f"❌ Python not found at {python_path}")
        return False
    
    # Test imports
    test_script = '''
import sys
try:
    import telegram
    print("✅ python-telegram-bot")
except ImportError as e:
    print(f"❌ python-telegram-bot: {e}")
    sys.exit(1)

try:
    import pydantic_settings
    print("✅ pydantic-settings")
except ImportError as e:
    print(f"❌ pydantic-settings: {e}")
    sys.exit(1)

try:
    import httpx
    print("✅ httpx")
except ImportError as e:
    print(f"❌ httpx: {e}")
    sys.exit(1)

try:
    import redis
    print("✅ redis")
except ImportError:
    print("⚠️  redis (optional)")

print("All required packages installed successfully!")
'''
    
    return run_command(f'"{python_path}" -c "{test_script}"', "Testing installation")


def create_activation_scripts():
    """Create activation scripts for easy environment activation."""
    
    # Windows batch file
    with open("activate_env.bat", "w", encoding='utf-8') as f:
        f.write("""@echo off
echo Activating MyPoolr Bot virtual environment...
call venv\\Scripts\\activate.bat
echo.
echo Virtual environment activated!
echo To run the bot: python run_bot.py
echo To deactivate: deactivate
echo.
cmd /k
""")
    
    # Unix shell script
    with open("activate_env.sh", "w", encoding='utf-8') as f:
        f.write("""#!/bin/bash
echo "Activating MyPoolr Bot virtual environment..."
source venv/bin/activate
echo
echo "Virtual environment activated!"
echo "To run the bot: python run_bot.py"
echo "To deactivate: deactivate"
echo
exec "$SHELL"
""")
    
    # Make shell script executable on Unix systems
    try:
        os.chmod("activate_env.sh", 0o755)
    except:
        pass  # Ignore on Windows
    
    print("✅ Activation scripts created:")
    print("   Windows: activate_env.bat")
    print("   Unix/Linux/Mac: ./activate_env.sh")


def main():
    """Main setup function."""
    print("🤖 MyPoolr Bot Environment Setup")
    print("=" * 50)
    
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  You're already in a virtual environment!")
        print("   Deactivate first with: deactivate")
        return False
    
    # Create virtual environment
    if not create_virtual_environment():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Test installation
    if not test_installation():
        return False
    
    # Create activation scripts
    create_activation_scripts()
    
    print("\n" + "=" * 50)
    print("🎉 Environment setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Activate the virtual environment:")
    if os.name == 'nt':
        print("   Windows: activate_env.bat")
    else:
        print("   Unix/Linux/Mac: ./activate_env.sh")
    print("2. Configure your bot token in .env.local")
    print("3. Run the bot: python run_bot.py")
    
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)