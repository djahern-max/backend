#!/bin/bash

# Exit script if any command fails
set -e

echo "=== Installing requirements for RYZE.ai ==="

# Install backend requirements
echo "Installing backend requirements..."
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic python-dateutil

# Check if npm is installed for frontend dependencies
if command -v npm &> /dev/null; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
else
    echo "npm not found. Skipping frontend dependencies installation."
    echo "Please install npm and run 'cd frontend && npm install' manually."
fi

echo "=== Requirements installation complete! ==="