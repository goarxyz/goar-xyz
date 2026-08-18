#!/usr/bin/env bash
# Production build script for GOAR on Replit.
#
# Steps:
#   1. Compile Python sources
#   2. Install Python dependencies into the workspace venv (.pythonlibs)
#   3. Download Playwright Chromium browser binaries
#   4. Bundle all required Nix-store shared libraries into
#      goar-production/bundled-libs/ so the package ships self-contained
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "=== GOAR production build ==="

# --- Locate the Python interpreter to use ---
# Replit creates a workspace venv at .pythonlibs/; use that so we stay in the
# same environment that gunicorn / run_flask.sh uses at runtime.
if [ -x "$ROOT/.pythonlibs/bin/python3" ]; then
  PY="$ROOT/.pythonlibs/bin/python3"
else
  PY="$(command -v python3)"
fi
echo "Python: $PY ($($PY --version 2>&1))"

# --- Locate pip ---
# Replit's .pythonlibs venv doesn't bundle pip; use uv (always present on
# Replit/Nix) pointing at our venv.  On traditional hosts with pip, use that.
if command -v uv >/dev/null 2>&1; then
  PIP_INSTALL="uv pip install --python $PY"
elif [ -x "$ROOT/.pythonlibs/bin/pip" ]; then
  PIP_INSTALL="$ROOT/.pythonlibs/bin/pip install"
elif $PY -m pip --version >/dev/null 2>&1; then
  PIP_INSTALL="$PY -m pip install"
else
  # Last resort: nix store pip (read-only for system packages, but can install
  # into a --target directory — skip silently if all else fails)
  echo "WARNING: no pip/uv found; skipping dependency install (packages may already be installed)" >&2
  PIP_INSTALL=""
fi

# 1. Compile Python sources (catches syntax errors early)
echo "--- compiling Python sources ---"
$PY -m compileall -q goar-production

# 2. Install Python dependencies
echo "--- installing Python dependencies ---"
if [ -n "$PIP_INSTALL" ]; then
  $PIP_INSTALL -r goar-production/requirements.txt
else
  echo "  skipped (no installer available)"
fi

# 3. Download Playwright browser binaries.
#    On Replit, system libraries come from Nix packages declared in .replit.
#    Set GOAR_PLAYWRIGHT_WITH_DEPS=1 on apt/dnf hosts to also pull system libs.
echo "--- installing Playwright Chromium ---"
if [ "${GOAR_PLAYWRIGHT_WITH_DEPS:-0}" = "1" ] && command -v apt-get >/dev/null 2>&1; then
  $PY -m playwright install --with-deps chromium
elif [ "${GOAR_PLAYWRIGHT_WITH_DEPS:-0}" = "1" ] && command -v dnf >/dev/null 2>&1; then
  $PY -m playwright install --with-deps chromium
else
  $PY -m playwright install chromium
fi

# 4. Bundle shared libraries so the package ships ready on any Linux host
echo "--- bundling shared libraries ---"
bash "$(dirname "${BASH_SOURCE[0]}")/bundle-libs.sh"

echo "=== GOAR build complete ==="
