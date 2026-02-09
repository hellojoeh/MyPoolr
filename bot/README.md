# MyPoolr Telegram Bot

World-class Telegram bot frontend for MyPoolr Circles - a modular savings group management system.

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

**Windows:**
```cmd
cd bot
start_bot.bat
```

**Linux/Mac:**
```bash
cd bot
chmod +x start_bot.sh
./start_bot.sh
```

### Option 2: Manual Setup

1. **Install Dependencies:**
   ```bash
   cd bot
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your bot token
   ```

3. **Run Setup Check:**
   ```bash
   python setup_bot.py
   ```

4. **Start the Bot:**
   ```bash
   python run_bot.py
   ```

## 📋 Requirements

- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- Redis Server (optional, for persistent state)

## ⚙️ Configuration

Edit `.env.local` with your settings:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Optional
BACKEND_API_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 🤖 Getting a Bot Token

1. Message @BotFather on Telegram
2. Send `/newbot`
3. Choose a name and username for your bot
4. Copy the token to your `.env.local` file

## 🔧 Troubleshooting

### Common Issues

**Import Errors:**
```bash
pip install --upgrade python-telegram-bot python-dotenv pydantic httpx redis loguru
```

**Redis Connection Failed:**
- Redis is optional - the bot will use memory storage
- To install Redis: https://redis.io/download

**Bot Token Issues:**
- Make sure token is from @BotFather
- Check for extra spaces in .env.local
- Token format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### Logs

Check `bot.log` for detailed error messages.

## 🎯 Features

- **Intuitive Interface**: Beautiful inline keyboards with smooth transitions
- **State Management**: Robust conversation flows with Redis persistence
- **Multi-Country Support**: Dynamic feature toggles and localization
- **Secure Operations**: Integration with backend API for financial operations
- **Responsive Design**: Optimized button layouts for all devices

## 📁 Project Structure

```
bot/
├── run_bot.py              # Main bot runner
├── setup_bot.py            # Setup and dependency checker
├── start_bot.bat           # Windows startup script
├── start_bot.sh            # Linux/Mac startup script
├── main.py                 # Application entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── handlers/               # Message and callback handlers
│   ├── commands.py         # Command handlers (/start, /help)
│   ├── callbacks.py        # Button callback handlers
│   ├── conversations.py    # Conversation flow handlers
│   ├── mypoolr_creation.py # MyPoolr creation workflow
│   ├── member_management.py # Member management interface
│   ├── contribution_confirmation.py # Contribution flows
│   └── tier_upgrade.py     # Tier upgrade interface
└── utils/                  # Utility modules
    ├── button_manager.py   # World-class button system
    ├── state_manager.py    # Conversation state management
    ├── backend_client.py   # Backend API client
    ├── formatters.py       # Message formatting utilities
    ├── ui_components.py    # UI components
    └── feedback_system.py  # Visual feedback system
```

## 🔄 Development Status

- ✅ Project structure and dependencies
- ✅ Button management system
- ✅ Core commands and navigation
- ✅ MyPoolr creation workflow
- ✅ Member management interface
- ✅ Contribution confirmation interface
- ✅ Tier upgrade interface

## 🤝 Support

For issues or questions:
1. Check the logs in `bot.log`
2. Run `python setup_bot.py` to verify setup
3. Ensure your bot token is correct
4. Check that all dependencies are installed

## 📄 License

This project is part of the MyPoolr Circles system.