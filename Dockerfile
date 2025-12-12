# Use Python slim image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including git)
RUN apt-get update && \
    apt-get install -y git build-essential nodejs npm redis-tools && \
    rm -rf /var/lib/apt/lists/*

# Copy project code
COPY . .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Run Daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "sales_crm.asgi:application"]
