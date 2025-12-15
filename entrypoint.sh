#!/bin/bash
# /entrypoint.sh - Start Caddy and Daphne concurrently and safely

# Exit immediately if a command exits with a non-zero status.
set -e

# --- 1. Start Caddy in the Background (Use 'caddy run' for foreground management) ---
# Running Caddy with 'caddy run' in the background (&) is more common in Docker.
echo "Starting Caddy in the background..."
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &

# --- 2. Wait for Caddy Admin API (CRITICAL for Django's configure_caddy) ---
# The Caddy API runs on 127.0.0.1:2019 inside the container.
echo "Waiting for Caddy Admin API on port 2019..."
until curl -s -o /dev/null -w "%{http_code}" http://localhost:2019/config -H "Content-Type: application/json"; do
  sleep 1
done
echo "Caddy Admin API is ready."

# --- 3. Wait for Redis (Good practice from your original compose file) ---
echo "Waiting for Redis..."
# Use REDIS_PASSWORD from environment variables in docker-compose.yml
until redis-cli -h redis -p 6379 -a wzjp4NUl+I8QthONqJKwnRL8cNFusnS0DtVG6n/hfug= ping; do
    sleep 1
done

# --- 4. Run Django Setup Commands ---
echo "Running Django migrations and collectstatic..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# --- 5. Start Daphne (Django ASGI server) in the foreground ---
# This command replaces the current shell, making it the main process.
# Caddy continues to run in the background.
echo "Starting Daphne (Django) on internal port 8001..."
exec daphne -b 0.0.0.0 -p 8001 sales_crm.asgi:application