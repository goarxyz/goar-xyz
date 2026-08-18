#!/usr/bin/env bash
set -euo pipefail

# Builds an Alpine guest root filesystem for PRoot. The result is intentionally
# unprivileged: both the build and the eventual runtime use the caller's UID.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/proot"
ROOTFS="$DIST_DIR/rootfs"
CACHE_DIR="$DIST_DIR/.cache"
# Alpine 3.22 supplies Python 3.12. GOAR uses Alpine's native greenlet and
# pyee packages together with Playwright's portable Python client and Alpine's
# system Node runtime. This avoids loading glibc-only Playwright wheels inside
# the musl-based root filesystem.
ALPINE_VERSION="${ALPINE_VERSION:-3.22.5}"
ALPINE_BRANCH="${ALPINE_BRANCH:-3.22}"

case "$(uname -m)" in
  x86_64|amd64) HOST_ARCH="x86_64" ;;
  aarch64|arm64) HOST_ARCH="aarch64" ;;
  *)
    echo "Unsupported host architecture: $(uname -m). Supported: x86_64 and aarch64." >&2
    exit 2
    ;;
esac

# GOAR_ROOTFS_ARCH permits a reproducible aarch64 Alpine rootfs for the Android
# application. Cross-building uses a maintained qemu-user binary through PRoot.
ARCH="${GOAR_ROOTFS_ARCH:-$HOST_ARCH}"
case "$ARCH" in
  x86_64|aarch64) ;;
  *)
    echo "Unsupported GOAR_ROOTFS_ARCH: $ARCH. Supported: x86_64 and aarch64." >&2
    exit 2
    ;;
esac

PROOT_BIN="${PROOT_BIN:-$(command -v proot || true)}"
if [[ -z "$PROOT_BIN" ]]; then
  echo "PRoot is required. Install your distribution's maintained proot package and rerun." >&2
  exit 127
fi

PROOT_QEMU_ARGS=()
if [[ "$ARCH" != "$HOST_ARCH" ]]; then
  if [[ "$HOST_ARCH" == "x86_64" && "$ARCH" == "aarch64" ]]; then
    QEMU_AARCH64_BIN="${QEMU_AARCH64_BIN:-$(command -v qemu-aarch64-static || true)}"
    if [[ -z "$QEMU_AARCH64_BIN" ]]; then
      echo "qemu-aarch64-static is required to build aarch64 on an x86_64 host." >&2
      exit 127
    fi
    PROOT_QEMU_ARGS=(-q "$QEMU_AARCH64_BIN")
  else
    echo "Cross-building $ARCH from $HOST_ARCH is not supported by this builder." >&2
    exit 2
  fi
fi

ROOTFS_ARCHIVE="alpine-minirootfs-${ALPINE_VERSION}-${ARCH}.tar.gz"
ROOTFS_URL="https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_BRANCH}/releases/${ARCH}/${ROOTFS_ARCHIVE}"
mkdir -p "$CACHE_DIR"

if [[ ! -f "$CACHE_DIR/$ROOTFS_ARCHIVE" ]]; then
  echo "[GOAR PRoot] Downloading Alpine ${ALPINE_VERSION} ${ARCH} minirootfs"
  curl --fail --location --retry 3 --output "$CACHE_DIR/$ROOTFS_ARCHIVE" "$ROOTFS_URL"
fi
if [[ ! -f "$CACHE_DIR/$ROOTFS_ARCHIVE.sha256" ]]; then
  curl --fail --location --retry 3 --output "$CACHE_DIR/$ROOTFS_ARCHIVE.sha256" "${ROOTFS_URL}.sha256"
fi
expected_hash="$(awk 'NF { print $1; exit }' "$CACHE_DIR/$ROOTFS_ARCHIVE.sha256")"
actual_hash="$(sha256sum "$CACHE_DIR/$ROOTFS_ARCHIVE" | awk '{print $1}')"
if [[ -z "$expected_hash" || "$expected_hash" != "$actual_hash" ]]; then
  echo "Alpine minirootfs checksum verification failed." >&2
  exit 1
fi

rm -rf "$ROOTFS"
mkdir -p "$ROOTFS"
tar -xzf "$CACHE_DIR/$ROOTFS_ARCHIVE" -C "$ROOTFS"
# QEMU executes foreign guest processes with the host user's filesystem
# credentials. Grant the host user write access while assembling a cross-built
# rootfs; the archived distribution still records deterministic root ownership.
chmod -R a+rwX "$ROOTFS"

