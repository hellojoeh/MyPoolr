/**
 * MyPoolr Telegram Bot - Cloudflare Workers Implementation
 * Handles Telegram webhook requests and processes bot commands
 */

// Simple Telegram Bot API wrapper for Cloudflare Workers
class TelegramBot {
  constructor(token) {
    this.token = token;
    this.apiUrl = `https://api.telegram.org/bot${token}`;
  }

  async sendMessage(chatId, text, options = {}) {
    const payload = {
      chat_id: chatId,
      text: text,
      ...options
    };

    const response = await fetch(`${this.apiUrl}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return response.json();
  }

  async answerCallbackQuery(callbackQueryId, options = {}) {
    const payload = {
      callback_query_id: callbackQueryId,
      ...options
    };

    const response = await fetch(`${this.apiUrl}/answerCallbackQuery`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return response.json();
  }
}

// Backend API client
class BackendClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.apiKey}`,
      ...options.headers
    };

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      throw new Error(`Backend request failed: ${response.status}`);
    }

    return response.json();
  }

  async healthCheck() {
    return this.request('/health');
  }

  async createMypoolr(data) {
    return this.request('/api/mypoolr', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async getMypoolr(mypoolrId) {
    return this.request(`/api/mypoolr/${mypoolrId}`);
  }

  async joinMypoolr(mypoolrId, memberData) {
    return this.request(`/api/mypoolr/${mypoolrId}/join`, {
      method: 'POST',
      body: JSON.stringify(memberData)
    });
  }
}

// Command handlers
const handlers = {
  '/start': async (bot, message, backend) => {
    const welcomeText = `
🎉 Welcome to MyPoolr Circles!

MyPoolr helps you manage rotating savings groups (chamas) with your friends and family.

Available commands:
/create - Create a new MyPoolr circle
/join - Join an existing circle
/status - Check your circle status
/help - Show this help message

Let's get started! 🚀
    `;

    await bot.sendMessage(message.chat.id, welcomeText);
  },

  '/create': async (bot, message, backend) => {
    // For simplicity, this is a basic implementation
    // In production, you'd want to implement a conversation flow
    await bot.sendMessage(
      message.chat.id,
      "To create a MyPoolr circle, please provide:\n\n" +
      "1. Circle name\n" +
      "2. Contribution amount\n" +
      "3. Number of members\n" +
      "4. Rotation frequency\n\n" +
      "Use format: /create <name> <amount> <members> <frequency>"
    );
  },

  '/join': async (bot, message, backend) => {
    await bot.sendMessage(
      message.chat.id,
      "To join a MyPoolr circle, use:\n/join <invitation_code>"
    );
  },

  '/status': async (bot, message, backend) => {
    try {
      // This would fetch user's circles from backend
      await bot.sendMessage(
        message.chat.id,
        "📊 Your MyPoolr Status:\n\n" +
        "Active Circles: 0\n" +
        "Total Contributions: $0\n" +
        "Next Payout: Not scheduled\n\n" +
        "Use /create to start your first circle!"
      );
    } catch (error) {
      await bot.sendMessage(
        message.chat.id,
        "❌ Unable to fetch status. Please try again later."
      );
    }
  },

  '/help': async (bot, message, backend) => {
    const helpText = `
🤖 MyPoolr Bot Commands:

/start - Welcome message and overview
/create - Create a new savings circle
/join - Join an existing circle
/status - Check your circles and contributions
/help - Show this help message

💡 Tips:
• Invite friends using invitation codes
• Set up automatic contributions
• Track your savings progress
• Get notified about payouts

Need support? Contact our team! 📞
    `;

    await bot.sendMessage(message.chat.id, helpText);
  }
};

// Main webhook handler
export default {
  async fetch(request, env, ctx) {
    // Only handle POST requests to webhook
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      // Parse Telegram update
      const update = await request.json();
      
      // Initialize bot and backend client
      const bot = new TelegramBot(env.TELEGRAM_BOT_TOKEN);
      const backend = new BackendClient(env.BACKEND_API_URL, env.BACKEND_API_KEY);

      // Handle message
      if (update.message) {
        const message = update.message;
        const text = message.text || '';
        
        // Extract command
        const command = text.split(' ')[0];
        
        // Handle known commands
        if (handlers[command]) {
          await handlers[command](bot, message, backend);
        } else if (text.startsWith('/')) {
          // Unknown command
          await bot.sendMessage(
            message.chat.id,
            "❓ Unknown command. Use /help to see available commands."
          );
        } else {
          // Regular message - could implement conversation flow here
          await bot.sendMessage(
            message.chat.id,
            "👋 Hi! Use /help to see what I can do for you."
          );
        }
      }

      // Handle callback queries (inline keyboard buttons)
      if (update.callback_query) {
        const callbackQuery = update.callback_query;
        
        // Acknowledge the callback
        await bot.answerCallbackQuery(callbackQuery.id);
        
        // Handle callback data
        const data = callbackQuery.data;
        await bot.sendMessage(
          callbackQuery.message.chat.id,
          `You clicked: ${data}`
        );
      }

      return new Response('OK', { status: 200 });
      
    } catch (error) {
      console.error('Webhook error:', error);
      return new Response('Internal Server Error', { status: 500 });
    }
  }
};