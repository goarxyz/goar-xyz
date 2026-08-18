#!/usr/bin/env bash
# Traditional Linux server installer for GOAR.
# Run as root.  For Replit deployments use artifacts/api-server/build-goar.sh instead.
set -euo pipefail

PREFIX=${GOAR_PREFIX:-/opt/goar}
STATE_DIR=${GOAR_STATE_DIR:-/var/lib/goar}
CONFIG_DIR=${GOAR_CONFIG_DIR:-/etc/goar}
SERVICE_USER=${GOAR_SERVICE_USER:-goar}

install_system_deps() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
      xvfb x11vnc tigervnc-standalone-server novnc websockify fluxbox xterm \
      libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      libgdk-pixbuf-2.0-0 libgtk-3-0 \
      libcups2 libdbus-1-3 \
      libasound2 \
      libgl1-mesa-glx libgl1 \
      libnspr4 libnss3 \
      libx11-6 libxcomposite1 libxcursor1 libxdamage1 \
      libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 \
      libxtst6 libxcb1 \
      fonts-liberation libharfbuzz0b libfreetype6 libfontconfig1
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y \
      xorg-x11-server-Xvfb x11vnc tigervnc-server novnc websockify fluxbox xterm \
      atk at-spi2-atk at-spi2-core cairo pango gdk-pixbuf2 gtk3 \
      cups-libs dbus-libs alsa-lib mesa-libGL \
      nspr nss \
      libX11 libXcomposite libXcursor libXdamage \
      libXext libXfixes libXi libXrandr libXrender \
      libXtst libxcb harfbuzz freetype fontconfig
  elif command -v apk >/dev/null 2>&1; then
    apk add --no-cache \
      xvfb x11vnc tigervnc novnc websockify fluxbox xterm \
      atk at-spi2-atk at-spi2-core cairo pango gdk-pixbuf gtk+3.0 \
      cups-libs dbus-libs alsa-lib mesa-gl \
      nss libx11 libxcomposite libxcursor libxdamage \
      libxext libxfixes libxi libxrandr libxrender \
      libxtst libxcb harfbuzz freetype fontconfig
  else
    echo "WARNING: No supported package manager found. Playwright --with-deps will attempt its own install." >&2
  fi
}

if [ "$(id -u)" -ne 0 ]; then
  echo "Run install.sh as root or with sudo." >&2
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$STATE_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -o "$SERVICE_USER" -g "$SERVICE_USER" \
  "$PREFIX" "$STATE_DIR" "$STATE_DIR/workspace" "$CONFIG_DIR"

cp -a ./* "$PREFIX"/
cp -a ./.env.example "$CONFIG_DIR/goar.env.example"
install -m 0644 goar.service /etc/systemd/system/goar.service

python3 -m venv "$PREFIX/.venv"
"$PREFIX/.venv/bin/pip" install --upgrade pip
"$PREFIX/.venv/bin/pip" install -r "$PREFIX/requirements.txt"

# Install system deps first, then download browser binaries
install_system_deps
"$PREFIX/.venv/bin/python" -m playwright install chromium

chown -R "$SERVICE_USER:$SERVICE_USER" "$PREFIX" "$STATE_DIR"
chmod 0750 "$PREFIX/run_cli.sh" "$PREFIX/run_flask.sh"
chmod 0644 "$PREFIX/goar.py" "$PREFIX/wsgi.py"

echo ""
echo "Installed GOAR at $PREFIX."
echo "Copy $CONFIG_DIR/goar.env.example to $CONFIG_DIR/goar.env, set credentials, then:"
echo "  systemctl daemon-reload && systemctl enable --now goar.service"
