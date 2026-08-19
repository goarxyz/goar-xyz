# Full Mistral Vibe Core Integration Architecture for GOAR

## Scope and Preservation Rule

GOAR will retain its existing **GOAR system prompt, identity, provider wiring, local browser automation, workspace APIs, and Android-contained deployment model**. The integration objective is to replace the ad hoc control-plane behavior around that prompt with the durable, inspectable execution architecture demonstrated by Mistral Vibe core. The referenced project is licensed under Apache License 2.0; any directly adapted source must retain attribution and the license notice. [1]

The integration is not limited to the existing GOAR operator-profile addition. It covers configuration layers, session lifecycle, planning, compaction, checkpoints and review, permissions, workspace trust, hooks, subagents, scheduling, and observable runtime state.

## Component Inventory and GOAR Target

| Mistral Vibe core family | Vibe design principle | GOAR target implementation | Acceptance evidence |
|---|---|---|---|
| Layered configuration | Immutable resolved configuration from ordered, validated layers | `GoarConfigResolver` with defaults, app/user state, workspace policy, session override, and request override layers; resolved values carry origin metadata | Conflicting layers resolve deterministically; invalid or untrusted values are rejected without mutating active state |
| Session lifecycle | Durable session metadata, lease ownership, title, history, and resume semantics | `GoarSessionCore` extends existing `SessionStore` with atomic session manifest, lease token, plan state, active profile, counters, loops, and compatibility migration | Create, resume, lock conflict, expiry, migration, and restart recovery tests |
| Plan session | A named plan is separate from an implementation turn and is persisted | `GoarPlanSession` with explicit draft/approved/executing/completed states, ordered plan steps, and append-only status events | Plan cannot execute before approval; step events survive restart; plan APIs return a stable projection |
| Context compaction | Compact a copy of history; only append a replacement boundary after a valid summary | `GoarCompactionManager` wraps the existing summary provider with snapshot, validation, rollback, retry, source range, and compaction event metadata | Empty/tool-call/overflow summary failures leave live history unchanged; successful compaction is replayable |
| Middleware pipeline | Before-turn policies can continue, inject context, stop, or compact | `GoarMiddlewarePipeline` performs profile, plan-mode, turn-budget, tool-budget, token-budget, compaction, checkpoint, and workspace-trust decisions before each agent turn | Ordered actions and injected notices are deterministic; terminal decisions block provider calls |
| Checkpoints and review | Append-only file-change event log, manual-drift reconciliation, review decisions, and dependency-safe revert | `GoarCheckpointLedger` supplements existing session snapshots and git checkpointing with per-turn file digests, change events, manual edits, keep/revert decision records, and restore projection | Changes can be listed, reviewed, kept, reverted, and reconciled without losing unrelated workspace state |
| Rewind | Turn-boundary truncation restores an earlier conversation/file projection | Existing rewind endpoint will be ledger-aware and records its reason and origin boundary | Rewind clears later events, restores selected projection, and maintains an auditable history |
| Profiles and permissions | Agent profile is a concrete tool policy, not prompt-only behavior | Existing GOAR `operator`, `plan`, `accept-edits`, and `explore` profiles become data-driven policy layers with request, session, and workspace overrides | Every model tool call is checked, denied calls are structured events, and defaults remain backward compatible |
| Managed shell and tools | Typed tool contracts, explicit approval semantics, safe workspace scope, and presentation events | `GoarToolPolicy` classifies read/edit/network/process/browser/secret/job actions; `GoarToolEvent` records policy, arguments digest, output digest, duration, and result status | Policy tests cover all registered tools; shell commands and path access are workspace-scoped under restrictive profiles |
| Trusted folders | Workspace trust is explicit and separate from tool identity | `GoarWorkspaceTrustStore` holds canonical workspace roots and trust grants; tools reject path traversal or untrusted roots | Trust grant/revoke, canonical-path, and symlink escape tests |
| Skills | Skills are discoverable, scoped instructions with controlled injection | Existing skills gain metadata validation, source/trust state, enablement per session, and deterministic prompt ordering | Malformed/untrusted skills are not injected; enabled skills restore across session resume |
| Hooks | Pre-tool, post-tool, and post-agent hooks are explicit lifecycle participants | `GoarHookRegistry` runs trusted hooks under a narrow event schema and rejects workspace-loaded executable hooks unless explicitly trusted | Hook order, timeout, failure isolation, and event redaction tests |
| Subagents | Specialized subagents have bounded turns, a scratchpad, streamed events, and accumulated result | Existing subagent capability becomes `GoarSubagentRunner` with profile, workspace/scratchpad, budget, parent event correlation, cancellation, and a structured final result | Subagent cannot exceed budget or escape inherited policy; parent receives result and tool stream summary |
| Scheduled loops | Session-scoped loops parse bounded intervals and persist next-fire state | `GoarLoopManager` stores recurring prompts in the durable session manifest and performs bounded local dispatch while the foreground runtime is alive | Interval parser, minimum interval, maximum loops, resume, and next-fire persistence tests |
| Scratchpad and worktrees | Temporary agent working state and project isolation are explicit | Session scratchpads live below app-private GOAR state; optional workspace snapshots receive checkpoint labels without changing the user-selected root | Scratchpad cleanup, path isolation, and checkpoint correspondence tests |
| Runtime events and observability | Event stream is the single source for tool, turn, compaction, plan, checkpoint, and subagent state | Existing GOAR events are normalized as `GoarCoreEvent` records, persisted as JSONL, and exposed as filtered session events | Event order, redaction, resume cursor, and retained-event-window tests |

