# Backend Dockerfile for DTaaS
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Microsoft ODBC Driver for SQL Server
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    unixodbc-dev \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Initialize database on first run
RUN python -c "from database import init_db; init_db()" || true

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "main.py"]

