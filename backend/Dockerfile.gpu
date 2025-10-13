# Production Dockerfile for Whisper App Backend with GPU support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Proxy settings for build
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Create non-root user
RUN groupadd -r whisper && \
    useradd -r -g whisper -u 1000 whisper

# Create working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA 11.8 support
RUN pip install --no-cache-dir \
    torch==2.1.0+cu118 \
    torchaudio==2.1.0+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Copy application code
COPY --chown=whisper:whisper . .

# Create data directories
RUN mkdir -p /data/uploads /data/results /data/temp /var/log/whisper && \
    chown -R whisper:whisper /data /var/log/whisper

# Switch to non-root user
USER whisper

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn (production mode with multiple workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
