"""Durable GOAR control-plane wrapper for interactive VibeHack terminal turns."""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Awaitable, Callable

from goar_vibe_core import GoarVibeCore


def _root() -> Path:
    return Path(os.getenv("GOAR_CONTROL_ROOT", "/data/goar/control"))


def _workspace() -> Path:
    return Path(os.getenv("GOAR_WORKSPACE", "/data/workspace"))


def _history_bytes(history: list[dict[str, Any]]) -> int:
    return sum(len(str(item.get("content") or "").encode("utf-8", errors="replace")) for item in history)


def _capture_workspace(core: GoarVibeCore, after: bool = False) -> None:
    """Bounded trusted-workspace snapshot for the per-turn checkpoint ledger."""
    count = 0
    for path in core.workspace.rglob("*"):
        if count >= 2000:
            core.events.append("checkpoint_scan_limited", {"files": count})
            break
        if not path.is_file() or not core.trust.allows(str(path)):
            continue
        (core.ledger.capture_after if after else core.ledger.capture_before)(str(path))
        count += 1


def _compact_history(repl: Any, core: GoarVibeCore) -> None:
    """Deterministic, atomic local compaction; never mutates history on failure."""
    original = list(repl.history)
    try:
        system = original[:1] if original and original[0].get("role") == "system" else []
        tail = original[-10:]
        discarded = original[len(system):max(len(system), len(original) - len(tail))]
        summary = "[GOAR CONTEXT COMPACTION] " + str(len(discarded)) + " earlier messages compacted locally. "
        summary += "Their detailed content remains in the durable VibeHack session record; continue from the retained recent context."
        repl.history = system + [{"role": "system", "content": summary}] + tail
        core.events.append("history_compacted", {"discarded": len(discarded), "retained": len(repl.history)})
    except Exception:
        repl.history = original
        core.events.append("history_compaction_failed", {})


async def run_interactive_turn(repl: Any, prompt: str, processor: Callable[[Any, str], Awaitable[None]]) -> bool:
    """Run exactly one interactive agent turn under the GOAR durable facade."""
    root, workspace = _root(), _workspace()
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    core = GoarVibeCore(root, workspace, repl.session_id, owner="interactive-" + secrets.token_hex(6))
    acquired, detail = core.acquire()
    if not acquired:
        from vibehack.ui.tui import log_to_pane
        log_to_pane(repl, "logs", "GOAR LEASE: " + detail)
        return False
    turn_id = "turn_" + secrets.token_hex(6)
    started = False
    try:
        from vibehack.config import cfg
        decision, config = core.before_turn(
            profile=str(core.session_config().get("profile", "operator")),
            turns=max(0, len(repl.history) // 2),
            max_turns=int(getattr(cfg, "MAX_TURN_MEMORY", 10)),
            tokens=_history_bytes(repl.history),
            token_budget=0,
            compact_threshold=int(core.session_config().get("compact_threshold", 0) or 0),
            history_size=len(repl.history),
        )
        if decision.action == "stop":
            from vibehack.ui.tui import log_to_pane
            log_to_pane(repl, "logs", "GOAR MIDDLEWARE: " + decision.message)
            return False
        if decision.action == "compact":
            _compact_history(repl, core)
        effective_prompt = (decision.message + "\n\n" + prompt) if decision.action == "inject" and decision.message else prompt
        core.begin_turn(turn_id)
        _capture_workspace(core, after=False)
        started = True
        core.events.append("interactive_turn_started", {"turn_id": turn_id, "config": config.fingerprint})
        repl._goar_core = core
        await processor(repl, effective_prompt)
        _capture_workspace(core, after=True)
        core.events.append("interactive_turn_completed", {"turn_id": turn_id})
        return True
    except Exception as exc:
        core.events.append("interactive_turn_failed", {"turn_id": turn_id, "error": (type(exc).__name__ + ": " + str(exc))[:2000]})
        raise
    finally:
        try:
            if started:
                core.seal_turn("interactive_turn")
        finally:
            if getattr(repl, "_goar_core", None) is core:
                delattr(repl, "_goar_core")
            core.release()
