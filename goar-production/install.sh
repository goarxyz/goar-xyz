#!/usr/bin/env bash
set -euo pipefail

PREFIX=${GOAR_PREFIX:-/opt/goar}
STATE_DIR=${GOAR_STATE_DIR:-/var/lib/goar}
CONFIG_DIR=${GOAR_CONFIG_DIR:-/etc/goar}
SERVICE_USER=${GOAR_SERVICE_USER:-goar}

if [ "$(id -u)" -ne 0 ]; then
  echo "Run install.sh as root or with sudo." >&2
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$STATE_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -o "$SERVICE_USER" -g "$SERVICE_USER" "$PREFIX" "$STATE_DIR" "$STATE_DIR/workspace" "$CONFIG_DIR"
cp -a ./* "$PREFIX"/
cp -a ./.env.example "$CONFIG_DIR/goar.env.example"
install -m 0644 goar.service /etc/systemd/system/goar.service

python3 -m venv "$PREFIX/.venv"
"$PREFIX/.venv/bin/pip" install --upgrade pip
"$PREFIX/.venv/bin/pip" install -r "$PREFIX/requirements.txt"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PREFIX" "$STATE_DIR"
chmod 0750 "$PREFIX/run_cli.sh" "$PREFIX/run_flask.sh"
chmod 0644 "$PREFIX/goar.py" "$PREFIX/wsgi.py"

echo "Installed GOAR at $PREFIX. Copy $CONFIG_DIR/goar.env.example to $CONFIG_DIR/goar.env, set credentials, then run:"
echo "  systemctl daemon-reload && systemctl enable --now goar.service"
