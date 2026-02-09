#!/usr/bin/env python3
"""
MyPoolr Bot Setup Script
Installs dependencies and checks the environment.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required, but you have {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True


def install_dependencies():
    """Install Python dependencies."""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    # Try pip install
    commands = [
        "pip install -r requirements.txt",
        "pip3 install -r requirements.txt",
        "python -m pip install -r requirements.txt",
        "python3 -m pip install -r requirements.txt"
    ]
    
    for cmd in commands:
        if run_command(cmd, f"Installing dependencies with '{cmd.split()[0]}'"):
            return True
    
    print("❌ Failed to install dependencies with any pip command")
    return False


def check_environment_file():
    """Check if environment file exists."""
    env_files = [".env.local", ".env"]
    
    for env_file in env_files:
        env_path = Path(__file__).parent / env_file
        if env_path.exists():
            print(f"✅ Found environment file: {env_file}")
            
            # Check if bot token is set
            with open(env_path, 'r') as f:
                content = f.read()
                if "TELEGRAM_BOT_TOKEN=" in content and "your_bot_token_here" not in content:
                    print("✅ Bot token appears to be configured")
                    return True
                else:
                    print("⚠️  Bot token needs to be configured")
                    print(f"   Edit {env_file} and set your TELEGRAM_BOT_TOKEN")
                    return False
    
    print("❌ No environment file found (.env.local or .env)")
    print("   Copy .env.example to .env.local and configure your bot token")
    return False


def test_imports():
    """Test if all required modules can be imported."""
    print("🔄 Testing imports...")
    
    try:
        import telegram
        print("✅ python-telegram-bot imported successfully")
    except ImportError:
        print("❌ python-telegram-bot not found")
        return False
    
    try:
        import redis
        print("✅ redis imported successfully")
    except ImportError:
        print("⚠️  redis not found (optional, will use memory storage)")
    
    try:
        import httpx
        print("✅ httpx imported successfully")
    except ImportError:
        print("❌ httpx not found")
        return False
    
    try:
        import pydantic
        print("✅ pydantic imported successfully")
    except ImportError:
        print("❌ pydantic not found")
        return False
    
    return True


def main():
    """Main setup function."""
    print("🤖 MyPoolr Bot Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n💡 Try installing dependencies manually:")
        print("   pip install python-telegram-bot python-dotenv pydantic httpx redis loguru")
        sys.exit(1)
    
    # Test imports
    if not test_imports():
        sys.exit(1)
    
    # Check environment
    env_ok = check_environment_file()
    
    print("\n" + "=" * 40)
    if env_ok:
        print("🎉 Setup completed successfully!")
        print("\nTo start the bot, run:")
        print("   python run_bot.py")
    else:
        print("⚠️  Setup completed with warnings")
        print("\nPlease configure your environment file before running the bot.")
    
    print("\n📚 Next steps:")
    print("1. Make sure your bot token is set in .env.local")
    print("2. Start Redis server (optional, for persistent state)")
    print("3. Run: python run_bot.py")


if __name__ == "__main__":
    main()