## Integration Boundaries

The following Vibe-specific surfaces are intentionally not substituted for GOAR because they are not part of the requested local GOAR runtime: Mistral account authentication, Vibe cloud telemetry, Vibe product branding, Vibe terminal UI, remote teleport services, and its model-specific system prompt. GOAR will implement compatible local control-plane concepts rather than import those external service dependencies.

## Runtime Sequence

The final local agent turn follows this ordered sequence:

1. Resolve the immutable GOAR configuration from its layered sources and record its fingerprint.
2. Acquire the session lease, restore its profile, plan, loop state, and latest checkpoint projection.
3. Run the middleware pipeline. It can inject policy/plan context, stop the turn, request atomic compaction, or continue.
4. Open a checkpoint-ledger turn and capture trusted-workspace pre-state for files changed by tools.
5. Invoke the existing GOAR agent with the unchanged GOAR system prompt plus runtime policy context.
6. Apply tool policy and workspace trust before every tool call, emitting redacted lifecycle events.
7. Reconcile changed workspace files, seal the checkpoint turn, persist session metadata atomically, and dispatch trusted post-tool/post-agent hooks.
8. Publish the resulting session event cursor to the local GOAR UI and Android workspace.

## Required Test Matrix

| Area | Required tests |
|---|---|
| Configuration | precedence, origin metadata, malformed value rejection, immutable resolved snapshot |
| Session | atomic save, lease conflict, resume, migration, crash recovery |
| Plan | lifecycle transition guards, event persistence, execution gate |
| Middleware | order, stop, injection, compaction, profile and budget behavior |
| Compaction | snapshot isolation, successful boundary replacement, failed-summary rollback, retry on context overflow |
| Checkpoints | pre/post capture, manual drift, list, review decision, dependency-safe revert, rewind |
| Tools and trust | profile allowlist, path escape, trusted-root, secret redaction, hook isolation |
| Skills and subagents | validation, deterministic injection, inherited policy, scratchpad scope, cancellation, bounded result |
| Loops | interval validation, limit, persistence, due dispatch |
| Android/API | local API schema, noVNC start route, app-private state behavior, manifest integrity, extraction semantics |

## Attribution

This architecture is based on concepts and public source structure in Mistral Vibe core, including its layered configuration builder, append-only checkpoint model, atomic compaction manager, middleware pipeline, profile model, subagent contract, and loop manager. Direct source reuse, if introduced in a later implementation step, must carry the required Apache-2.0 notices. [1] [2] [3] [4] [5]

## References

[1] [Mistral Vibe Apache License 2.0](https://github.com/mistralai/mistral-vibe/blob/main/LICENSE)

[2] [Mistral Vibe core directory](https://github.com/mistralai/mistral-vibe/tree/main/vibe/core)

[3] [Mistral Vibe configuration builder](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/config/builder.py)

[4] [Mistral Vibe checkpoint ledger](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/checkpoints/checkpointer.py)

[5] [Mistral Vibe compaction manager](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/compaction/manager.py)
