#!/usr/bin/env bash
# Launcher for GOAR on Replit.
#
# Replit's workflow environment automatically sets:
#   LD_LIBRARY_PATH=/path/to/goar-production/bundled-libs
#
# That directory is populated at build time by bundle-libs.sh with every
# Nix-store shared library that Playwright's Chromium headless shell needs
# (libgbm, libxkbcommon, libdrm, libasound, libdbus, etc.) so the binary
# starts on any glibc Linux host without needing Nix or a package manager.
#
# On non-Replit hosts: set LD_LIBRARY_PATH manually if bundled-libs/ is
# not already on it, or use 'playwright install --with-deps chromium' and
# the traditional goar-production/install.sh instead.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# Prepend bundled libs (safe no-op if already set by the workflow environment)
BUNDLED="$ROOT/goar-production/bundled-libs"
if [ -d "$BUNDLED" ]; then
  case ":${LD_LIBRARY_PATH:-}:" in
    *":$BUNDLED:"*) ;;   # already present
    *) export LD_LIBRARY_PATH="$BUNDLED${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
  esac
fi

exec bash goar-production/run_flask.sh
