#!/bin/bash
# /entrypoint.sh - Start Caddy and Daphne concurrently and safely

set -e

# --- 1. Start Caddy in the Background ---
echo "Starting Caddy in the background..."
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &

# --- 2. Wait for Caddy Admin API (CRITICAL for Django's dynamic routing) ---
echo "Waiting for Caddy Admin API on port 2019..."
until curl -s -o /dev/null -w "%{http_code}" http://localhost:2019/config -H "Content-Type: application/json"; do
  sleep 1
done
echo "Caddy Admin API is ready."

# --- 3. Wait for Redis ---
echo "Waiting for Redis..."
until redis-cli -h redis -p 6379 -a ${REDIS_PASSWORD} ping; do
    sleep 1
done
echo "Redis is up."

# --- 4. Run Django Setup Commands (This is where the crash is!) ---
echo "Running Django migrations and collectstatic..."
# This step requires STATIC_ROOT to be correctly set in settings.py
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# --- 5. Start Daphne (Django ASGI server) in the foreground on PORT 8001 ---
echo "Starting Daphne (Django) on internal port 8001..."
exec daphne -b 0.0.0.0 -p 8001 sales_crm.asgi:application