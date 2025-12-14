#!/bin/bash

# Start Caddy in background
echo "Starting Caddy..."
caddy start --config /etc/caddy/Caddyfile --adapter caddyfile &

# Start Django (Daphne)
echo "Starting Daphne..."
exec daphne -b 0.0.0.0 -p 8000 sales_crm.asgi:application
