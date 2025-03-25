#!/bin/bash

# Exit script if any command fails
set -e

echo "=== Running database migrations for RYZE.ai ==="

# Check if alembic is installed
if ! command -v alembic &> /dev/null; then
    echo "Alembic is not installed. Please run setup_alembic.sh first."
    exit 1
fi

# Run the migrations
alembic upgrade head

echo "=== Migrations completed successfully! ==="