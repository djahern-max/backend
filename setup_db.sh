#!/bin/bash

# Exit script if any command fails
set -e

echo "=== Setting up PostgreSQL database for RYZE.ai ==="

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed. Please install it using: brew install postgresql"
    exit 1
fi

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading configuration from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo ".env file not found. Creating one with default values..."
    # Create default .env file
    cat > .env << EOF
DB_NAME=ryze_db
DB_USER=ryze_user
DB_PASSWORD=ryze_password
DB_HOST=localhost
DATABASE_URL=postgresql://\${DB_USER}:\${DB_PASSWORD}@\${DB_HOST}/\${DB_NAME}
EOF
    export $(grep -v '^#' .env | xargs)
    echo "Created .env file with default values."
fi

# Database configuration from environment variables
DB_NAME=${DB_NAME:-ryze_db}
DB_USER=${DB_USER:-ryze_user}
DB_PASSWORD=${DB_PASSWORD:-ryze_password}
DB_HOST=${DB_HOST:-localhost}

# Create database user
echo "Creating database user $DB_USER..."
createuser $DB_USER 2>/dev/null || echo "User $DB_USER already exists"

# Set user password
psql postgres -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || echo "Failed to set password"

# Create database
echo "Creating database $DB_NAME..."
createdb -O $DB_USER $DB_NAME 2>/dev/null || echo "Database $DB_NAME already exists"

# Update DATABASE_URL in .env if needed
grep -q "^DATABASE_URL=" .env && \
  sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST/$DB_NAME|" .env || \
  echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST/$DB_NAME" >> .env

echo "=== Database setup complete! ==="
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Password: $DB_PASSWORD"
echo "Connection string: postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST/$DB_NAME"