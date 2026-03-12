# Use Python 3.12 slim image
FROM python:3.12-slim

# Build argument to control dev dependencies installation
ARG INSTALL_DEV=false

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies conditionally
# Production: only runtime deps
# Development: runtime + dev deps
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        echo "Installing with dev dependencies..." && \
        uv sync --frozen --all-extras; \
    else \
        echo "Installing runtime dependencies only..." && \
        uv sync --frozen; \
    fi

# Copy application code
COPY app.py main.py ./
COPY src/ ./src/

# Expose port for API
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uv", "run", "uvicorn", "app:combined_app", "--host", "0.0.0.0", "--port", "8000"]
