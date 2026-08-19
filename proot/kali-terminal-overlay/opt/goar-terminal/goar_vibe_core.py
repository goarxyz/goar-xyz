"""GOAR's local Vibe-style control plane.

This module deliberately uses only the Python standard library so it remains
inside the Android Alpine rootfs.  It adapts public architectural concepts from
Mistral Vibe core (Apache-2.0) without importing its cloud, terminal UI, or
model-specific system-prompt dependencies.  GOAR's own system prompt remains
owned by goar.py.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import os
import re
import secrets
import threading
import time


CORE_VERSION = "goar-vibe-core/1"
MIN_LOOP_SECONDS = 30
MAX_LOOPS_PER_SESSION = 50
_MAX_SNAPSHOT_BYTES = 512 * 1024
_INTERVAL = re.compile(r"^(\d+)([smhd])$")


def _atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _digest(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8", errors="replace")
    return sha256(value).hexdigest()


def _now() -> float:
    return time.time()


@dataclass(frozen=True)
class ConfigLayer:
    name: str
    values: dict[str, Any]
    trusted: bool = True


@dataclass(frozen=True)
class ResolvedConfig:
    values: dict[str, Any]
    origins: dict[str, str]
    fingerprint: str


class GoarConfigResolver:
    """Last-trusted-layer-wins resolver with origin and fingerprint metadata."""

    def __init__(self, allowed_keys: Iterable[str]) -> None:
        self.allowed_keys = frozenset(allowed_keys)

    def resolve(self, layers: Iterable[ConfigLayer]) -> ResolvedConfig:
        values: dict[str, Any] = {}
        origins: dict[str, str] = {}
        for layer in layers:
            if not layer.trusted:
                continue
            for key, value in layer.values.items():
                if key not in self.allowed_keys:
                    continue
                values[key] = value
                origins[key] = layer.name
        material = json.dumps({"values": values, "origins": origins}, sort_keys=True, default=str)
        return ResolvedConfig(values=values, origins=origins, fingerprint=_digest(material))


@dataclass
class MiddlewareDecision:
    action: str = "continue"  # continue, stop, compact, inject
    reason: str = ""
    message: str = ""


class GoarMiddlewarePipeline:
    """Deterministic before-turn guardrail pipeline."""

    def before_turn(
        self,
        *,
        profile: str,
        turn_count: int,
        max_turns: int,
        token_count: int,
        token_budget: int,
        context_threshold: int,
        history_size: int,
        plan_state: str | None,
    ) -> MiddlewareDecision:
        if max_turns > 0 and turn_count >= max_turns:
            return MiddlewareDecision("stop", "turn_limit", "Agent turn limit reached for this session.")
        if token_budget > 0 and token_count >= token_budget:
            return MiddlewareDecision("stop", "token_budget", "Session token budget reached; compact or start a new session.")
        if context_threshold > 0 and token_count >= context_threshold and history_size > 4:
            return MiddlewareDecision("compact", "context_threshold", "Session context threshold reached; compacting safely before the next model call.")
        if profile == "plan" and plan_state in {None, "draft"}:
            return MiddlewareDecision(
                "inject",
                "plan_mode",
                "[GOAR PLAN MODE] Research and write/update the durable plan. Do not make workspace changes until the plan is approved.",
            )
        return MiddlewareDecision()


@dataclass
class SessionLease:
    session_id: str
    owner: str
    expires_at: float


class SessionLeaseStore:
    def __init__(self, root: Path) -> None:
        self.root = root / "leases"
        self._lock = threading.Lock()

    def _path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.json"

    def acquire(self, session_id: str, owner: str, ttl_seconds: int = 180) -> tuple[bool, SessionLease | None]:
        with self._lock:
            path = self._path(session_id)
            current = _load_json(path, {})
            now = _now()
            current_owner = str(current.get("owner") or "")
            current_expiry = float(current.get("expires_at") or 0)
            if current_owner and current_owner != owner and current_expiry > now:
                return False, SessionLease(session_id, current_owner, current_expiry)
            lease = SessionLease(session_id, owner, now + max(30, ttl_seconds))
            _atomic_json(path, asdict(lease))
            return True, lease

    def release(self, session_id: str, owner: str) -> None:
        with self._lock:
            path = self._path(session_id)
            current = _load_json(path, {})
            if current.get("owner") == owner:
                path.unlink(missing_ok=True)


@dataclass
class PlanStep:
    id: str
    description: str
    status: str = "pending"
    note: str = ""
    updated_at: float = field(default_factory=_now)


@dataclass
class PlanRecord:
    id: str
    session_id: str
    title: str
    state: str
    created_at: float
    updated_at: float
    steps: list[PlanStep] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "title": self.title,
            "state": self.state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [asdict(step) for step in self.steps],
            "events": list(self.events),
        }


class GoarPlanSession:
    _TRANSITIONS = {
        "draft": {"approved", "cancelled"},
        "approved": {"executing", "cancelled"},
        "executing": {"completed", "blocked", "cancelled"},
        "blocked": {"executing", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }

    def __init__(self, root: Path, session_id: str) -> None:
        self.path = root / "plans" / f"{session_id}.json"
        self.session_id = session_id

    def load(self) -> PlanRecord | None:
        raw = _load_json(self.path, None)
        if not isinstance(raw, dict) or not raw.get("id"):
            return None
        return PlanRecord(
            id=str(raw["id"]), session_id=str(raw.get("session_id") or self.session_id),
            title=str(raw.get("title") or "GOAR plan"), state=str(raw.get("state") or "draft"),
            created_at=float(raw.get("created_at") or _now()), updated_at=float(raw.get("updated_at") or _now()),
            steps=[PlanStep(**step) for step in raw.get("steps", []) if isinstance(step, dict)],
            events=list(raw.get("events", [])),
        )

    def create(self, title: str, steps: Iterable[str]) -> PlanRecord:
        now = _now()
        record = PlanRecord(
            id="plan_" + secrets.token_hex(6), session_id=self.session_id,
            title=title.strip() or "GOAR plan", state="draft", created_at=now, updated_at=now,
            steps=[PlanStep(id=f"step_{index + 1}", description=text.strip()) for index, text in enumerate(steps) if text.strip()],
        )
        self._event(record, "created", {"step_count": len(record.steps)})
        self._save(record)
        return record

    def transition(self, state: str, note: str = "") -> PlanRecord:
        record = self.load()
        if record is None:
            raise ValueError("No plan exists for this session")
        if state not in self._TRANSITIONS.get(record.state, set()):
            raise ValueError(f"Invalid plan transition: {record.state} -> {state}")
        record.state = state
        record.updated_at = _now()
        self._event(record, "state", {"state": state, "note": note[:2000]})
        self._save(record)
        return record

    def update_step(self, step_id: str, status: str, note: str = "") -> PlanRecord:
        record = self.load()
        if record is None:
            raise ValueError("No plan exists for this session")
        if status not in {"pending", "running", "completed", "blocked", "skipped"}:
            raise ValueError("Invalid plan step status")
        step = next((item for item in record.steps if item.id == step_id), None)
        if step is None:
            raise ValueError("Unknown plan step")
        step.status, step.note, step.updated_at = status, note[:4000], _now()
        record.updated_at = _now()
        self._event(record, "step", {"id": step_id, "status": status, "note": step.note})
        self._save(record)
        return record

    def _event(self, record: PlanRecord, kind: str, detail: dict[str, Any]) -> None:
        record.events.append({"at": _now(), "kind": kind, "detail": detail})
        record.events = record.events[-500:]

    def _save(self, record: PlanRecord) -> None:
        _atomic_json(self.path, record.to_dict())


@dataclass
class FileChange:
    path: str
    before_digest: str | None
    after_digest: str | None
    before_text: str | None = None
    after_text: str | None = None


class GoarCheckpointLedger:
    """Append-only per-turn file digest ledger with bounded snapshot payloads."""

    def __init__(self, root: Path, workspace: Path, session_id: str) -> None:
        self.workspace = workspace.resolve()
        self.path = root / "checkpoints" / f"{session_id}.json"
        self._open: dict[str, Any] | None = None

    def begin(self, turn_id: str) -> None:
        if self._open is not None:
            raise RuntimeError("checkpoint turn already open")
        self._open = {"turn_id": turn_id, "started_at": _now(), "changes": {}}

    def capture_before(self, path: str) -> None:
        safe = self._safe_path(path)
        if self._open is None:
            return
        key = str(safe.relative_to(self.workspace))
        self._open["changes"].setdefault(key, {"before": self._file_state(safe), "after": None})

    def capture_after(self, path: str) -> None:
        safe = self._safe_path(path)
        if self._open is None:
            return
        key = str(safe.relative_to(self.workspace))
        row = self._open["changes"].setdefault(key, {"before": None, "after": None})
        row["after"] = self._file_state(safe)

    def seal(self, label: str = "agent_turn") -> dict[str, Any] | None:
        if self._open is None:
            return None
        open_turn, self._open = self._open, None
        changes: list[dict[str, Any]] = []
        for path, item in open_turn["changes"].items():
            before, after = item.get("before"), item.get("after")
            if before != after:
                changes.append({"path": path, "before": before, "after": after})
        record = {"id": "checkpoint_" + secrets.token_hex(6), "at": _now(), "label": label, "turn_id": open_turn["turn_id"], "changes": changes}
        data = _load_json(self.path, {"events": []})
        data.setdefault("events", []).append(record)
        data["events"] = data["events"][-250:]
        _atomic_json(self.path, data)
        return record

    def events(self) -> list[dict[str, Any]]:
        return list(_load_json(self.path, {"events": []}).get("events", []))

    def review(self, checkpoint_id: str, decision: str) -> dict[str, Any]:
        """Record keep/revert and materialize a safe file-level revert when requested.

        Large files remain digest-only and cannot be automatically restored; the
        resulting structured error keeps the decision ledger truthful.
        """
        if decision not in {"keep", "revert"}:
            raise ValueError("decision must be keep or revert")
        data = _load_json(self.path, {"events": [], "reviews": []})
        event = next((item for item in data.get("events", []) if item.get("id") == checkpoint_id), None)
        if event is None:
            raise ValueError("checkpoint not found")
        restored: list[str] = []
        if decision == "revert":
            for change in reversed(event.get("changes") or []):
                target = self._safe_path(str(change.get("path") or ""))
                before = change.get("before")
                if before is None:
                    target.unlink(missing_ok=True)
                    restored.append(str(target.relative_to(self.workspace)))
                    continue
                if not isinstance(before, dict) or "text" not in before:
                    raise ValueError(f"checkpoint {checkpoint_id} cannot restore {change.get('path')}: no bounded text snapshot")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(before["text"]), encoding="utf-8")
                restored.append(str(target.relative_to(self.workspace)))
        review = {"id": "review_" + secrets.token_hex(5), "at": _now(), "checkpoint_id": checkpoint_id, "decision": decision, "restored": restored}
        data.setdefault("reviews", []).append(review)
        data["reviews"] = data["reviews"][-500:]
        _atomic_json(self.path, data)
        return review

    def reviews(self) -> list[dict[str, Any]]:
        return list(_load_json(self.path, {"reviews": []}).get("reviews", []))

    def _safe_path(self, path: str) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = candidate.resolve(strict=False)
        if resolved != self.workspace and self.workspace not in resolved.parents:
            raise ValueError("Checkpoint path escapes trusted workspace")
        return resolved

    @staticmethod
    def _file_state(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            data = path.read_bytes()
        except OSError:
            return None
        item: dict[str, Any] = {"digest": _digest(data), "bytes": len(data)}
        if len(data) <= _MAX_SNAPSHOT_BYTES:
            item["text"] = data.decode("utf-8", errors="replace")
        return item


class WorkspaceTrustStore:
    def __init__(self, root: Path, default_workspace: Path) -> None:
        self.path = root / "workspace_trust.json"
        self.default_workspace = default_workspace.resolve()

    def roots(self) -> list[Path]:
        raw = _load_json(self.path, {"roots": [str(self.default_workspace)]})
        candidates = raw.get("roots") if isinstance(raw, dict) else []
        roots: list[Path] = []
        for item in candidates or [str(self.default_workspace)]:
            try:
                roots.append(Path(str(item)).resolve())
            except OSError:
                continue
        return roots or [self.default_workspace]

    def trust(self, path: str) -> list[str]:
        root = Path(path).resolve()
        current = {str(item) for item in self.roots()}
        current.add(str(root))
        _atomic_json(self.path, {"roots": sorted(current)})
        return sorted(current)

    def revoke(self, path: str) -> list[str]:
        root = str(Path(path).resolve())
        current = {str(item) for item in self.roots()}
        current.discard(root)
        current.add(str(self.default_workspace))
        _atomic_json(self.path, {"roots": sorted(current)})
        return sorted(current)

    def allows(self, path: str) -> bool:
        candidate = Path(path).resolve(strict=False)
        return any(candidate == root or root in candidate.parents for root in self.roots())


class GoarHookRegistry:
    """Trusted in-process lifecycle hooks with isolated failures and bounded output."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[[dict[str, Any]], Any]]] = {"pre_tool": [], "post_tool": [], "post_agent": []}

    def register(self, event: str, hook: Callable[[dict[str, Any]], Any]) -> None:
        if event not in self._hooks:
            raise ValueError("Unknown hook event")
        self._hooks[event].append(hook)

    def dispatch(self, event: str, payload: dict[str, Any]) -> list[str]:
        notices: list[str] = []
        for hook in self._hooks.get(event, []):
            try:
                result = hook(dict(payload))
                if result:
                    notices.append(str(result)[:1000])
            except Exception as exc:  # Hooks are observational and must not break GOAR.
                notices.append(f"hook_error:{type(exc).__name__}")
        return notices


