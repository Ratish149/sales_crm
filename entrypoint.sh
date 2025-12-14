#!/bin/bash

# Start Caddy in background
echo "Starting Caddy..."
caddy start --config /etc/caddy/Caddyfile --adapter caddyfile &

# Start Django (Daphne) on internal port 8001
echo "Starting Daphne on 8001..."
exec daphne -b 0.0.0.0 -p 8001 sales_crm.asgi:application
