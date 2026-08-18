#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOTFS="$ROOT_DIR/proot/rootfs"
PROOT_BIN="${PROOT_BIN:-$(command -v proot)}"
QEMU_AARCH64_BIN="${QEMU_AARCH64_BIN:-$(command -v qemu-aarch64-static)}"

chmod -R a+rwX "$ROOTFS"
"$PROOT_BIN" -0 -R "$ROOTFS" -q "$QEMU_AARCH64_BIN" \
  -b /dev -b /proc -b /sys -b /etc/resolv.conf:/etc/resolv.conf \
  /bin/sh -ec '
    grep -v "^playwright" /opt/goar/requirements.txt > /tmp/requirements-no-playwright.txt
    /opt/goar/.venv/bin/pip install --target /opt/goar/.venv/lib/python3.12/site-packages --upgrade -r /tmp/requirements-no-playwright.txt
    /opt/goar/.venv/bin/pip download --no-deps --only-binary=:all: \
      --platform manylinux2014_aarch64 --implementation cp --python-version 312 --abi cp312 \
      --dest /tmp "playwright==1.62.0"
    set -- /tmp/playwright-*_aarch64.whl
    test "$#" -eq 1
    /bin/busybox unzip -oq "$1" -d /opt/goar/.venv/lib/python3.12/site-packages
    /opt/goar/.venv/bin/python -c "from playwright.async_api import async_playwright; print(\"Playwright client ready\")"
    chmod 0755 /usr/local/bin/goar-serve /opt/goar/run_cli.sh /opt/goar/run_flask.sh
    chmod 1777 /tmp
  '

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

mkdir -p "$ROOTFS/etc/goar"
cat > "$ROOTFS/etc/goar/rootfs-release" <<EOF
GOAR_ROOTFS=alpine-proot
ALPINE_VERSION=3.22.5
ALPINE_ARCH=aarch64
BUILT_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

tar --numeric-owner --sort=name --mtime='UTC 2026-01-01' -C "$ROOTFS" -czf "$ROOT_DIR/proot/goar-alpine-3.22.5-aarch64.tar.gz" .
