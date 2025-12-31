# GEXA - Web Search API for AI Agents
# Single-stage Docker build for Azure Container Apps

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build dependencies
    build-essential \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    # Additional utilities
    wget \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY dashboard/ ./dashboard/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Install Playwright browsers
RUN playwright install chromium

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "gexa.main:app", "--host", "0.0.0.0", "--port", "8000"]
