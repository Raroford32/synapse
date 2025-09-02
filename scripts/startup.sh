#!/bin/bash
# Startup script for Synapse

set -e

echo "🚀 Starting Synapse initialization..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "${POSTGRES_HOST:-postgres}" -U "${POSTGRES_USER:-synapse}" -d "${POSTGRES_DB:-synapse_db}" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" ping 2>/dev/null; do
  echo "Redis is unavailable - sleeping"
  sleep 2
done
echo "✅ Redis is ready!"

# Initialize database
echo "Initializing database..."
python scripts/init_db.py

# Run migrations
echo "Running database migrations..."
alembic upgrade head || echo "No migrations to run"

echo "✅ Initialization complete!"

# Start the application
echo "Starting Synapse application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1