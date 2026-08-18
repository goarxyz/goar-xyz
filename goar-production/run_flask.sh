#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
: "${GOAR_HOST:=127.0.0.1}"
: "${GOAR_PORT:=8080}"
if ! command -v gunicorn >/dev/null 2>&1; then
  echo "gunicorn is required for production Flask service execution; install requirements.txt first" >&2
  exit 127
fi
exec gunicorn \
  --chdir "$(pwd)" \
  --bind "${GOAR_HOST}:${GOAR_PORT}" \
  --workers 1 \
  --threads 8 \
  --timeout 0 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile - \
  wsgi:application
