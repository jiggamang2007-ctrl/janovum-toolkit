# Janovum Platform — Production Dockerfile
# Build:  docker build -t janovum .
# Run:    docker run -p 5050:5050 janovum

FROM python:3.12-slim

# Prevent interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# Install Chrome + dependencies for Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg2 \
    curl \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy platform source code
COPY . .

# Create data directories
RUN mkdir -p data/audio data/bots data/conversations data/costs \
    data/traces data/approvals data/auth data/sandbox \
    logs agent_screenshots

# Expose the server port
EXPOSE 5050

# Environment defaults
ENV SERVER_PORT=5050
ENV DEBUG=false
ENV PYTHONUNBUFFERED=1

# Run the main server
CMD ["python", "server_v5.py"]
