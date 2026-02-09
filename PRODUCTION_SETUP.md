# MyPoolr Circles - Production Deployment Guide

## 🌐 Production Deployment Options

### Option 1: Railway (Recommended - Easiest)
**Pros:** Simple deployment, built-in Redis, automatic HTTPS, free tier
**Cons:** Limited free tier resources

### Option 2: Render
**Pros:** Good free tier, easy deployment, automatic HTTPS
**Cons:** Slower cold starts on free tier

### Option 3: DigitalOcean App Platform
**Pros:** Reliable, good performance, reasonable pricing
**Cons:** No free tier, requires payment

### Option 4: Heroku
**Pros:** Well-established, many addons
**Cons:** No free tier anymore, more expensive

## 🚀 Railway Deployment (Recommended)

### Step 1: Prepare Your Code

1. **Create production environment files:**
   ```bash
   # Create production environment files
   cp backend/.env.local backend/.env.production
   cp bot/.env.local bot/.env.production
   ```

2. **Update environment for production:**
   - Set `ENVIRONMENT=production`
   - Set `DEBUG=False`
   - Generate secure API keys

### Step 2: Deploy to Railway

1. **Install Railway CLI:**
   ```bash
   # Windows (PowerShell)
   iwr -useb https://railway.app/install.ps1 | iex
   
   # Or using npm
   npm install -g @railway/cli
   ```

2. **Initialize Railway project:**
   ```bash
   railway login
   railway init
   ```

3. **Add services:**
   ```bash
   # Add Redis service
   railway add redis
   
   # Deploy backend
   railway up --service backend
   
   # Deploy bot (separate service)
   railway up --service bot
   ```

4. **Set environment variables in Railway dashboard:**
   - Go to railway.app dashboard
   - Set all your environment variables
   - Get the backend URL from Railway

### Step 3: Configure Production URLs

Railway will give you URLs like:
- Backend: `https://backend-production-abc123.up.railway.app`
- Bot: `https://bot-production-def456.up.railway.app`

## 🔧 Production Configuration

### Backend Environment (.env.production)
```env
# Environment
ENVIRONMENT=production
DEBUG=False

# Supabase (same as development)
SUPABASE_URL=https://lgfwxvdbkavufbchzvuo.supabase.co
SUPABASE_KEY=your_key
SUPABASE_SERVICE_KEY=your_service_key

# Redis (Railway will provide this)
REDIS_URL=redis://default:password@redis.railway.internal:6379

# Celery (same as Redis)
CELERY_BROKER_URL=redis://default:password@redis.railway.internal:6379
CELERY_RESULT_BACKEND=redis://default:password@redis.railway.internal:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security (IMPORTANT: Generate secure keys)
SECRET_KEY=your_super_secure_secret_key_here_change_this

# M-Pesa Configuration (for Kenya)
MPESA_CONSUMER_KEY=your_production_mpesa_key
MPESA_CONSUMER_SECRET=your_production_mpesa_secret
MPESA_BUSINESS_SHORT_CODE=your_shortcode
MPESA_LIPA_NA_MPESA_PASSKEY=your_passkey
MPESA_ENVIRONMENT=production
MPESA_CALLBACK_URL=https://your-backend.railway.app/api/payment/callback/mpesa
MPESA_TIMEOUT_URL=https://your-backend.railway.app/api/payment/timeout/mpesa
```

### Bot Environment (.env.production)
```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4
WEBHOOK_URL=https://your-backend.railway.app/webhook

# Backend API Configuration
BACKEND_API_URL=https://your-backend.railway.app
BACKEND_API_KEY=your_secure_api_key_here

# Redis (Railway internal)
REDIS_URL=redis://default:password@redis.railway.internal:6379

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 🔐 Security Setup

### 1. Generate Secure API Key
```python
import secrets
api_key = secrets.token_urlsafe(32)
print(f"API Key: {api_key}")
```

### 2. Generate Secret Key
```python
import secrets
secret_key = secrets.token_urlsafe(64)
print(f"Secret Key: {secret_key}")
```

### 3. Set Telegram Webhook
```bash
curl -X POST "https://api.telegram.org/bot8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-backend.railway.app/webhook"}'
```

## 📁 Project Structure for Deployment

```
mypoolr-circles/
├── backend/
│   ├── railway.toml          # Railway backend config
│   ├── requirements.txt      # Python dependencies
│   ├── main.py              # FastAPI app
│   └── .env.production      # Production environment
├── bot/
│   ├── railway.toml          # Railway bot config
│   ├── requirements.txt      # Bot dependencies
│   ├── main.py              # Bot main file
│   └── .env.production      # Production environment
└── railway.json             # Multi-service config
```

## 🚀 Alternative: Render Deployment

### Step 1: Create Render Account
1. Go to https://render.com/
2. Connect your GitHub repository

### Step 2: Create Services
1. **Backend Web Service:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Environment: Add all backend env vars

2. **Bot Background Worker:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Environment: Add all bot env vars

3. **Redis Service:**
   - Create Redis instance
   - Use connection string in env vars

### Step 3: Configure URLs
Render gives you URLs like:
- Backend: `https://mypoolr-backend.onrender.com`
- Bot: Background worker (no URL needed)

## 🔧 Production Checklist

### Before Deployment:
- [ ] Update environment to production
- [ ] Generate secure API keys
- [ ] Configure M-Pesa production credentials
- [ ] Set up monitoring and logging
- [ ] Test all endpoints locally

### After Deployment:
- [ ] Set Telegram webhook to production URL
- [ ] Test bot functionality
- [ ] Monitor logs for errors
- [ ] Set up health checks
- [ ] Configure backup strategies

### Security Checklist:
- [ ] Use HTTPS everywhere
- [ ] Secure API keys generated
- [ ] Environment variables properly set
- [ ] Database access restricted
- [ ] Redis access secured
- [ ] Rate limiting enabled

## 📊 Monitoring Setup

### Health Checks
```python
# Add to main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

### Logging Configuration
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🚨 Troubleshooting

### Common Issues:
1. **Webhook not receiving messages:**
   - Check webhook URL is HTTPS
   - Verify webhook is set correctly
   - Check backend logs

2. **Database connection issues:**
   - Verify Supabase credentials
   - Check network connectivity
   - Review connection string

3. **Redis connection problems:**
   - Verify Redis URL format
   - Check Redis service status
   - Review connection credentials

4. **Celery worker not processing:**
   - Check Redis connection
   - Verify worker is running
   - Review task queue status

## 📞 Support Resources

- **Railway:** https://docs.railway.app/
- **Render:** https://render.com/docs
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Supabase:** https://supabase.com/docs
- **Redis Cloud:** https://redis.com/redis-enterprise-cloud/

## 🎯 Next Steps

1. Choose deployment platform (Railway recommended)
2. Generate production credentials
3. Deploy backend and bot
4. Configure webhook URL
5. Test production deployment
6. Monitor and maintain

Ready to deploy? Let's start with Railway! 🚀