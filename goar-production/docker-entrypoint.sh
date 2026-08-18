#!/usr/bin/env sh
set -eu

: "${GOAR_HOME:=/data/goar}"
: "${GOAR_WORKSPACE:=/workspace}"
: "${GOAR_AUTO_INSTALL_DESKTOP:=0}"
: "${GOAR_RUN_UID:=1000}"
: "${GOAR_RUN_GID:=1000}"

export GOAR_HOME GOAR_WORKSPACE GOAR_AUTO_INSTALL_DESKTOP GOAR_RUN_UID GOAR_RUN_GID

if [ "$(id -u)" = "0" ]; then
  # Keep the host-mounted workspace under its existing host ownership. Only
  # private GOAR state and ephemeral desktop files are initialized here.
  mkdir -p "$GOAR_HOME" "${HOME:-/tmp/goar-home}"
  chown -R "$GOAR_RUN_UID:$GOAR_RUN_GID" "$GOAR_HOME" "${HOME:-/tmp/goar-home}"
  exec gosu "$GOAR_RUN_UID:$GOAR_RUN_GID" "$0" "$@"
fi

mkdir -p \
  "$GOAR_HOME" \
  "$GOAR_HOME"/history \
  "$GOAR_HOME"/sessions \
  "$GOAR_HOME"/skills \
  "$GOAR_HOME"/task_events \
  "$GOAR_HOME"/memory \
  "${HOME:-/tmp/goar-home}" \
  "$GOAR_WORKSPACE" \
  "$GOAR_WORKSPACE"/downloads \
  "$GOAR_WORKSPACE"/uploads

case "${GOAR_PUBLIC_BIND_ADDRESS:-127.0.0.1}" in
  127.0.0.1|::1|localhost) ;;
  *)
    if [ -z "${GOAR_REQUIRE_KEY:-}" ]; then
      echo "[GOAR] Warning: no GOAR_REQUIRE_KEY is configured for a non-local published address. Set a strong access key before exposing GOAR." >&2
    fi
    ;;
esac

exec "$@"
