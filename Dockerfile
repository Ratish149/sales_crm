# Install dependencies
FROM python:3.11-slim

WORKDIR /app

# Copy code
COPY . .

# Install pip packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Default run
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
