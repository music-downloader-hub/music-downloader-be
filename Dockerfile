# Backend Dockerfile for Apple Music Downloader
FROM ubuntu:latest

# Set working directory
WORKDIR /app

# Install system dependencies for downloader
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    tar \
    gzip \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    # For MP4Box (GPAC)
    libgpac-dev \
    gpac \
    # For MP4Decrypt (Bento4)
    libssl-dev \
    libcrypto++-dev \
    # For Go runtime (needed for downloader)
    golang-go \
    # For FFmpeg (if needed for audio processing)
    ffmpeg \
    # For Node.js (if needed for some tools)
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment
RUN python3 -m venv /app/.venv

# Activate virtual environment and install Python dependencies
RUN /app/.venv/bin/pip install --upgrade pip && \
    /app/.venv/bin/pip install -r requirements.txt

# Copy the entire backend directory
COPY . .

# Install MP4Decrypt (Bento4) - required for MV downloads
RUN wget -O bento4.zip "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip" && \
    unzip bento4.zip && \
    cp Bento4-SDK-1-6-0-641.x86_64-unknown-linux/bin/mp4decrypt /usr/local/bin/ && \
    chmod +x /usr/local/bin/mp4decrypt && \
    rm -rf bento4.zip Bento4-SDK-1-6-0-641.x86_64-unknown-linux


# Copy the entire backend directory
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Make startup script executable
RUN chmod +x /app/start_services.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run backend service
CMD ["/app/start_services.sh"]
