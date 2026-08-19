from __future__ import annotations

import os
from pathlib import Path

import pexpect

ROOTFS = os.environ.get(
    "GOAR_ALPINE_VIBE_ROOTFS", "/home/ubuntu/goar-xyz/proot/alpine-vibe-rootfs"
)
LOG = Path("/home/ubuntu/goar-alpine-vibe-first-boot-pexpect.log")
COMMAND = (
    "sudo unshare -n -- /usr/bin/proot -0 "
    f"-R {ROOTFS} -q /usr/bin/qemu-aarch64-static "
    "-b /dev -b /proc -b /sys /bin/sh -ec "
    "'HOME=/data/goar-first-boot TERM=xterm-256color "
    "/usr/local/bin/goar-alpine-vibe'"
)

with LOG.open("wb") as log:
    child = pexpect.spawn(
        "/bin/sh",
        ["-c", COMMAND],
        encoding=None,
        timeout=45,
        dimensions=(32, 120),
    )
    child.logfile_read = log
    index = child.expect(
        [
            b"Welcome",
            b"Mistral",
            b"Vibe",
            b"API Key",
            b"onboarding",
            pexpect.EOF,
            pexpect.TIMEOUT,
        ]
    )
    if index >= 5:
        output = child.before.decode("utf-8", errors="replace")
        child.close(force=True)
        raise SystemExit(f"TUI did not render expected onboarding content (index={index}): {output}")
    child.sendcontrol("c")
    child.close(force=True)

print("first-boot full-screen Textual onboarding probe passed")
