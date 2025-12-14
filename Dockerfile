# Use Python slim image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including git and Caddy)
RUN apt-get update && \
    apt-get install -y git build-essential nodejs npm redis-tools curl debian-keyring debian-archive-keyring apt-transport-https && \
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && \
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list && \
    apt-get update && \
    apt-get install -y caddy && \
    rm -rf /var/lib/apt/lists/*

# Copy project code
COPY . .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy entrypoint and Caddyfile
COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports (8000=Caddy Gateway, 2019=Caddy API)
# Django runs internally on 8001
EXPOSE 8000
EXPOSE 2019

# Run Entrypoint
CMD ["/entrypoint.sh"]
