# Webshop screenshot collector — long-running container. See DEPLOY.txt.
# Build:  docker build -t screenshot-bot .
FROM python:3.11-slim

# Chromium + driver and the shared libs headless Chrome needs.
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# requirements first so this pip layer is cached and only rebuilds when
# requirements.txt itself changes, not on every code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime code only. collect.py is the long-running scheduler (container main
# process); it imports run_cycle from screenshot.py.
COPY screenshot.py collect.py ./

CMD ["python", "collect.py"]
