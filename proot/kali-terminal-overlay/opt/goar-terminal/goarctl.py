#!/usr/bin/env python3
"""Terminal control surface for GOAR's durable local Vibe-style state."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from goar_vibe_core import GoarVibeCore


CONTROL_ROOT = Path(os.getenv("GOAR_CONTROL_ROOT", "/data/goar/control"))
WORKSPACE = Path(os.getenv("GOAR_WORKSPACE", "/data/workspace"))
DEFAULT_SESSION = os.getenv("GOAR_SESSION_ID", "terminal")


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def core_for(session_id: str) -> GoarVibeCore:
    CONTROL_ROOT.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    return GoarVibeCore(CONTROL_ROOT, WORKSPACE, session_id)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="goarctl", description="GOAR terminal control plane")
    root.add_argument("--session", default=DEFAULT_SESSION, help="Durable session identifier")
    sub = root.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("events").add_argument("--limit", type=int, default=100)

    config = sub.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("show")
    config_set = config_sub.add_parser("set")
    config_set.add_argument("key")
    config_set.add_argument("value")

    trust = sub.add_parser("trust")
    trust_sub = trust.add_subparsers(dest="trust_command", required=True)
    trust_sub.add_parser("list")
    trust_add = trust_sub.add_parser("add")
    trust_add.add_argument("path")
    trust_remove = trust_sub.add_parser("remove")
    trust_remove.add_argument("path")

    plan = sub.add_parser("plan")
    plan_sub = plan.add_subparsers(dest="plan_command", required=True)
    plan_sub.add_parser("show")
    plan_create = plan_sub.add_parser("create")
    plan_create.add_argument("title")
    plan_create.add_argument("steps", nargs="+", help="One or more plan steps")
    for name, state in (("approve", "approved"), ("start", "executing"), ("complete", "completed"), ("block", "blocked"), ("cancel", "cancelled")):
        item = plan_sub.add_parser(name)
        item.set_defaults(plan_state=state)
        item.add_argument("--note", default="")
    plan_step = plan_sub.add_parser("step")
    plan_step.add_argument("id")
    plan_step.add_argument("status", choices=("pending", "running", "completed", "blocked", "skipped"))
    plan_step.add_argument("--note", default="")

    checkpoint = sub.add_parser("checkpoint")
    check_sub = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    check_sub.add_parser("list")
    review = check_sub.add_parser("review")
    review.add_argument("id")
    review.add_argument("decision", choices=("keep", "revert"))

    loop = sub.add_parser("loop")
    loop_sub = loop.add_subparsers(dest="loop_command", required=True)
    loop_sub.add_parser("list")
    loop_add = loop_sub.add_parser("add")
    loop_add.add_argument("interval", help="Minimum 30s; e.g. 30s, 5m, 1h")
    loop_add.add_argument("prompt")
    loop_remove = loop_sub.add_parser("remove")
    loop_remove.add_argument("id")
    return root


def parse_value(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    core = core_for(args.session)

    try:
        if args.command == "status":
            emit(core.status())
            return 0
        if args.command == "events":
            emit(core.events.read(limit=args.limit))
            return 0
        if args.command == "config":
            if args.config_command == "show":
                emit(core.session_config())
            else:
                emit(core.update_session_config({args.key: parse_value(args.value)}))
            return 0
        if args.command == "trust":
            if args.trust_command == "list":
                emit({"roots": [str(path) for path in core.trust.roots()]})
            elif args.trust_command == "add":
                emit({"roots": core.trust.trust(args.path)})
            else:
                emit({"roots": core.trust.revoke(args.path)})
            return 0
        if args.command == "plan":
            if args.plan_command == "show":
                record = core.plan.load()
                emit(record.to_dict() if record else None)
            elif args.plan_command == "create":
                emit(core.plan.create(args.title, args.steps).to_dict())
            elif args.plan_command == "step":
                emit(core.plan.update_step(args.id, args.status, args.note).to_dict())
            else:
                emit(core.plan.transition(args.plan_state, args.note).to_dict())
            return 0
        if args.command == "checkpoint":
            if args.checkpoint_command == "list":
                emit({"events": core.ledger.events(), "reviews": core.ledger.reviews()})
            else:
                emit(core.ledger.review(args.id, args.decision))
            return 0
        if args.command == "loop":
            if args.loop_command == "list":
                emit({"loops": core.loops.list()})
            elif args.loop_command == "add":
                item = core.loops.create(args.interval, args.prompt)
                core.events.append("loop_created", {"id": item["id"], "interval_seconds": item["interval_seconds"]})
                emit(item)
            else:
                removed = core.loops.delete(args.id)
                core.events.append("loop_deleted", {"id": args.id, "removed": removed})
                emit({"removed": removed})
            return 0
    except (OSError, ValueError) as exc:
        print(f"goarctl: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
