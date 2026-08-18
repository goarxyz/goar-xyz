#!/usr/bin/env bash
# bundle-libs.sh — collect every shared library Playwright's Chromium
# headless shell needs into goar-production/bundled-libs/.
#
# How it works (fast — no slow recursive /nix/store scan):
#
#   1. readelf -d extracts NEEDED lib names from the browser binary (static,
#      cannot hang even on Chrome's special ELF).
#
#   2. PATH already contains /nix/store/<hash>-<pkg>/bin entries for every
#      installed Nix package.  We strip /bin → /lib to get lib dirs instantly.
#
#   3. For the mesa-libgbm package (which has no /bin dir and therefore isn't
#      in PATH), we query the Nix store DB:
#        nix-store --query --references <main-mesa-path>
#      which returns the exact store path of the gbm output in milliseconds.
#
#   4. We recurse one level into each copied Nix lib to pick up transitive deps
#      (e.g. libdrm variants that libgbm requires).
#
# After this runs, run-goar.sh prepends bundled-libs/ to LD_LIBRARY_PATH
# (Replit also does this automatically for the workflow environment).
# The package then starts on any glibc Linux host without needing Nix or apt.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$ROOT/goar-production/bundled-libs"
mkdir -p "$DEST"

# ── Locate the Playwright browser binaries ─────────────────────────────────
PW_SHELL=$(find "$ROOT/.cache/ms-playwright" \
            -name "chrome-headless-shell" -type f 2>/dev/null | head -1 || true)
PW_CHROME=$(find "$ROOT/.cache/ms-playwright" \
             -maxdepth 5 -name "chrome" -type f 2>/dev/null | head -1 || true)

if [ -z "$PW_SHELL" ] && [ -z "$PW_CHROME" ]; then
  echo "ERROR: No Playwright browser binary found." \
       "Run 'python3 -m playwright install chromium' first." >&2
  exit 1
fi

# ── Helpers ────────────────────────────────────────────────────────────────

declare -A _COPIED

copy_lib() {
  local src="$1"
  [ -f "$src" ] || return 0
  [ -n "${_COPIED[$src]+set}" ] && return 0
  _COPIED[$src]=1

  local name real real_name
  name="$(basename "$src")"
  real="$(readlink -f "$src")"
  real_name="$(basename "$real")"

  if [ ! -f "$DEST/$real_name" ]; then
    cp -L "$src" "$DEST/$real_name"
    chmod 0755 "$DEST/$real_name"
    echo "  bundled: $real_name"
  fi
  if [ "$name" != "$real_name" ] && [ ! -e "$DEST/$name" ]; then
    ln -sf "$real_name" "$DEST/$name"
  fi
}

# NEEDED lib names from a binary via readelf (static; cannot hang)
needed_libs() {
  local binary="$1"
  readelf -d "$binary" 2>/dev/null | awk '/\(NEEDED\)/ {
    line = $0
    idx = index(line, "[")
    if (idx > 0) {
      rest = substr(line, idx+1)
      end = index(rest, "]")
      if (end > 0) print substr(rest, 1, end-1)
    }
  }'
}

# System lib dirs — present on every glibc Linux host; we do NOT bundle these
SYS_DIRS=(
  /lib /lib64
  /lib/x86_64-linux-gnu
  /lib/x86_64-linux-gnu/glibc-hwcaps/x86-64-v4
  /lib/x86_64-linux-gnu/glibc-hwcaps/x86-64-v3
  /usr/lib /usr/lib/x86_64-linux-gnu
)

in_system_dirs() {
  local soname="$1"
  local d
  for d in "${SYS_DIRS[@]}"; do
    [ -f "$d/$soname" ] && return 0
    # check versioned name glob
    local stem="${soname%%.*}"
    ls "$d/${stem}.so"* 2>/dev/null | head -1 | grep -q . && return 0
  done
  return 1
}

# ── Build Nix lib dirs from current PATH ──────────────────────────────────
# PATH contains /nix/store/<hash>-<pkg>/bin for every activated Nix package.
# Strip /bin to get the package root, then add /lib and /lib64 if they exist.
NIX_LIB_DIRS=()
IFS=: read -ra _PATH_DIRS <<< "${PATH:-}"
for d in "${_PATH_DIRS[@]}"; do
  [[ "$d" != /nix/store/* ]] && continue
  pkg_root="${d%/bin}"
  [ -d "$pkg_root/lib" ]   && NIX_LIB_DIRS+=("$pkg_root/lib")
  [ -d "$pkg_root/lib64" ] && NIX_LIB_DIRS+=("$pkg_root/lib64")
done

# ── Also add mesa-libgbm (no /bin dir, not in PATH) ───────────────────────
# Find it via the main mesa package which IS in PATH
mesa_bin_pkg=$(printf '%s\n' "${_PATH_DIRS[@]}" | grep '/nix/store/[^/]*-mesa-[0-9]' | grep -v 'cross_tools\|spirv\|opencl\|dev$' | head -1 || true)
if [ -n "$mesa_bin_pkg" ]; then
  mesa_pkg_root="${mesa_bin_pkg%/bin}"
  # Query the Nix store DB for mesa's referenced packages (includes libgbm output)
  while IFS= read -r dep; do
    [ -d "$dep/lib" ] && NIX_LIB_DIRS+=("$dep/lib")
  done < <(nix-store --query --references "$mesa_pkg_root" 2>/dev/null | grep -i "gbm\|drm\|mesa" || true)
fi

echo "Nix lib dirs: ${#NIX_LIB_DIRS[@]}"

# ── Resolve and bundle a soname ───────────────────────────────────────────
bundle_soname() {
  local soname="$1"
  in_system_dirs "$soname" && return 0   # system lib — don't bundle

  local stem="${soname%%.*}"
  local found=""
  for ld in "${NIX_LIB_DIRS[@]}"; do
    local hit
    hit=$(ls "$ld/${stem}.so"* 2>/dev/null | head -1 || true)
    if [ -n "$hit" ]; then
      found="$hit"
      break
    fi
  done

  if [ -n "$found" ]; then
    copy_lib "$found"
  else
    echo "  WARNING: $soname not found in Nix dirs" >&2
  fi
}

# ── Bundle transitive deps of a Nix lib (one level) ──────────────────────
bundle_transitive() {
  local binary="$1"
  while IFS= read -r soname; do
    [ -n "$soname" ] && bundle_soname "$soname"
  done < <(needed_libs "$binary")
}

# ── Main ──────────────────────────────────────────────────────────────────
echo "=== Bundling Chromium shared libraries into bundled-libs/ ==="

# Pass 1: direct deps of the Playwright browser binaries
for binary in "$PW_SHELL" "$PW_CHROME"; do
  [ -f "$binary" ] || continue
  echo "--- scanning $(basename "$binary") ---"
  while IFS= read -r soname; do
    [ -n "$soname" ] && bundle_soname "$soname"
  done < <(needed_libs "$binary")
done

# Pass 2: transitive deps of each lib we just bundled
echo "--- scanning transitive deps ---"
for lib in "$DEST"/*.so* ; do
  [ -f "$lib" ] || continue
  bundle_transitive "$lib"
done

count=$(find "$DEST" -maxdepth 1 -name "*.so*" 2>/dev/null | wc -l || echo 0)
echo "=== Done: $count library files in $DEST ==="
