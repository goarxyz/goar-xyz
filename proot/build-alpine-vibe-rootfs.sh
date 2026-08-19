#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/proot"
CACHE_DIR="$DIST_DIR/alpine-vibe-cache"
SOURCE_DIR="$DIST_DIR/alpine-vibe-mistral"
OVERLAY_DIR="$DIST_DIR/alpine-vibe-overlay"
ROOTFS="${ROOTFS:-$DIST_DIR/alpine-vibe-rootfs}"
ARCHIVE_OUT="${ARCHIVE_OUT:-$DIST_DIR/goar-alpine-vibe-3.24.1-aarch64.tar.gz}"
SHA_OUT="${ARCHIVE_OUT}.sha256"

ALPINE_VERSION="3.24.1"
ALPINE_BRANCH="3.24"
ARCH="aarch64"
ROOTFS_ARCHIVE="$CACHE_DIR/alpine-minirootfs-${ALPINE_VERSION}-${ARCH}.tar.gz"
ROOTFS_CHECKSUM="$ROOTFS_ARCHIVE.sha256"
EXPECTED_SHA256="f55a90f69052c5bd6f92cb09a8f47065970830b194c917a006fb94028e721259"
TREE_SITTER_WHEEL="$CACHE_DIR/tree_sitter-0.26.0-cp314-cp314-manylinux2014_aarch64.whl"
TREE_SITTER_WHEEL_URL="https://files.pythonhosted.org/packages/c4/2c/c82326b7b97e3c485c18679883b16f89e5e913c639d3b219d3da70c9e67e/tree_sitter-0.26.0-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl"
TREE_SITTER_WHEEL_SHA256="b8ea92a255c91671a7ec4625aba3ab7bb5220c423630ffbf83c45d7312abe084"

PROOT_BIN="${PROOT_BIN:-$(command -v proot || true)}"
QEMU_AARCH64_BIN="${QEMU_AARCH64_BIN:-$(command -v qemu-aarch64-static || true)}"

if [[ -z "$PROOT_BIN" || ! -x "$PROOT_BIN" ]]; then
  echo "PRoot is required to build the Alpine guest." >&2
  exit 127
fi
if [[ -z "$QEMU_AARCH64_BIN" || ! -x "$QEMU_AARCH64_BIN" ]]; then
  echo "qemu-aarch64-static is required to build AArch64 on this host." >&2
  exit 127
fi
for required in "$ROOTFS_ARCHIVE" "$ROOTFS_CHECKSUM" "$SOURCE_DIR/pyproject.toml" "$OVERLAY_DIR/usr/local/bin/goar-alpine-vibe"; do
  if [[ ! -e "$required" ]]; then
    echo "Missing required Alpine Vibe build input: $required" >&2
    exit 2
  fi
done

published_sha256="$(awk 'NF { print $1; exit }' "$ROOTFS_CHECKSUM")"
actual_sha256="$(sha256sum "$ROOTFS_ARCHIVE" | awk '{print $1}')"
if [[ "$published_sha256" != "$EXPECTED_SHA256" || "$actual_sha256" != "$EXPECTED_SHA256" ]]; then
  echo "Fresh Alpine minirootfs checksum verification failed." >&2
  echo "Expected: $EXPECTED_SHA256" >&2
  echo "Published: $published_sha256" >&2
  echo "Actual:   $actual_sha256" >&2
  exit 1
fi

if [[ ! -f "$TREE_SITTER_WHEEL" ]]; then
  curl --fail --location --retry 3 --output "$TREE_SITTER_WHEEL" "$TREE_SITTER_WHEEL_URL"
fi
if [[ "$(sha256sum "$TREE_SITTER_WHEEL" | awk '{print $1}')" != "$TREE_SITTER_WHEEL_SHA256" ]]; then
  echo "Pinned tree-sitter wheel checksum verification failed." >&2
  exit 1
fi

rm -rf "$ROOTFS"
mkdir -p "$ROOTFS"
tar -xzf "$ROOTFS_ARCHIVE" -C "$ROOTFS"
chmod -R u+rwX "$ROOTFS"

proot_run() {
  "$PROOT_BIN" -0 -R "$ROOTFS" -q "$QEMU_AARCH64_BIN" \
    -b /dev -b /proc -b /sys -b /etc/resolv.conf:/etc/resolv.conf \
    /bin/sh -ec "$1"
}

proot_run "
  printf '%s\\n' \\
    'https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_BRANCH}/main' \\
    'https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_BRANCH}/community' \\
    > /etc/apk/repositories
  apk update
  apk add --no-cache \\
    bash ca-certificates coreutils curl git \\
    python3 py3-pip py3-virtualenv \\
    build-base python3-dev linux-headers libffi-dev openssl-dev \\
    cargo rust gcompat \\
    font-dejavu font-noto
  update-ca-certificates
  mkdir -p /opt/goar-alpine-vibe /data/goar/workspace /etc/goar-alpine-vibe
  chmod 0755 /data /data/goar /data/goar/workspace
