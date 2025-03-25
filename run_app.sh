#!/bin/bash

# Exit script if any command fails
set -e

echo "=== Starting RYZE.ai Application ==="

# Check if screen is installed
if ! command -v screen &> /dev/null; then
    echo "Screen is not installed. Installing..."
    sudo apt-get update && sudo apt-get install -y screen
fi

# Start backend server in a screen session
echo "Starting backend server..."
screen -dmS ryze-backend bash -c "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

# Start frontend development server in a screen session
echo "Starting frontend development server..."
screen -dmS ryze-frontend bash -c "cd frontend && npm start"

echo "=== RYZE.ai application started! ==="
echo "Backend running at: http://localhost:8000"
echo "Frontend running at: http://localhost:3000"
echo ""
echo "To view running screens:"
echo "  - List all screens: screen -ls"
echo "  - Attach to backend: screen -r ryze-backend"
echo "  - Attach to frontend: screen -r ryze-frontend"
echo "  - Detach from screen: Press Ctrl+A, then D"