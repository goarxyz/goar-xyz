#!/usr/bin/env bash
# Build the GOAR terminal-first Kali ARM64 PRoot rootfs from the official minimal base.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KALI_ARCHIVE="${KALI_ARCHIVE:-$ROOT/proot/kali-sources/kali-nethunter-rootfs-minimal-arm64.tar.xz}"
KALI_SHA256_FILE="${KALI_SHA256_FILE:-$ROOT/proot/kali-sources/expected-minimal-arm64.sha256}"
STAGE="${STAGE:-$ROOT/proot/.kali-terminal-stage}"
OUTPUT="${OUTPUT:-$ROOT/proot/goar-kali-terminal-arm64.tar.gz}"
VIBE_SOURCE="$ROOT/proot/kali-terminal-vibehack"
OVERLAY="$ROOT/proot/kali-terminal-overlay"
QEMU="${QEMU_AARCH64:-$(command -v qemu-aarch64-static)}"
PROOT="${PROOT:-$(command -v proot)}"
GET_PIP="${GET_PIP:-$ROOT/proot/tools/get-pip.py}"

for required in "$KALI_ARCHIVE" "$KALI_SHA256_FILE" "$VIBE_SOURCE/pyproject.toml" "$VIBE_SOURCE/requirements.lock" "$OVERLAY/opt/goar-terminal/GOAR_TERMINAL_PROMPT.md" "$QEMU" "$PROOT"; do
  [[ -e "$required" ]] || { echo "Missing required build input: $required" >&2; exit 2; }
done

# This official helper is intentionally a local build cache rather than a
# versioned repository artifact. The guest has no pip bootstrap by default.
if [[ ! -f "$GET_PIP" ]]; then
  mkdir -p "$(dirname "$GET_PIP")"
  curl --fail --location --retry 3 --silent --show-error \
    https://bootstrap.pypa.io/get-pip.py -o "$GET_PIP"
fi

expected="$(awk '{print $1}' "$KALI_SHA256_FILE" | head -n 1)"
actual="$(sha256sum "$KALI_ARCHIVE" | awk '{print $1}')"
[[ "$expected" == "$actual" ]] || { echo "Kali archive checksum mismatch" >&2; exit 3; }

rm -rf "$STAGE"
mkdir -p "$STAGE"
# Device nodes are intentionally not archived. Android PRoot supplies /dev bind mounts.
tar --exclude='dev/*' --exclude='./dev/*' -xJf "$KALI_ARCHIVE" -C "$STAGE"
GUEST="$STAGE/kali-arm64"
[[ -d "$GUEST/usr" && -d "$GUEST/etc" ]] || { echo "Unexpected Kali archive layout" >&2; exit 4; }

mkdir -p "$GUEST/opt/vibehack/app" "$GUEST/opt/goar-terminal" "$GUEST/data/goar/home" "$GUEST/data/goar/control" "$GUEST/data/goar/tmp" "$GUEST/data/goar/logs" "$GUEST/data/workspace" "$GUEST/usr/local/bin" "$GUEST/tmp"
tar -C "$VIBE_SOURCE" --exclude=.git --exclude='__pycache__' -cf - . | tar -C "$GUEST/opt/vibehack/app" -xf -
tar -C "$OVERLAY" --exclude='__pycache__' -cf - . | tar -C "$GUEST" -xf -
cp "$GET_PIP" "$GUEST/tmp/get-pip.py"
chmod 0755 "$GUEST/usr/local/bin/goar-terminal" "$GUEST/usr/local/bin/goarctl" "$GUEST/opt/goar-terminal/goarctl.py" "$GUEST/opt/goar-terminal/goar_loopd.py" "$GUEST/opt/goar-terminal/goar_agent_turn.py"

"$PROOT" -0 -r "$GUEST" -q "$QEMU" -b /dev -b /proc -b /sys -b /etc/resolv.conf:/etc/resolv.conf /usr/bin/bash --noprofile --norc -c '
  set -e
  python3 -m venv --without-pip /opt/vibehack/.venv
  /opt/vibehack/.venv/bin/python /tmp/get-pip.py --disable-pip-version-check
  /opt/vibehack/.venv/bin/python -m pip install --no-cache-dir -r /opt/vibehack/app/requirements.lock
  /opt/vibehack/.venv/bin/python -m pip install --no-cache-dir --no-deps /opt/vibehack/app
  export GOAR_PROOT_GUEST=1 VH_SANDBOX=true HOME=/data/goar/home GOAR_WORKSPACE=/data/workspace GOAR_CONTROL_ROOT=/data/goar/control GOAR_RUNTIME_TMP=/data/goar/tmp
  /usr/local/bin/goarctl status >/tmp/goarctl-smoke.json
  /opt/vibehack/.venv/bin/vibehack --help >/tmp/vibehack-help.txt
  rm -rf /root/.cache /tmp/pip-* /tmp/get-pip.py
  find /opt/vibehack -type d -name __pycache__ -prune -exec rm -rf {} +
  find /opt/vibehack -type f -name "*.pyc" -delete
'

# Clear build-only and first-run state; Android mounts durable state under /data at launch.
rm -rf "$GUEST/data/goar/control"/* "$GUEST/data/goar/home"/* "$GUEST/data/goar/logs"/* "$GUEST/data/workspace"/*
rm -rf "$GUEST/tmp"/* "$GUEST/var/cache/apt/archives"/* "$GUEST/var/lib/apt/lists"/*
# The minimal NetHunter base includes harmless Chromium policy remnants; the terminal product ships no browser stack.
rm -rf "$GUEST/etc/chromium" "$GUEST/usr/share/chromium" "$GUEST/usr/share/kali-defaults/etc/chromium"
rm -f "$GUEST/usr/lib/udev/hwdb.d/60-autosuspend-chromiumos.hwdb" "$GUEST/usr/share/vboot/bin/lib/shflags/README.chromium"
find "$GUEST/opt" "$GUEST/usr/local" "$GUEST/data" -xdev -type f -name '*.pyc' -delete
find "$GUEST/opt" "$GUEST/usr/local" "$GUEST/data" -xdev -type d -name __pycache__ -prune -exec rm -rf {} +

mkdir -p "$(dirname "$OUTPUT")"
tar --exclude='./run/systemd' --exclude='./run/systemd/*' --exclude='./dev' --exclude='./dev/*' --exclude='./proc' --exclude='./proc/*' --exclude='./sys' --exclude='./sys/*' --numeric-owner --sort=name --mtime='UTC 2026-08-19' --pax-option=delete=atime,delete=ctime -C "$GUEST" -czf "$OUTPUT" .
printf '%s  %s\n' "$(sha256sum "$OUTPUT" | awk '{print $1}')" "$(basename "$OUTPUT")" > "$OUTPUT.sha256"
printf 'archive=%s\nbytes=%s\nsha256=%s\n' "$OUTPUT" "$(stat -c %s "$OUTPUT")" "$(sha256sum "$OUTPUT" | awk '{print $1}')"
