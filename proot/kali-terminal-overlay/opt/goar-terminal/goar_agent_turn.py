#!/usr/bin/env python3
"""Run one bounded VibeHack/GOAR turn under durable control-plane ownership."""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
from pathlib import Path

from goar_vibe_core import GoarVibeCore


def control_root() -> Path:
    return Path(os.getenv("GOAR_CONTROL_ROOT", "/data/goar/control"))


def workspace() -> Path:
    return Path(os.getenv("GOAR_WORKSPACE", "/data/workspace"))


def load_repl(session_id: str):
    from vibehack.config import cfg
    from vibehack.llm.provider import Finding
    from vibehack.agent.knowledge import KnowledgeState
    from vibehack.repl import VibehackREPL
    from vibehack.session.persistence import load_session

    state = load_session(session_id) or {}
    repl = VibehackREPL(
        target=state.get("target") or None,
        op_mode=state.get("op_mode", "agent"),
        persona=state.get("persona", "dev-safe"),
        unchained=bool(state.get("unchained", False)),
        no_memory=False,
        api_key=cfg.API_KEY,
    )
    repl.session_id = session_id
    repl.history = list(state.get("history", []))
    repl.key_findings = [Finding(**item) for item in state.get("findings", [])]
    repl.knowledge = KnowledgeState.from_dict(state.get("knowledge", {}))
    repl.auto_allow = True
    repl._system_built = bool(repl.history and repl.history[0].get("role") == "system")
    return repl


async def run_turn(session_id: str, prompt: str, *, loop_id: str | None = None) -> int:
    from vibehack.config import cfg
    from vibehack.core.repl.logic import process_llm_turn

    root = control_root()
    work = workspace()
    root.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    core = GoarVibeCore(root, work, session_id, owner="loop-" + secrets.token_hex(6))
    acquired, detail = core.acquire()
    if not acquired:
        core.events.append("loop_skipped", {"loop_id": loop_id, "reason": detail})
        print(detail, file=sys.stderr)
        return 3

    turn_id = "turn_" + secrets.token_hex(6)
    try:
        decision, config = core.before_turn(
            profile=str(core.session_config().get("profile", "operator")),
            turns=0,
            max_turns=cfg.MAX_TURN_MEMORY,
            tokens=0,
            token_budget=0,
            compact_threshold=0,
            history_size=0,
        )
        if decision.action == "stop":
            core.events.append("loop_stopped", {"loop_id": loop_id, "reason": decision.reason})
            print(decision.message, file=sys.stderr)
            return 4

        effective_prompt = prompt
        if decision.action == "inject" and decision.message:
            effective_prompt = f"{decision.message}\n\n{prompt}"
        core.begin_turn(turn_id)
        core.events.append(
            "loop_turn_started",
            {"loop_id": loop_id, "turn_id": turn_id, "config": config.fingerprint},
        )
        repl = load_repl(session_id)
        repl.history.append(
            {
                "role": "system",
                "content": "[GOAR LOOP TURN] This is a bounded scheduled turn. Complete only the current loop objective, preserve checkpoints, and stop when the objective is complete or blocked.",
            }
        )
        await process_llm_turn(repl, effective_prompt)
        repl._persist()
        core.seal_turn("loop_turn")
        core.events.append("loop_turn_completed", {"loop_id": loop_id, "turn_id": turn_id})
        return 0
    except Exception as exc:
        core.events.append(
            "loop_turn_failed",
            {"loop_id": loop_id, "turn_id": turn_id, "error": f"{type(exc).__name__}: {exc}"[:2000]},
        )
        try:
            core.seal_turn("loop_turn_failed")
        except Exception:
            pass
        print(f"GOAR loop turn failed: {exc}", file=sys.stderr)
        return 1
    finally:
        core.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one durable GOAR/VibeHack turn")
    parser.add_argument("--session", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--loop-id")
    args = parser.parse_args(argv)
    return asyncio.run(run_turn(args.session, args.prompt, loop_id=args.loop_id))


if __name__ == "__main__":
    raise SystemExit(main())
