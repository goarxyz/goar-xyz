# GOAR OS Native Operator Console

## Product boundary

The Android application is a **terminal-first operator console**, not a browser shell. It presents separate native monochrome workspaces over one app-private Kali PRoot guest. The direct terminal and the VibeHack agent conversation are deliberately different experiences and must never write UI chrome, conversation text, package activity, or control events into one another.

| Workspace | Purpose | Guest command | Output boundary |
|---|---|---|---|
| Console | Native landing and navigation after the verified backend is installed. | None. | Backend state and navigation only. |
| Terminal | Direct operator-owned Kali shell for scripts and commands. | `/bin/bash -l` | Raw operator shell only. |
| Agent Chat | Dedicated VibeHack terminal REPL with the GOAR prompt and lifecycle wrapper. | `/usr/local/bin/goar-terminal` | Agent conversation and agent tool output only. |
| Control | Session state, plans, loops, checkpoints, and event access. | `goarctl` queries only. | Structured control output only. |
| Configuration | Provider setup and runtime preferences stored in app-private GOAR state. | Writes validated `.env` values only on explicit save. | Configuration fields only. |
| Kali Packages | Operator-approved APT package selection and custom package install. | `apt-get update` or `apt-get install -y -- <packages>`. | Package progress and command output only. |

## Durable runtime

The foreground service owns a **separate PRoot loop-daemon process**. It mounts the same durable GOAR state and workspace as the interactive workspaces, scans every persisted loop record, and starts bounded agent turns under the existing session lease. The direct Terminal and Agent Chat use their own foreground PTY sessions. They set `GOAR_DISABLE_LOOPS=1` so they cannot create competing schedulers.

The state, workspace, configuration, plans, loops, checkpoints, and event ledger are app-private files. They persist across activity recreation and app reopening. The foreground service requests `START_STICKY` and `stopWithTask=false`, so Android can recreate the durable scheduler after a process restart. Android may still terminate an app under extreme system pressure, so the design treats durable records and idempotent loop handling—not an immortal process—as the recovery guarantee.

## Package-management model

The package screen never runs an installation implicitly. An operator must select a preset or type package names, review the exact APT command, and explicitly start it. Package names are validated as whitespace-separated Debian package tokens before the app forms `apt-get install -y -- <packages>`. Output is shown only on the package screen and package state is retained inside the private Kali rootfs.

The package screen contains convenience presets for reconnaissance, web testing, wireless tooling, password auditing, and general utilities, but it does not grant capabilities beyond the local Kali guest and Android network path already available to the direct terminal.

## Monochrome navigation

The Console home has six independent entries: **Terminal**, **Agent Chat**, **Control**, **Kali Packages**, **Configuration**, and **Runtime**. Every screen uses the existing black, white, muted-gray, and thin-outline style. A user returns to the Console through native navigation rather than overlaying panels over any PTY view.

> Direct Terminal means direct Terminal: no injected assistant transcripts, no dashboard widgets, no package progress, no plan reminders, and no GOAR system messages beyond what a command executed by the operator itself emits.
