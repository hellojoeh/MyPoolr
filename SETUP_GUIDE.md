# MyPoolr Circles Setup Guide

## Prerequisites

- Python 3.11+
- Git
- A Telegram Bot Token (you already have this)
- Supabase account (you already have this configured)

## 1. Redis Setup

### Option A: Local Development (Windows)

**Using Docker (Recommended):**
```bash
# Install Docker Desktop from https://docker.com
# Then run:
docker run -d -p 6379:6379 --name redis redis:alpine
```

**Using WSL2:**
```bash
# Install WSL2 if not already installed
wsl --install

# In WSL terminal:
sudo apt update
sudo apt install redis-server
sudo service redis-server start

# Test Redis
redis-cli ping  # Should return "PONG"
```

**Using Windows Binary:**
1. Download from: https://github.com/microsoftarchive/redis/releases
2. Extract and run `redis-server.exe`
3. Default runs on `localhost:6379`

### Option B: Cloud Redis (Production)

**Redis Cloud (Free Tier):**
1. Go to https://redis.com/redis-enterprise-cloud/
2. Sign up for free account
3. Create a new database
4. Copy the connection string
5. Update your `.env.local`:
   ```
   REDIS_URL=redis://username:password@host:port/0
   ```

## 2. Celery Setup

Celery is already configured. Once Redis is running:

```bash
# Terminal 1: Start the backend API
cd backend
python main.py

# Terminal 2: Start Celery worker
cd backend
celery -A celery_app worker --loglevel=info

# Terminal 3: (Optional) Start Celery Beat for scheduled tasks
cd backend
celery -A celery_app beat --loglevel=info
```

## 3. Telegram Webhook Setup

### Option A: Development with ngrok

1. **Install ngrok:**
   - Download from https://ngrok.com/download
   - Extract and add to PATH
   - Sign up for free account and get auth token

2. **Setup ngrok:**
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

3. **Start your backend:**
   ```bash
   cd backend
   python main.py  # Runs on http://localhost:8000
   ```

4. **Start ngrok tunnel:**
   ```bash
   ngrok http 8000
   ```
   
   This gives you a public URL like: `https://abc123.ngrok-free.app`

5. **Update bot configuration:**
   ```bash
   # Update bot/.env.local
   WEBHOOK_URL=https://abc123.ngrok-free.app/webhook
   ```

6. **Set Telegram webhook:**
   ```bash
   curl -X POST "https://api.telegram.org/bot8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://abc123.ngrok-free.app/webhook"}'
   ```

### Option B: Production Deployment

**Railway (Recommended for beginners):**

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   # or
   curl -fsSL https://railway.app/install.sh | sh
   ```

2. **Deploy:**
   ```bash
   railway login
   railway init
   railway add redis  # Adds Redis service
   railway deploy
   ```

3. **Set environment variables in Railway dashboard:**
   - All your `.env.local` variables
   - `WEBHOOK_URL=https://your-app.railway.app/webhook`

**Render:**

1. Go to https://render.com/
2. Connect your GitHub repository
3. Create a Web Service for the backend
4. Add Redis service
5. Set environment variables
6. Deploy

## 4. Complete Startup Sequence

### Development:
```bash
# Terminal 1: Redis (if using Docker)
docker start redis

# Terminal 2: Backend API
cd backend
python main.py

# Terminal 3: Celery Worker
cd backend
celery -A celery_app worker --loglevel=info

# Terminal 4: ngrok (for webhook)
ngrok http 8000

# Terminal 5: Telegram Bot
cd bot
python main.py
```

### Production:
- Deploy backend to Railway/Render/Heroku
- Redis runs as a service
- Celery runs as a background worker
- Webhook URL points to your deployed backend
- Bot can run on the same server or separately

## 5. Environment Variables Summary

**Backend (.env.local):**
```env
# Supabase (you already have this)
SUPABASE_URL=https://lgfwxvdbkavufbchzvuo.supabase.co
SUPABASE_KEY=your_key
SUPABASE_SERVICE_KEY=your_service_key

# Redis
REDIS_URL=redis://localhost:6379/0  # Local
# REDIS_URL=redis://username:password@host:port/0  # Cloud

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
SECRET_KEY=your_secret_key_here
```

**Bot (.env.local):**
```env
# Telegram
TELEGRAM_BOT_TOKEN=8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4
WEBHOOK_URL=https://your-domain.com/webhook  # Set this after deployment

# Backend
BACKEND_API_URL=http://localhost:8000  # Local
# BACKEND_API_URL=https://your-backend.railway.app  # Production

# Redis
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 6. Testing Your Setup

1. **Test Redis:**
   ```bash
   redis-cli ping  # Should return "PONG"
   ```

2. **Test Backend:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test Celery:**
   ```bash
   # Check if worker is running in the celery terminal
   # Should show "ready" status
   ```

4. **Test Telegram Bot:**
   ```bash
   # Send /start to your bot in Telegram
   # Should receive a response
   ```

## 7. Quick Start Commands

**For immediate testing (all local):**
```bash
# 1. Start Redis with Docker
docker run -d -p 6379:6379 --name redis redis:alpine

# 2. Start backend
cd backend && python main.py &

# 3. Start celery
cd backend && celery -A celery_app worker --loglevel=info &

# 4. Start ngrok
ngrok http 8000 &

# 5. Set webhook (replace URL with ngrok URL)
curl -X POST "https://api.telegram.org/bot8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://YOUR_NGROK_URL.ngrok-free.app/webhook"}'

# 6. Start bot
cd bot && python main.py
```

## Troubleshooting

**Redis Connection Issues:**
- Check if Redis is running: `redis-cli ping`
- Verify port 6379 is not blocked
- Check Redis logs

**Webhook Issues:**
- Ensure HTTPS (not HTTP) for webhook URL
- Check if webhook is set: `curl https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo`
- Verify backend is accessible from internet

**Celery Issues:**
- Check Redis connection
- Verify celery_app.py imports correctly
- Check worker logs for errors

Need help with any specific step? Let me know!