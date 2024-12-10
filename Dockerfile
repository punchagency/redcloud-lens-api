# Stage 1: Base and Dependencies
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements.prod.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.prod.txt

# Stage 2: Final Image
FROM python:3.11-slim

WORKDIR /app

# Copy only the necessary files
COPY --from=base /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=base /usr/local/bin /usr/local/bin
COPY . .

# Expose application port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Command to run the app with Gunicorn
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
