# Big Three Anime NLP Pipeline - Dockerfile
# Production-ready container for extraordinary analysis

FROM python:3.9-slim

# Set metadata
LABEL maintainer="Big Three Anime NLP Team"
LABEL description="Containerized pipeline for anime review sentiment and topic analysis"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome and ChromeDriver
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` \
    && wget -q -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config.yml .
COPY Makefile .

# Create necessary directories
RUN mkdir -p data/raw data/processed data/analysis data/exports logs reports

# Set Chrome options for headless operation
ENV CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --remote-debugging-port=9222"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pandas; print('Health check passed')" || exit 1

# Default command
CMD ["python", "-m", "src.pipeline", "--help"]

# Expose port for potential web interface
EXPOSE 8080

# Volume for data persistence
VOLUME ["/app/data"]

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Labels for better image management
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.version=$VERSION
LABEL org.label-schema.name="Big Three Anime NLP"
LABEL org.label-schema.description="Containerized pipeline for anime review analysis"
LABEL org.label-schema.vendor="Big Three Anime NLP Team"
LABEL org.label-schema.schema-version="1.0" 