"

cp -a "$SOURCE_DIR/." "$ROOTFS/opt/goar-alpine-vibe/"
# Runtime packaging deliberately omits upstream development-only material. This
# excludes non-runtime audio fixtures and CI-only Sentry injection scripts while
# retaining the complete production TUI, onboarding, agent, session, tool, and
# workspace packages.
rm -rf "$ROOTFS/opt/goar-alpine-vibe/.git" "$ROOTFS/opt/goar-alpine-vibe/.github" "$ROOTFS/opt/goar-alpine-vibe/.vibe" "$ROOTFS/opt/goar-alpine-vibe/tests" "$ROOTFS/opt/goar-alpine-vibe/scripts"
cp -a "$OVERLAY_DIR/." "$ROOTFS/"
chmod 0755 "$ROOTFS/usr/local/bin/goar-alpine-vibe"

proot_run "
  python3 -m venv /opt/goar-alpine-vibe/.venv
"

# Alpine 3.24 currently provides Python 3.14 while the upstream tree-sitter
# release offers an AArch64 manylinux wheel but not a musllinux wheel for 3.14.
# The tested wheel works with Alpine's gcompat after its extension suffix is
# renamed to the guest interpreter's musl suffix; this avoids QEMU compiler
# subprocess failures while retaining the upstream pinned tree-sitter release.
unzip -oq "$TREE_SITTER_WHEEL" -d "$ROOTFS/opt/goar-alpine-vibe/.venv/lib/python3.14/site-packages"
mv "$ROOTFS/opt/goar-alpine-vibe/.venv/lib/python3.14/site-packages/tree_sitter/_binding.cpython-314-aarch64-linux-gnu.so" "$ROOTFS/opt/goar-alpine-vibe/.venv/lib/python3.14/site-packages/tree_sitter/_binding.cpython-314-aarch64-linux-musl.so"

proot_run "
  /opt/goar-alpine-vibe/.venv/bin/pip install --no-cache-dir --upgrade pip
  /opt/goar-alpine-vibe/.venv/bin/pip install --no-cache-dir /opt/goar-alpine-vibe
  # mistralai declares tracing packages transitively. The private fork replaces
  # every tracing call with local no-op spans, so remove these packages entirely.
  /opt/goar-alpine-vibe/.venv/bin/pip uninstall -y \\
    opentelemetry-api opentelemetry-exporter-otlp-proto-common \\
    opentelemetry-exporter-otlp-proto-http opentelemetry-proto \\
    opentelemetry-sdk opentelemetry-semantic-conventions || true
  rm -rf /opt/goar-alpine-vibe/.venv/lib/python3.14/site-packages/opentelemetry* \\
    /opt/goar-alpine-vibe/.venv/lib/python3.14/site-packages/*opentelemetry*
  # Wheels may bundle their own test suites; they are not runtime dependencies
  # and can contain obsolete telemetry fixture code.
  find /opt/goar-alpine-vibe/.venv/lib/python3.14/site-packages -type d -name tests -prune -exec rm -rf {} +
  /opt/goar-alpine-vibe/.venv/bin/python -m compileall -q /opt/goar-alpine-vibe/vibe
  /opt/goar-alpine-vibe/.venv/bin/vibe --version
  test ! -e /opt/goar-alpine-vibe/vibe/cli/audio_player
  test ! -e /opt/goar-alpine-vibe/vibe/cli/audio_recorder
  test ! -e /opt/goar-alpine-vibe/vibe/cli/transcribe
  test ! -d /opt/goar-alpine-vibe/.venv/lib/python3.14/site-packages/opentelemetry
  chmod 0755 /usr/local/bin/goar-alpine-vibe
  chmod 1777 /tmp
"

cat > "$ROOTFS/etc/goar-alpine-vibe/rootfs-release" <<EOF
GOAR_ROOTFS=alpine-private-vibe-proot
ALPINE_VERSION=${ALPINE_VERSION}
ALPINE_ARCH=${ARCH}
UPSTREAM_MISTRAL_VIBE_COMMIT=5e6aa0f6beb3454454f4c1de74a7652ba577ab05
PRIVACY_PROFILE=no-telemetry-no-crash-reports-no-updates-no-audio-no-feedback-no-account-no-experiments
LAUNCHER=/usr/local/bin/goar-alpine-vibe
EOF

rm -f "$ARCHIVE_OUT" "$SHA_OUT"
tar --numeric-owner --sort=name --mtime='UTC 2026-01-01' -C "$ROOTFS" -cf - . | gzip -n > "$ARCHIVE_OUT"
sha256sum "$ARCHIVE_OUT" > "$SHA_OUT"

printf '%s\n' "[GOAR Alpine Private Vibe] Build complete"
printf '%s\n' "  Rootfs:  $ROOTFS"
printf '%s\n' "  Archive: $ARCHIVE_OUT"
printf '%s\n' "  SHA256:  $(awk '{print $1}' "$SHA_OUT")"
