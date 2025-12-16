# Imagineer Production Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Base image with system dependencies
FROM python:3.12-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Python dependencies
FROM base as builder

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Use verbose output to keep CI logs active during large wheel downloads
ENV PIP_PROGRESS_BAR=ascii
RUN pip install -v --no-cache-dir --upgrade pip && \
    pip install -v --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    pip install -v --no-cache-dir -r requirements.txt && \
    pip install -v --no-cache-dir gunicorn

# Stage 3: Production image
FROM base

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN useradd -m -u 1000 imagineer && \
    chown -R imagineer:imagineer /app

# Copy application code
COPY --chown=imagineer:imagineer . .

# Switch to non-root user
USER imagineer

# Expose port
EXPOSE 10050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:10050/api/health || exit 1

# Environment variables (override in docker-compose)
ENV FLASK_ENV=production \
    FLASK_RUN_PORT=10050 \
    PYTHONUNBUFFERED=1

# Run with gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:10050", \
     "--workers", "2", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "server.api:app"]
