#!/bin/bash

# Azure App Service Startup Script for GEXA

# Install the package
pip install -e ".[dev]"

# Install Playwright and browser
playwright install chromium
playwright install-deps chromium

# Start the application
exec gunicorn gexa.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
