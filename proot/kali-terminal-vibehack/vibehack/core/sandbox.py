"""PRoot-native execution environment for the GOAR terminal distribution.

VibeHack's upstream sandbox is a Docker container.  GOAR is already executing
inside an Android app-private Kali PRoot guest, so attempting to start Docker
would fail and would duplicate the containment boundary.  This module preserves
the upstream public sandbox API while defining that guest as the execution
runtime.
"""

from __future__ import annotations

import atexit
import os
from pathlib import Path

from rich.console import Console

from vibehack.config import cfg

console = Console()

# Kept for upstream callers that display or retain a sandbox identifier.
CONTAINER_NAME = "goar-proot-guest"
IMAGE_NAME = "kali-nethunter-minimal-arm64"
GUEST_MARKER_ENV = "GOAR_PROOT_GUEST"
DEFAULT_WORKSPACE = Path("/data/workspace")
DEFAULT_TMP = Path("/data/goar/tmp")


def _inside_goar_guest() -> bool:
    """Return true only for the launcher-created GOAR PRoot guest."""
    return os.getenv(GUEST_MARKER_ENV, "") == "1"


def check_docker() -> bool:
    """Compatibility name: validate the PRoot guest instead of Docker."""
    return _inside_goar_guest()


def _workspace() -> Path:
    return Path(os.getenv("GOAR_WORKSPACE", str(DEFAULT_WORKSPACE))).expanduser()


def _runtime_tmp() -> Path:
    return Path(os.getenv("GOAR_RUNTIME_TMP", str(DEFAULT_TMP))).expanduser()


def is_container_running() -> bool:
    """Compatibility name: the PRoot guest is present for the process lifetime."""
    return _inside_goar_guest()


def is_container_exists() -> bool:
    return _inside_goar_guest()


def install_docker_engine() -> None:
    """Docker is intentionally unavailable in the Android PRoot distribution."""
    raise RuntimeError(
        "GOAR runs VibeHack inside its app-private Kali PRoot guest; Docker is not "
        "installed or required. Start the terminal through the GOAR launcher."
    )


def pull_image_if_needed() -> None:
    """No-op: the verified Kali guest rootfs is downloaded by the Android installer."""
    if not _inside_goar_guest():
        raise RuntimeError(
            "GOAR PRoot guest not detected. Launch VibeHack through goar-terminal."
        )


def start_sandbox() -> None:
    """Prepare durable in-guest directories for the current VibeHack session."""
    if not _inside_goar_guest():
        raise RuntimeError(
            "GOAR PRoot guest not detected. This VibeHack build cannot start Docker."
        )
    workspace = _workspace()
    runtime_tmp = _runtime_tmp()
    workspace.mkdir(parents=True, exist_ok=True)
    runtime_tmp.mkdir(parents=True, exist_ok=True)
    cfg.BIN_DIR.mkdir(parents=True, exist_ok=True)
    console.print(
        "[bold green]✓ GOAR app-private Kali PRoot runtime ready[/bold green]"
    )
    console.print(
        f"[dim]  Workspace: {workspace} (RW), guest network: enabled[/dim]"
    )


def ensure_sandbox_running() -> bool:
    """Maintain upstream behavior while treating PRoot as the runtime boundary."""
    try:
        start_sandbox()
        return True
    except Exception as exc:  # pragma: no cover - console path
        console.print(f"[bold red]GOAR PRoot runtime unavailable: {exc}[/bold red]")
        return False


def stop_sandbox() -> None:
    """No-op: PRoot lifetime is owned by the Android terminal foreground service."""
    return None


atexit.register(stop_sandbox)
