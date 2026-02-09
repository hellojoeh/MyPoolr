#!/usr/bin/env python3
"""Deploy MyPoolr Circles to production."""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_railway_cli():
    """Check if Railway CLI is installed."""
    success, stdout, stderr = run_command("railway --version")
    return success

def install_railway_cli():
    """Install Railway CLI."""
    print("📦 Installing Railway CLI...")
    
    # Try npm first
    success, stdout, stderr = run_command("npm install -g @railway/cli")
    if success:
        print("✅ Railway CLI installed via npm")
        return True
    
    # Try PowerShell installer
    print("Trying PowerShell installer...")
    success, stdout, stderr = run_command(
        'iwr -useb https://railway.app/install.ps1 | iex',
        shell=True
    )
    if success:
        print("✅ Railway CLI installed via PowerShell")
        return True
    
    print("❌ Failed to install Railway CLI")
    print("Please install manually from: https://railway.app/cli")
    return False

def create_railway_configs():
    """Create Railway configuration files."""
    
    # Backend railway.toml
    backend_config = """[build]
builder = "nixpacks"

[deploy]
startCommand = "python main.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"

[environments.production.variables]
ENVIRONMENT = "production"
"""

    # Bot railway.toml  
    bot_config = """[build]
builder = "nixpacks"

[deploy]
startCommand = "python main.py"
restartPolicyType = "on_failure"

[environments.production.variables]
ENVIRONMENT = "production"
"""

    # Create backend config
    backend_path = Path("backend/railway.toml")
    with open(backend_path, 'w') as f:
        f.write(backend_config)
    print(f"✅ Created {backend_path}")

    # Create bot config
    bot_path = Path("bot/railway.toml")
    with open(bot_path, 'w') as f:
        f.write(bot_config)
    print(f"✅ Created {bot_path}")

def create_requirements_files():
    """Ensure requirements.txt files exist."""
    
    backend_requirements = """fastapi==0.104.1
uvicorn==0.24.0
supabase==2.0.2
redis==5.0.1
celery==5.3.4
python-telegram-bot==20.7
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
requests==2.31.0
psutil==5.9.6
"""

    bot_requirements = """python-telegram-bot==20.7
redis==5.0.1
requests==2.31.0
python-dotenv==1.0.0
pydantic==2.5.0
"""

    # Backend requirements
    backend_req_path = Path("backend/requirements.txt")
    if not backend_req_path.exists():
        with open(backend_req_path, 'w') as f:
            f.write(backend_requirements)
        print(f"✅ Created {backend_req_path}")

    # Bot requirements
    bot_req_path = Path("bot/requirements.txt")
    if not bot_req_path.exists():
        with open(bot_req_path, 'w') as f:
            f.write(bot_requirements)
        print(f"✅ Created {bot_req_path}")

def deploy_to_railway():
    """Deploy to Railway."""
    
    print("🚀 Deploying to Railway...")
    
    # Login to Railway
    print("1. Logging into Railway...")
    success, stdout, stderr = run_command("railway login")
    if not success:
        print("❌ Failed to login to Railway")
        print("Please run 'railway login' manually")
        return False
    
    # Initialize project
    print("2. Initializing Railway project...")
    success, stdout, stderr = run_command("railway init")
    if not success:
        print("⚠️ Project might already exist, continuing...")
    
    # Add Redis service
    print("3. Adding Redis service...")
    success, stdout, stderr = run_command("railway add redis")
    if not success:
        print("⚠️ Redis service might already exist, continuing...")
    
    # Deploy backend
    print("4. Deploying backend...")
    success, stdout, stderr = run_command("railway up", cwd="backend")
    if not success:
        print(f"❌ Backend deployment failed: {stderr}")
        return False
    
    print("✅ Backend deployed successfully!")
    
    # Deploy bot
    print("5. Deploying bot...")
    success, stdout, stderr = run_command("railway up", cwd="bot")
    if not success:
        print(f"❌ Bot deployment failed: {stderr}")
        return False
    
    print("✅ Bot deployed successfully!")
    
    return True

def show_next_steps():
    """Show next steps after deployment."""
    
    print("\n🎉 Deployment Complete!")
    print("=" * 50)
    
    print("\n📋 Next Steps:")
    print("1. Go to railway.app dashboard")
    print("2. Get your backend URL (e.g., https://backend-production-abc123.up.railway.app)")
    print("3. Update bot/.env.local with the backend URL:")
    print("   BACKEND_API_URL=https://your-backend-url")
    print("   WEBHOOK_URL=https://your-backend-url/webhook")
    print("4. Set environment variables in Railway dashboard")
    print("5. Run: python setup_webhook.py")
    print("6. Test your bot!")
    
    print("\n🔧 Environment Variables to Set in Railway:")
    print("Backend Service:")
    print("- All variables from backend/.env.local")
    print("Bot Service:")
    print("- All variables from bot/.env.local")
    
    print("\n📊 Monitoring:")
    print("- Check Railway logs for any errors")
    print("- Test webhook with: python setup_webhook.py")
    print("- Monitor bot responses in Telegram")

def main():
    """Main deployment function."""
    
    print("🚀 MyPoolr Circles - Production Deployment")
    print("=" * 50)
    
    # Check if Railway CLI is installed
    if not check_railway_cli():
        print("Railway CLI not found. Installing...")
        if not install_railway_cli():
            return False
    else:
        print("✅ Railway CLI found")
    
    # Create configuration files
    print("\n📁 Creating configuration files...")
    create_railway_configs()
    create_requirements_files()
    
    # Ask user if they want to deploy
    print("\n🤔 Ready to deploy to Railway?")
    print("This will:")
    print("- Create a new Railway project")
    print("- Add Redis service")
    print("- Deploy backend and bot")
    
    choice = input("\nProceed with deployment? (y/N): ").strip().lower()
    
    if choice != 'y':
        print("Deployment cancelled.")
        print("You can deploy manually later with: railway up")
        return True
    
    # Deploy to Railway
    if deploy_to_railway():
        show_next_steps()
        return True
    else:
        print("❌ Deployment failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)