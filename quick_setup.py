#!/usr/bin/env python3
"""
Quick setup script for MyPoolr Circles development environment.
This script helps you get started quickly with local development.
"""

import os
import sys
import subprocess
import platform
import requests
import time
from pathlib import Path

def print_step(step, message):
    """Print a formatted step message."""
    print(f"\n🔧 Step {step}: {message}")
    print("=" * 50)

def run_command(command, check=True, shell=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(command, shell=shell, check=check, 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_redis():
    """Check if Redis is running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True
    except:
        return False

def start_redis_docker():
    """Start Redis using Docker."""
    print("Starting Redis with Docker...")
    success, stdout, stderr = run_command("docker run -d -p 6379:6379 --name mypoolr-redis redis:alpine")
    if success:
        print("✅ Redis started successfully with Docker")
        return True
    else:
        print(f"❌ Failed to start Redis with Docker: {stderr}")
        return False

def check_docker():
    """Check if Docker is available."""
    success, _, _ = run_command("docker --version")
    return success

def setup_environment():
    """Set up the development environment."""
    print("🚀 MyPoolr Circles Quick Setup")
    print("=" * 50)
    
    # Step 1: Check Python version
    print_step(1, "Checking Python version")
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor >= 11:
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro} is supported")
    else:
        print(f"❌ Python {python_version.major}.{python_version.minor} is not supported. Please use Python 3.11+")
        return False
    
    # Step 2: Install Python dependencies
    print_step(2, "Installing Python dependencies")
    
    # Backend dependencies
    print("Installing backend dependencies...")
    os.chdir("backend")
    success, stdout, stderr = run_command("pip install -r requirements.txt")
    if success:
        print("✅ Backend dependencies installed")
    else:
        print(f"❌ Failed to install backend dependencies: {stderr}")
        return False
    
    # Bot dependencies
    print("Installing bot dependencies...")
    os.chdir("../bot")
    success, stdout, stderr = run_command("pip install -r requirements.txt")
    if success:
        print("✅ Bot dependencies installed")
    else:
        print(f"❌ Failed to install bot dependencies: {stderr}")
        return False
    
    os.chdir("..")
    
    # Step 3: Setup Redis
    print_step(3, "Setting up Redis")
    
    if check_redis():
        print("✅ Redis is already running")
    else:
        print("Redis is not running. Attempting to start...")
        
        if check_docker():
            if start_redis_docker():
                # Wait for Redis to start
                print("Waiting for Redis to start...")
                time.sleep(3)
                if check_redis():
                    print("✅ Redis is now running")
                else:
                    print("❌ Redis failed to start properly")
                    return False
            else:
                print("❌ Failed to start Redis with Docker")
                print("Please install Redis manually or use a cloud Redis service")
                return False
        else:
            print("❌ Docker not found. Please install Redis manually:")
            print("  - Windows: Download from https://github.com/microsoftarchive/redis/releases")
            print("  - Or use WSL2: sudo apt install redis-server")
            print("  - Or use a cloud Redis service like Redis Cloud")
            return False
    
    # Step 4: Check environment files
    print_step(4, "Checking environment configuration")
    
    backend_env = Path("backend/.env.local")
    bot_env = Path("bot/.env.local")
    
    if backend_env.exists():
        print("✅ Backend environment file exists")
    else:
        print("❌ Backend .env.local not found")
        print("Please copy backend/.env.example to backend/.env.local and configure it")
        return False
    
    if bot_env.exists():
        print("✅ Bot environment file exists")
    else:
        print("❌ Bot .env.local not found")
        print("Please copy bot/.env.example to bot/.env.local and configure it")
        return False
    
    # Step 5: Test backend
    print_step(5, "Testing backend setup")
    
    print("Running backend tests...")
    os.chdir("backend")
    success, stdout, stderr = run_command("python test_checkpoint.py")
    if success:
        print("✅ Backend tests passed")
    else:
        print(f"❌ Backend tests failed: {stderr}")
        return False
    
    os.chdir("..")
    
    # Step 6: Instructions for next steps
    print_step(6, "Setup Complete! Next Steps")
    
    print("""
✅ Development environment is ready!

To start the system:

1. Start the backend API:
   cd backend
   python main.py

2. Start Celery worker (new terminal):
   cd backend
   celery -A celery_app worker --loglevel=info

3. For webhook development, start ngrok (new terminal):
   ngrok http 8000
   
4. Set your Telegram webhook:
   curl -X POST "https://api.telegram.org/botYOUR_TOKEN/setWebhook" \\
        -H "Content-Type: application/json" \\
        -d '{"url": "https://YOUR_NGROK_URL.ngrok-free.app/webhook"}'

5. Start the bot (new terminal):
   cd bot
   python main.py

📚 For detailed instructions, see SETUP_GUIDE.md
🐛 For troubleshooting, check the logs in each terminal
""")
    
    return True

if __name__ == "__main__":
    try:
        success = setup_environment()
        if success:
            print("\n🎉 Setup completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Setup failed. Please check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)