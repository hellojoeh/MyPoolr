# Deploy MyPoolr Bot to Railway

## Prerequisites
- Railway account (sign up at https://railway.app)
- GitHub account (to connect your repo)
- $5 free credit per month included

## Step 1: Stop Cloudflare Worker

### Option A: Delete the Worker (Recommended)
1. Go to https://dash.cloudflare.com
2. Navigate to **Workers & Pages**
3. Find **mypoolr-bot** worker
4. Click on it, then go to **Settings**
5. Scroll down and click **Delete** button
6. Confirm deletion

### Option B: Disable the Worker (Keep for backup)
1. Go to https://dash.cloudflare.com
2. Navigate to **Workers & Pages**
3. Find **mypoolr-bot** worker
4. Click on it, then go to **Settings**
5. Under **Triggers**, remove all routes/triggers
6. This stops it from receiving webhook requests

## Step 2: Delete Telegram Webhook

Run this command to remove the webhook (so bot can use polling mode):

```bash
curl -X POST "https://api.telegram.org/bot8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4/deleteWebhook?drop_pending_updates=true"
```

Or use this Python script:

```python
import requests

BOT_TOKEN = "8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4"
url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"

response = requests.post(url, json={"drop_pending_updates": True})
print(response.json())
```

Expected response:
```json
{"ok": true, "result": true, "description": "Webhook was deleted"}
```

## Step 3: Deploy to Railway

### 3.1 Create Railway Project
1. Go to https://railway.app
2. Click **Start a New Project**
3. Select **Deploy from GitHub repo**
4. Authorize Railway to access your GitHub
5. Select your **mypoolr** repository
6. Railway will detect it's a Python project

### 3.2 Configure Build Settings
1. In Railway dashboard, go to your project
2. Click on **Settings** tab
3. Set **Root Directory** to: `bot`
4. Set **Start Command** to: `python main.py`
5. Click **Save**

### 3.3 Add Environment Variables
1. Go to **Variables** tab
2. Click **+ New Variable** and add each one:

```
TELEGRAM_BOT_TOKEN=8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4
BACKEND_API_URL=https://mypoolr-backend.onrender.com
BACKEND_API_KEY=rnd_eGhD9lbNHdkSY0r922jaMpLcZctq
REDIS_URL=redis://default:dffmE5aUSNeNhkx0dV0LbryVJAA1ujRe@redis-10445.crce218.eu-central-1-1.ec2.cloud.redislabs.com:10445
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=False
```

**IMPORTANT:** Do NOT set `WEBHOOK_URL` - leave it empty for polling mode

### 3.4 Deploy
1. Click **Deploy** button
2. Railway will:
   - Install Python 3.10
   - Install dependencies from `requirements.txt`
   - Start the bot with `python main.py`
3. Check **Deployments** tab for build logs
4. Once deployed, check **Logs** tab to verify bot is running

## Step 4: Verify Bot is Working

1. Open Telegram and find your bot
2. Send `/start` command
3. You should see the welcome message with inline buttons
4. Test creating a group, viewing groups, etc.

## Railway Features

✅ **$5 Free Credit/Month** - Enough for small bots
✅ **Automatic Restarts** - If bot crashes, Railway restarts it
✅ **Easy Logs** - View real-time logs in dashboard
✅ **GitHub Integration** - Auto-deploy on git push
✅ **Environment Variables** - Secure secret management

## Monitoring

### Check Bot Status
- Railway Dashboard → Your Project → **Logs** tab
- Look for: "Starting MyPoolr Telegram Bot..."
- Look for: "Backend connection verified"

### Check Telegram Connection
```bash
curl "https://api.telegram.org/bot8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4/getMe"
```

### Check Webhook Status (Should be empty)
```bash
curl "https://api.telegram.org/bot8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4/getWebhookInfo"
```

Expected response:
```json
{
  "ok": true,
  "result": {
    "url": "",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

## Troubleshooting

### Bot not responding
1. Check Railway logs for errors
2. Verify webhook is deleted: `curl "https://api.telegram.org/bot.../getWebhookInfo"`
3. Check environment variables are set correctly
4. Restart deployment in Railway dashboard

### "Backend connection test failed"
- Check `BACKEND_API_URL` is correct
- Check `BACKEND_API_KEY` is correct
- Verify backend is running: https://mypoolr-backend.onrender.com/health

### Railway build fails
- Check `requirements.txt` is in `bot/` folder
- Check Python version in `runtime.txt` is supported
- Check Railway logs for specific error

## Cost Estimate

Railway Free Tier:
- $5 credit per month
- Bot uses ~$0.10-0.50/day depending on usage
- Should cover 10-50 days of operation
- After free credit, pay-as-you-go pricing

## Alternative: Keep Cloudflare + Add Polling Fallback

If you want to keep Cloudflare as backup:
1. Don't delete Cloudflare worker
2. Deploy to Railway with polling mode
3. If Railway goes down, quickly set webhook back to Cloudflare
4. This gives you redundancy

## Next Steps

After successful deployment:
1. Test all bot features thoroughly
2. Monitor Railway usage in dashboard
3. Set up alerts for when credit runs low
4. Consider upgrading if you need more resources
