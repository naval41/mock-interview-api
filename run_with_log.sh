#!/bin/bash

# Mock Interview API - Start with logging
# Kills existing processes on port 8000 and starts server with log output

cd "$(dirname "$0")"

echo "🎯 Mock Interview API - Starting with log output"
echo "=============================================="

# Set log file with timestamp
LOG_FILE="server_$(date +%Y%m%d_%H%M%S).log"

echo "📝 Log file: $LOG_FILE"
echo "🔍 Checking for existing processes on port 8000..."

# Kill any existing processes on port 8000
PIDS=$(lsof -t -i:8000 2>/dev/null)
if [ ! -z "$PIDS" ]; then
    echo "🛑 Killing existing processes: $PIDS"
    kill -9 $PIDS
    sleep 1
else
    echo "✅ No existing processes found on port 8000"
fi

echo "🚀 Starting server with logging..."
echo "📍 Server URL: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "📝 Logs will be written to: $LOG_FILE"
echo "=============================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Activate virtual environment
source venv/bin/activate

# Start the server with logging
ENV=local python3.12 -m uvicorn app.main:app --reload --log-level trace --access-log --use-colors --port 8000 2>&1 | tee "$LOG_FILE"