class GoarLoopManager:
    def __init__(self, root: Path, session_id: str) -> None:
        self.path = root / "loops" / f"{session_id}.json"

    @staticmethod
    def parse_interval(value: str) -> int:
        match = _INTERVAL.fullmatch(value.strip().lower())
        if not match:
            raise ValueError("Interval must be <number><s|m|h|d>")
        seconds = int(match.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]
        if seconds < MIN_LOOP_SECONDS:
            raise ValueError(f"Interval must be at least {MIN_LOOP_SECONDS}s")
        return seconds

    def list(self) -> list[dict[str, Any]]:
        return list(_load_json(self.path, {"loops": []}).get("loops", []))

    def create(self, interval: str, prompt: str) -> dict[str, Any]:
        seconds = self.parse_interval(interval)
        prompt = prompt.strip()
        if not prompt or prompt.startswith("/"):
            raise ValueError("Loop prompt must be non-empty and cannot start with '/'")
        loops = self.list()
        if len(loops) >= MAX_LOOPS_PER_SESSION:
            raise ValueError(f"Loop limit reached ({MAX_LOOPS_PER_SESSION})")
        now = _now()
        item = {"id": "loop_" + secrets.token_hex(4), "interval_seconds": seconds, "prompt": prompt, "created_at": now, "next_fire_at": now + seconds}
        loops.append(item)
        _atomic_json(self.path, {"loops": loops})
        return item

    def due(self, now: float | None = None) -> list[dict[str, Any]]:
        current = _now() if now is None else now
        return [item for item in self.list() if float(item.get("next_fire_at") or 0) <= current]

    def mark_fired(self, loop_id: str, now: float | None = None) -> dict[str, Any] | None:
        current = _now() if now is None else now
        loops = self.list()
        found = None
        for item in loops:
            if item.get("id") == loop_id:
                item["next_fire_at"] = current + int(item["interval_seconds"])
                found = item
                break
        _atomic_json(self.path, {"loops": loops})
        return found

    def delete(self, loop_id: str) -> bool:
        loops = self.list()
        kept = [item for item in loops if item.get("id") != loop_id]
        _atomic_json(self.path, {"loops": kept})
        return len(kept) != len(loops)


