# GOAR Core Adaptation: Mistral Vibe-Inspired Local Operator Architecture

## Purpose

GOAR already contains durable sessions, task journals, jobs with checkpoint and retry state, automatic history compaction, skill discovery, subagents, git checkpoints, and local browser automation. The goal is therefore **not** to replace GOAR with Mistral Vibe or copy its implementation. The goal is to adopt the parts of its core design that make a local Android operator safer, clearer, and more recoverable while preserving the complete GOAR backend.

## Reference Patterns

Mistral Vibe separates named agent profiles from the agent loop and applies concrete tool-policy overrides rather than relying only on prompt text. Its built-in profiles distinguish read-only planning, edit-focused work, approval-based operation, and unrestricted execution. Its session logger uses serialized writes, atomic metadata replacement, and durable session data. Its compaction manager only mutates the live conversation after producing a valid summary, and its checkpointer treats changes as an append-only, reviewable event history. [1] [2] [3] [4]

| Vibe pattern | Existing GOAR capability | GOAR adaptation |
|---|---|---|
| Named agent profiles backed by tool policy | GOAR currently operates in a single global auto-approve mode | Add session-scoped `operator`, `plan`, `accept-edits`, and `explore` profiles with explicit allowlists. |
| Read-only plan / explore operation | GOAR has powerful tools and a shared workspace, but no enforced profile boundary | Enforce read-only allowlists in `plan` and `explore`; blocked tools return a structured policy denial before execution. |
| Edit-focused profile | GOAR has file-edit tools plus browser, secrets, shell, and installation tools | Provide `accept-edits`, allowing workspace file edits and code search but blocking network, browser, shell, secret, job, and system-changing tools. |
| Durable profile/session identity | GOAR already persists history, UI messages, model, title, and token counts | Persist each session’s active profile and present it through a local API. |
| Clear profile visibility in system context | GOAR’s system prompt currently states that auto-approve is always enabled | Append a profile-specific policy block to the system prompt and use it as the enforcement source of truth. |

## Selected First Upgrade

The first compatible upgrade is a **Vibe-inspired operator-profile system**. It is deliberately small and enforceable:

| Profile | Intended use | Tool policy |
|---|---|---|
| `operator` | Existing GOAR behavior for end-to-end unattended operation | Full tool set; preserves GOAR’s current auto-approve compatibility. |
| `plan` | Explore a project, inspect a site, or design a change safely | Read-only tools only; no writes, shell, browser input, downloads, secrets, jobs, or external side effects. |
| `accept-edits` | Implement or refactor files without allowing broader operational actions | Workspace read/search/edit, todo, skill inspection, session compaction, and undo/checkpoint tools; no shell, network, browser, secrets, or jobs. |
| `explore` | Lightweight read-only investigation, including subagent use | Minimal read/search/list/skill tool set. |

The profile is a guardrail, not merely a prompt. Every model-issued tool call is checked against the active profile immediately before execution. The default remains `operator` for compatibility with existing GOAR workflows. The Android UI continues to load the full local backend; profile selection is available through local loopback API endpoints and session metadata.

## Android Installer Correction

The Android rootfs failure was traced to GNU tar `L` long-name records. The installer skipped those metadata records, so the next file was extracted using a truncated 100-byte header path. A long Python cache filename was consequently written to its parent `__pycache__` directory, yielding the device’s `EISDIR` error. The corrected extractor consumes GNU `L` and `K` records, applies the resulting full pathname or link target to the subsequent entry, and retains the archive path and symbolic-link boundary checks.

A host integration harness was run against the actual 425.7 MiB Android rootfs archive. It processed **23,844 filesystem entries** and **3,341 GNU long-path/link records**, restored archive modes, verified the formerly failing `cryptography/.../__pycache__/rsa.cpython-312.pyc` path, and then launched the extracted aarch64 GOAR backend under PRoot/QEMU. The backend health endpoint returned HTTP 200 after its emulated cold start.

## References

[1] [Mistral Vibe core directory](https://github.com/mistralai/mistral-vibe/tree/main/vibe/core)

[2] [Mistral Vibe agent profiles](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/agents/models.py)

[3] [Mistral Vibe compaction manager](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/compaction/manager.py)

[4] [Mistral Vibe checkpoint mechanism](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/checkpoints/checkpointer.py)
