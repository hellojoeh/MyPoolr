#!/bin/bash

echo "🤖 MyPoolr Telegram Bot Setup and Start"
echo

# Change to bot directory
cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python not found! Please install Python 3.8+"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "✅ Using Python: $PYTHON_CMD"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🔧 Virtual environment not found. Creating one..."
    $PYTHON_CMD create_env.py
    if [ $? -ne 0 ]; then
        echo "❌ Environment setup failed!"
        exit 1
    fi
    echo
fi

# Activate virtual environment and run bot
echo "🚀 Starting bot in virtual environment..."
source venv/bin/activate && python run_bot.py