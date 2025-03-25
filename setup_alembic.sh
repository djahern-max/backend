#!/bin/bash

# Exit script if any command fails
set -e

echo "=== Setting up Alembic for database migrations ==="

# Install required packages
echo "Installing required packages..."
pip install alembic sqlalchemy psycopg2-binary python-dotenv

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo ".env file not found. Please run setup_db.sh first."
    exit 1
fi

# Create directory structure if it doesn't exist
mkdir -p alembic/versions

# Create alembic.ini file
echo "Creating alembic.ini..."
cat > alembic.ini << EOF
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = ${DATABASE_URL}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

# Create alembic/env.py
echo "Creating alembic/env.py..."
cat > alembic/env.py << 'EOF'
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# This is the Alembic Config object
config = context.config

# Override sqlalchemy.url with environment variable
if os.getenv('DATABASE_URL'):
    config.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL'))

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
from app.models.database import Base
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF

echo "=== Alembic setup complete! ==="
echo "You can now run database migrations using:"
echo "./migrate_db.sh"