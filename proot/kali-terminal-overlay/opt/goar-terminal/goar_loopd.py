#!/usr/bin/env python3
"""Small durable scheduler for GOAR session-scoped VibeHack turns."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from goar_vibe_core import GoarVibeCore


CONTROL_ROOT = Path(os.getenv("GOAR_CONTROL_ROOT", "/data/goar/control"))
WORKSPACE = Path(os.getenv("GOAR_WORKSPACE", "/data/workspace"))
PYTHON = os.getenv("GOAR_PYTHON", "/opt/vibehack/.venv/bin/python")
TURN_RUNNER = Path("/opt/goar-terminal/goar_agent_turn.py")
POLL_SECONDS = max(2, int(os.getenv("GOAR_LOOP_POLL_SECONDS", "5")))
TURN_TIMEOUT = max(30, int(os.getenv("GOAR_LOOP_TURN_TIMEOUT", "300")))
RUNNING = True


def stop(_signal: int, _frame: object) -> None:
    global RUNNING
    RUNNING = False


def session_ids() -> list[str]:
    directory = CONTROL_ROOT / "loops"
    if not directory.exists():
        return []
    return sorted(path.stem for path in directory.glob("*.json") if path.stem)


def run_due(core: GoarVibeCore) -> None:
    for item in core.loops.due():
        loop_id = str(item.get("id") or "")
        prompt = str(item.get("prompt") or "").strip()
        if not loop_id or not prompt:
            continue
        updated = core.loops.mark_fired(loop_id)
        if updated is None:
            continue
        core.events.append(
            "loop_fired",
            {"id": loop_id, "next_fire_at": updated.get("next_fire_at")},
        )
        command = [
            PYTHON,
            str(TURN_RUNNER),
            "--session",
            core.session_id,
            "--loop-id",
            loop_id,
            "--prompt",
            prompt,
        ]
        try:
            result = subprocess.run(
                command,
                cwd=str(WORKSPACE),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=TURN_TIMEOUT,
                env=os.environ.copy(),
            )
            core.events.append(
                "loop_runner_result",
                {
                    "id": loop_id,
                    "returncode": result.returncode,
                    "output_digest": __import__("hashlib").sha256(
                        result.stdout.encode("utf-8", errors="replace")
                    ).hexdigest(),
                },
            )
        except subprocess.TimeoutExpired:
            core.events.append("loop_runner_timeout", {"id": loop_id, "timeout": TURN_TIMEOUT})
        except OSError as exc:
            core.events.append("loop_runner_error", {"id": loop_id, "error": type(exc).__name__})


def main() -> int:
    CONTROL_ROOT.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while RUNNING:
        for session_id in session_ids():
            try:
                run_due(GoarVibeCore(CONTROL_ROOT, WORKSPACE, session_id, owner="loopd"))
            except Exception as exc:
                # A bad session record must not stop schedules for every other session.
                print(f"goar-loopd: session {session_id}: {type(exc).__name__}: {exc}", file=sys.stderr)
        time.sleep(POLL_SECONDS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