# PRoot keeps the guest package manager isolated while allowing network access.
# The resolver bind is required for apk and pip to reach their repositories.
proot_run() {
  "$PROOT_BIN" -0 -R "$ROOTFS" "${PROOT_QEMU_ARGS[@]}" \
    -b /dev -b /proc -b /sys \
    -b /etc/resolv.conf:/etc/resolv.conf \
    /bin/sh -ec "$1"
}

proot_run "
  printf '%s\\n' \
    'https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_BRANCH}/main' \
    'https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_BRANCH}/community' \
    > /etc/apk/repositories
  apk update
  apk add --no-cache \
    bash ca-certificates curl git \
    python3 py3-pip py3-virtualenv py3-greenlet py3-pyee \
    nodejs \
    chromium \
    tigervnc fluxbox xterm websockify \
    font-noto font-noto-emoji ttf-dejavu \
    libstdc++ mesa-gl
  update-ca-certificates
  python3 -m venv --system-site-packages /opt/goar/.venv
"

install -d "$ROOTFS/opt/goar" "$ROOTFS/data/goar" "$ROOTFS/data/workspace" "$ROOTFS/etc/goar"
# The local launcher refreshes this value before every PRoot execution. A
# placeholder keeps the driver wrapper structurally complete in the archive.
printf '%s\n' "$ROOTFS" > "$ROOTFS/etc/goar/host-rootfs-path"
cp -a "$ROOT_DIR/goar-production/." "$ROOTFS/opt/goar/"
cp -a "$DIST_DIR/rootfs-overlay/." "$ROOTFS/"

proot_run "
  grep -v '^playwright' /opt/goar/requirements.txt > /tmp/requirements-no-playwright.txt
  # QEMU guest processes can report a synthetic root identity that pip refuses
  # to use for virtual-environment writes. An explicit target remains inside
  # the same venv search path and works on both native and cross builds.
  /opt/goar/.venv/bin/pip install --target /opt/goar/.venv/lib/python3.12/site-packages --upgrade -r /tmp/requirements-no-playwright.txt

  # Playwright publishes no musllinux wheel. Its Python client is portable,
  # so extract the matching manylinux wheel without its bundled glibc Node
  # binary, then direct it to Alpine's maintained /usr/bin/node instead.
  /opt/goar/.venv/bin/pip download --no-deps --only-binary=:all: \
    --platform manylinux2014_${ARCH} --implementation cp --python-version 312 --abi cp312 \
    --dest /tmp 'playwright==1.62.0'
  set -- /tmp/playwright-*_${ARCH}.whl
  test "\$#" -eq 1
  /bin/busybox unzip -oq "\$1" -d /opt/goar/.venv/lib/python3.12/site-packages
  /opt/goar/.venv/bin/python -c 'from playwright.async_api import async_playwright; print("Playwright client ready")'

  chmod 0755 /usr/local/bin/goar-serve
  chmod 0755 /opt/goar/run_cli.sh /opt/goar/run_flask.sh
  chmod 1777 /tmp
"

# PRoot's Node syscall translation can resolve the driver package against the
# host rootfs. The wrapper maps the guest path to the generated rootfs location.
cat > "$ROOTFS/opt/goar/.venv/lib/python3.12/site-packages/playwright/driver/node" <<'NODE_WRAPPER'
#!/bin/sh
set -eu
script="${1:?missing Playwright driver script}"
shift
case "$script" in
  /opt/goar/*)
    host_root="$(cat /etc/goar/host-rootfs-path)"
    exec /usr/bin/node "${host_root}${script}" "$@"
    ;;
  *)
    exec /usr/bin/node "$script" "$@"
    ;;
esac
NODE_WRAPPER
chmod 0755 "$ROOTFS/opt/goar/.venv/lib/python3.12/site-packages/playwright/driver/node"

# Distribution metadata is written after dependencies resolve so callers can
# tell which exact base and build source they are running.
cat > "$ROOTFS/etc/goar/rootfs-release" <<EOF
GOAR_ROOTFS=alpine-proot
ALPINE_VERSION=${ALPINE_VERSION}
ALPINE_ARCH=${ARCH}
BUILT_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

# A portable archive is convenient for copying to a local PRoot host. It is
# excluded from Git and can be regenerated deterministically by this script.
tar --numeric-owner --sort=name --mtime='UTC 2026-01-01' -C "$ROOTFS" -czf "$DIST_DIR/goar-alpine-${ALPINE_VERSION}-${ARCH}.tar.gz" .

echo "[GOAR PRoot] Build complete"
echo "  Rootfs: $ROOTFS"
echo "  Archive: $DIST_DIR/goar-alpine-${ALPINE_VERSION}-${ARCH}.tar.gz"