class GoarCoreEventLog:
    def __init__(self, root: Path, session_id: str) -> None:
        self.path = root / "events" / f"{session_id}.jsonl"
        self._lock = threading.Lock()

    def append(self, kind: str, detail: dict[str, Any]) -> dict[str, Any]:
        event = {"id": "evt_" + secrets.token_hex(6), "at": _now(), "kind": kind, "detail": detail}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def read(self, after: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        try:
            rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, ValueError):
            rows = []
        if after:
            for index, item in enumerate(rows):
                if item.get("id") == after:
                    rows = rows[index + 1:]
                    break
        return rows[-max(1, min(limit, 1000)):]


class GoarVibeCore:
    """Session-scoped facade used by GOAR's live agent loop and local APIs."""

    ALLOWED_CONFIG = frozenset({"max_turns", "token_budget", "compact_threshold", "profile", "plan_required", "workspace_roots"})

    def __init__(self, root: Path, workspace: Path, session_id: str, owner: str | None = None) -> None:
        self.root = root
        self.workspace = workspace.resolve()
        self.session_id = session_id
        self.owner = owner or "goar-" + secrets.token_hex(6)
        self.config = GoarConfigResolver(self.ALLOWED_CONFIG)
        self.leases = SessionLeaseStore(root)
        self.trust = WorkspaceTrustStore(root, self.workspace)
        self.hooks = GoarHookRegistry()
        self._open_checkpoint: GoarCheckpointLedger | None = None
        self._bind(session_id)

    def _bind(self, session_id: str) -> None:
        self.session_id = session_id
        self.plan = GoarPlanSession(self.root, session_id)
        self.ledger = GoarCheckpointLedger(self.root, self.workspace, session_id)
        self.loops = GoarLoopManager(self.root, session_id)
        self.events = GoarCoreEventLog(self.root, session_id)

    def bind_session(self, session_id: str) -> None:
        if session_id != self.session_id:
            self._bind(session_id)

    @property
    def _config_path(self) -> Path:
        return self.root / "config" / f"{self.session_id}.json"

    def session_config(self) -> dict[str, Any]:
        raw = _load_json(self._config_path, {})
        return {key: value for key, value in raw.items() if key in self.ALLOWED_CONFIG} if isinstance(raw, dict) else {}

    def update_session_config(self, values: dict[str, Any]) -> dict[str, Any]:
        current = self.session_config()
        for key, value in values.items():
            if key not in self.ALLOWED_CONFIG:
                raise ValueError(f"unknown config key: {key}")
            if key in {"max_turns", "token_budget", "compact_threshold"}:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{key} must be an integer")
                if value < 0:
                    raise ValueError(f"{key} must be non-negative")
            if key == "profile" and value not in {"operator", "plan", "accept-edits", "explore"}:
                raise ValueError("profile is invalid")
            current[key] = value
        _atomic_json(self._config_path, current)
        self.events.append("config_updated", {"keys": sorted(values)})
        return current

    def resolve_config(self, *, profile: str, max_turns: int, token_budget: int, compact_threshold: int) -> ResolvedConfig:
        return self.config.resolve([
            ConfigLayer("defaults", {"profile": "operator", "max_turns": max_turns, "token_budget": token_budget, "compact_threshold": compact_threshold, "workspace_roots": [str(self.workspace)]}),
            ConfigLayer("trusted_workspace", {"workspace_roots": [str(item) for item in self.trust.roots()]}),
            ConfigLayer("session", {"profile": profile}),
            ConfigLayer("session_override", self.session_config()),
        ])

    def acquire(self) -> tuple[bool, str]:
        ok, existing = self.leases.acquire(self.session_id, self.owner)
        if ok:
            self.events.append("session_lease_acquired", {"owner": self.owner})
            return True, ""
        assert existing is not None
        return False, f"Session is active in another GOAR runtime until {existing.expires_at:.0f}."

    def release(self) -> None:
        self.leases.release(self.session_id, self.owner)
        self.events.append("session_lease_released", {"owner": self.owner})

    def before_turn(self, *, profile: str, turns: int, max_turns: int, tokens: int, token_budget: int, compact_threshold: int, history_size: int) -> tuple[MiddlewareDecision, ResolvedConfig]:
        config = self.resolve_config(profile=profile, max_turns=max_turns, token_budget=token_budget, compact_threshold=compact_threshold)
        plan = self.plan.load()
        decision = GoarMiddlewarePipeline().before_turn(
            profile=profile, turn_count=turns, max_turns=int(config.values.get("max_turns") or max_turns),
            token_count=tokens, token_budget=int(config.values.get("token_budget") or token_budget),
            context_threshold=int(config.values.get("compact_threshold") or compact_threshold),
            history_size=history_size, plan_state=plan.state if plan else None,
        )
        self.events.append("middleware", {"action": decision.action, "reason": decision.reason, "config": config.fingerprint})
        return decision, config

    def begin_turn(self, turn_id: str) -> None:
        self.ledger.begin(turn_id)
        self.events.append("turn_started", {"turn_id": turn_id})

    def record_tool(self, name: str, args: dict[str, Any], result: str | None = None) -> None:
        self.events.append("tool_result" if result is not None else "tool_call", {
            "name": name, "args_digest": _digest(json.dumps(args, sort_keys=True, default=str)),
            "result_digest": _digest(result) if result is not None else None,
        })

    def capture_workspace_arg(self, args: dict[str, Any], after: bool = False) -> None:
        for value in args.values():
            if not isinstance(value, str):
                continue
            try:
                if self.trust.allows(value):
                    (self.ledger.capture_after if after else self.ledger.capture_before)(value)
            except (OSError, ValueError):
                continue

    def seal_turn(self, label: str = "agent_turn") -> None:
        checkpoint = self.ledger.seal(label)
        if checkpoint is not None:
            self.events.append("checkpoint", {"id": checkpoint["id"], "changes": len(checkpoint["changes"])})
        self.hooks.dispatch("post_agent", {"session_id": self.session_id, "checkpoint": checkpoint})

    def status(self) -> dict[str, Any]:
        plan = self.plan.load()
        return {
            "version": CORE_VERSION,
            "session_id": self.session_id,
            "trusted_roots": [str(item) for item in self.trust.roots()],
            "plan": plan.to_dict() if plan else None,
            "loops": self.loops.list(),
            "checkpoint_count": len(self.ledger.events()),
            "event_count": len(self.events.read(limit=1000)),
        }
