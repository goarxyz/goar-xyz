FROM python:3.12-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GOAR_HOME=/data/goar \
    GOAR_WORKSPACE=/workspace \
    GOAR_HOST=0.0.0.0 \
    GOAR_PORT=8080 \
    GOAR_AUTO_INSTALL_DESKTOP=0 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HOME=/tmp/goar-home

# The image deliberately contains every desktop dependency required at runtime.
# GOAR never invokes a package manager after the container has started.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        dumb-init \
        gosu \
        chromium \
        tigervnc-standalone-server \
        websockify \
        novnc \
        fluxbox \
        xterm \
        fonts-liberation \
        fonts-noto-color-emoji \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libu2f-udev \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxshmfence1 \
        libxtst6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/goar

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . ./

RUN groupadd --gid 10001 goar \
    && useradd --uid 10001 --gid goar --create-home --home-dir /home/goar --shell /usr/sbin/nologin goar \
    && install -d -o goar -g goar -m 0750 /data/goar /workspace /workspace/downloads /workspace/uploads /ms-playwright \
    && install -m 0755 docker-entrypoint.sh /usr/local/bin/goar-entrypoint \
    && chown -R goar:goar /opt/goar /home/goar /data/goar /workspace /ms-playwright

# The entrypoint starts as root only long enough to initialize private state,
# then uses gosu to run the service as the configured unprivileged UID and GID.
USER root

EXPOSE 8080
VOLUME ["/data/goar", "/workspace"]

HEALTHCHECK --interval=30s --timeout=8s --start-period=45s --retries=3 \
    CMD python -c "import os, urllib.request; request = urllib.request.Request('http://127.0.0.1:8080/health'); key = os.getenv('GOAR_REQUIRE_KEY', ''); key and request.add_header('X-API-Key', key); urllib.request.urlopen(request, timeout=5).read()" || exit 1

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/usr/local/bin/goar-entrypoint"]
CMD ["gunicorn", "--chdir", "/opt/goar", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "--graceful-timeout", "30", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "wsgi:application"]
