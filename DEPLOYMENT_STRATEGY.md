# MyPoolr Circles - Deployment Strategy

## 🏗️ Current Architecture

Your MyPoolr system uses a **microservices architecture**:

```
┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   FastAPI       │
│   (bot/)        │◄──►│   Backend       │
│                 │    │   (backend/)    │
│   - Polling     │    │   - API         │
│   - User UI     │    │   - Celery      │
│   - Commands    │    │   - Database    │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┘
                   │
            ┌─────────────────┐
            │   Redis Cloud   │
            │   + Supabase    │
            └─────────────────┘
```

## 🚀 Deployment Requirements

### Deploy BOTH Services:

#### 1. Backend Service (Web Service)
- **Directory**: `backend/`
- **Type**: Web service with public URL
- **Port**: 8000
- **Health Check**: `/health`
- **Scaling**: Can handle multiple instances

#### 2. Bot Service (Background Worker)
- **Directory**: `bot/`
- **Type**: Background worker (no public URL)
- **Scaling**: Single instance recommended
- **Connects to**: Backend API + Telegram

## 📦 Platform-Specific Deployment

### Railway Deployment

```bash
# 1. Deploy Backend (Web Service)
cd backend
railway up --service backend

# 2. Deploy Bot (Background Worker)  
cd ../bot
railway up --service bot
```

### Render Deployment

1. **Backend**: Create "Web Service"
   - Build: `pip install -r requirements.txt`
   - Start: `python main.py`
   - Port: 8000

2. **Bot**: Create "Background Worker"
   - Build: `pip install -r requirements.txt`
   - Start: `python main.py`

### Manual Deployment Steps

1. **Create two separate services/containers**
2. **Backend service**:
   - Expose port 8000
   - Set all backend environment variables
   - Enable health checks on `/health`

3. **Bot service**:
   - No port exposure needed
   - Set bot environment variables
   - Include backend URL for API calls

## 🔧 Environment Configuration

### Backend Service Environment
```env
# All variables from backend/.env.local
SUPABASE_URL=...
REDIS_URL=...
CELERY_BROKER_URL=...
API_HOST=0.0.0.0
API_PORT=8000
BACKEND_API_KEY=...
SECRET_KEY=...
```

### Bot Service Environment  
```env
# All variables from bot/.env.local
TELEGRAM_BOT_TOKEN=...
BACKEND_API_URL=https://your-backend-url
BACKEND_API_KEY=...
REDIS_URL=...
```

## 🎯 Why Both Services?

### Backend Service Provides:
- ✅ MyPoolr management API
- ✅ Member registration endpoints
- ✅ Transaction processing
- ✅ Tier management
- ✅ Payment integration
- ✅ Background task processing (Celery)

### Bot Service Provides:
- ✅ Telegram user interface
- ✅ Command handling (/start, /help, etc.)
- ✅ Interactive buttons and menus
- ✅ User conversation flows
- ✅ Real-time message processing

### They Work Together:
- Bot receives user messages from Telegram
- Bot calls Backend API for business logic
- Backend processes requests and updates database
- Backend sends responses back to Bot
- Bot sends formatted messages to users

## 🚀 Deployment Commands

### Option 1: Automated (Railway)
```bash
python deploy_production.py
```

### Option 2: Manual Railway
```bash
# Login and setup
railway login
railway init

# Add Redis
railway add redis

# Deploy backend
cd backend
railway up

# Deploy bot  
cd ../bot
railway up
```

### Option 3: Other Platforms
Follow platform-specific guides for deploying:
1. One web service (backend)
2. One background worker (bot)
3. One Redis instance (shared)

## 📊 Post-Deployment Checklist

- [ ] Backend service running and accessible
- [ ] Bot service running (check logs)
- [ ] Redis connection working for both services
- [ ] Backend API responding to health checks
- [ ] Bot can communicate with backend API
- [ ] Telegram bot responding to messages
- [ ] Celery workers processing tasks
- [ ] Database connections stable

## 🔍 Testing Deployment

1. **Test Backend**:
   ```bash
   curl https://your-backend-url/health
   ```

2. **Test Bot**:
   - Send `/start` to your Telegram bot
   - Check bot service logs for activity

3. **Test Integration**:
   - Try creating a MyPoolr through the bot
   - Verify data appears in Supabase
   - Check Celery task processing

## 💡 Pro Tips

- **Start with backend deployment first**
- **Get backend URL before deploying bot**
- **Update bot environment with backend URL**
- **Monitor logs during initial deployment**
- **Test each service independently**
- **Use health checks for monitoring**

Ready to deploy both services? 🚀