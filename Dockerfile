# Backend Dockerfile for Apple Music Downloader
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for wrapper and downloader
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

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install MP4Decrypt (Bento4) - required for MV downloads
RUN wget -O bento4.zip "https://www.bento4.com/downloads/Bento4_src-1-6-0-640.zip" && \
    unzip bento4.zip && \
    cd Bento4_src-1-6-0-640 && \
    make && \
    cp bin/mp4decrypt /usr/local/bin/ && \
    chmod +x /usr/local/bin/mp4decrypt && \
    cd .. && \
    rm -rf bento4.zip Bento4_src-1-6-0-640

# Download and setup wrapper binary
RUN mkdir -p /app/wrapper && \
    cd /app/wrapper && \
    wget "https://github.com/zhaarey/wrapper/releases/download/linux.V2/wrapper.x86_64.tar.gz" && \
    tar -xzf wrapper.x86_64.tar.gz && \
    chmod +x wrapper && \
    rm wrapper.x86_64.tar.gz

# Copy the entire backend directory
COPY . .

# Create necessary directories
RUN mkdir -p logs data \
    /app/rootfs/data/data/com.apple.android.music/files

# Make startup script executable
RUN chmod +x /app/start_services.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/wrapper:${PATH}"

# Expose ports
EXPOSE 8080 10020 20020

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run both wrapper and backend services
CMD ["/app/start_services.sh"]
