# MyPoolr Telegram Bot - Cloudflare Workers

This is a Cloudflare Workers implementation of the MyPoolr Telegram bot, providing a serverless alternative to running the bot as a background worker.

## Setup

### 1. Install Dependencies

```bash
cd cloudflare-worker
npm install
```

### 2. Configure Wrangler

Make sure you have Wrangler CLI installed:

```bash
npm install -g wrangler
wrangler login
```

### 3. Set Environment Variables

Set your secrets using Wrangler:

```bash
# Telegram Bot Token
wrangler secret put TELEGRAM_BOT_TOKEN

# Backend API Configuration
wrangler secret put BACKEND_API_URL
wrangler secret put BACKEND_API_KEY
```

### 4. Create KV Namespace (Optional)

For storing bot state:

```bash
wrangler kv:namespace create "BOT_STATE"
wrangler kv:namespace create "BOT_STATE" --preview
```

Update the namespace IDs in `wrangler.toml`.

### 5. Deploy

```bash
# Deploy to development
npm run dev

# Deploy to production
npm run deploy:prod
```

## Webhook Setup

After deployment, set up the Telegram webhook:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mypoolr-bot-prod.<your-subdomain>.workers.dev"}'
```

## Features

- ✅ Serverless execution (no always-on server needed)
- ✅ Automatic scaling
- ✅ Global edge deployment
- ✅ Built-in DDoS protection
- ✅ Free tier available (100,000 requests/day)
- ✅ Low latency responses

## Cost Comparison

**Render Worker Service:**
- $7/month minimum
- Always running (even when idle)
- Single region deployment

**Cloudflare Workers:**
- Free tier: 100,000 requests/day
- Paid: $5/month for 10M requests
- Pay-per-use (no idle costs)
- Global edge deployment

## Architecture

```
Telegram → Cloudflare Workers → Your Backend API (Render)
                ↓
            KV Storage (optional)
```

## Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `BACKEND_API_URL`: URL of your backend API (e.g., https://mypoolr-backend.onrender.com)
- `BACKEND_API_KEY`: API key for backend authentication

## Limitations

- 10ms CPU time limit per request (usually sufficient for bot responses)
- 128MB memory limit
- No persistent connections (stateless)
- Cold start latency (minimal with Workers)

## Migration from Python Bot

The Cloudflare Workers implementation provides the same core functionality as your Python bot but with these advantages:

1. **Cost Effective**: No monthly server costs for low-traffic bots
2. **Scalable**: Automatically handles traffic spikes
3. **Reliable**: Built-in redundancy and failover
4. **Fast**: Global edge deployment reduces latency

The JavaScript implementation handles the same Telegram webhook events and communicates with your existing backend API.