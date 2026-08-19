# Kali Terminal Migration Audit

**Date:** 2026-08-19
**Purpose:** Replace the previous Flask/Chromium/VNC GOAR distribution with a compact, terminal-first Android PRoot design.

## Verified Inputs

| Component | Revision or source | Verified requirement | Integration decision |
|---|---|---|---|
| Kali NetHunter minimal rootfs | Official `kali-nethunter-rootfs-minimal-arm64.tar.xz` | Official ARM64 archive; SHA-256 checked against the adjacent official `SHA256SUMS`; 137,313,840 bytes compressed; includes Bash, Python 3.13, APT, and Git. | Use as the separate first-run backend download. Do not use the 1.6 GiB full rootfs. |
| VibeHack | `579714b848625b26bb5765f37a0c40818293c54f` | Python 3.11+ terminal REPL built with `prompt-toolkit` and `rich`; its current execution layer hard-requires Docker. | Carry under the user-confirmed permission basis, but replace only its Docker executor with a persistent PRoot-native shell/PTY executor. |
| Mistral Vibe | `5e6aa0f6beb3454454f4c1de74a7652ba577ab05` | Apache-2.0 licensed; provides sessions, plans, loops, middleware, checkpoints, compaction, trust, hooks, and observability patterns. | Reuse/adapt permitted control-plane mechanisms with Apache-2.0 notices, keeping GOAR’s system prompt and drive. |
| Grok Build ptyctl | `d92c5b0b8582fda358de1f97446aa74af44a464f` | Apache-2.0 licensed; models an actual PTY plus ANSI terminal state, scrollback, resize, key input, interrupt, and terminal-generated replies. | Implement an Android-native terminal around the same behavioral contract; no browser, Flask server, or WebView. |

## Rootfs Baseline

The approved base is the official current **minimal ARM64 Kali NetHunter rootfs**, not the full image. The inspected archive has a `kali-arm64/` top-level directory and includes `/usr/bin/bash`, `/usr/bin/python3.13`, `/usr/bin/python3`, `/usr/bin/apt`, and `/usr/bin/git`. It is therefore adequate for a Python terminal agent without carrying Chromium, VNC, noVNC, Gunicorn, or Flask.

The rootfs remains a first-run download to preserve a compact APK. The APK carries the matching Android PRoot runtime separately in its native library section: `libproot.so`, `libproot-loader.so`, `libproot-loader32.so`, and `libtalloc.so`. The runtime continues to materialize the talloc soname as `filesDir/goar/native-runtime/libtalloc.so.2`.

## VibeHack Adaptation Boundary

VibeHack’s interface is a full-screen `prompt-toolkit` terminal REPL with persistent history, slash commands, memory, tool discovery, and agent-turn orchestration. Its current `PersistentSession` starts a Bash process through `docker exec`, and its `execute_shell()` gate fails whenever Docker is unavailable. Docker cannot run inside an unrooted Android PRoot guest.

The migration therefore preserves the REPL, memory, tool discovery, output sanitization, and agent orchestration, while replacing the Docker-specific sandbox/session module with a guest-native persistent Bash session. The guest itself is the containment boundary: the rootfs, GOAR drive, workspace, temporary data, logs, and Vibe state are all placed below the app-private `filesDir/goar` hierarchy. Android networking remains available to the guest through PRoot, but no public server or browser interface is started.

The VibeHack repository presently declares no public license. The user explicitly confirmed permission to modify and redistribute it for this project on 2026-08-19. This permission basis must be retained in the project’s third-party notice alongside the source revision.

## Native Terminal Contract

The Android front end is a real terminal, not a scrollable command-output view. Its completed implementation follows the ptyctl model:

1. `GoarPtyBridge` uses the native JNI bridge to allocate a pseudo-terminal, fork, and execute the PRoot command with `TERM=xterm-256color` and `COLORTERM=truecolor`.
2. The monochrome `GoarTerminalView` accepts the ANSI/VT controls used by Bash and VibeHack, retains scrollback, cursor state, and alternate-screen behavior, and returns UTF-8 input plus navigation/control sequences to the PTY.
3. Android layout changes update the terminal grid and invoke the native window-size operation so the guest receives its resize signal.
4. The workspace activity owns and explicitly closes the PTY bridge; durable scheduled loops are guest-side processes and are protected by the session lease.
5. No WebView, HTTP listener, Flask process, VNC/noVNC component, or browser dependency remains in the Android terminal path.

## Mistral-Style GOAR Control Plane

The terminal build retains the following local, durable mechanisms rather than merely exposing a raw shell:

| Mechanism | Terminal-first role |
|---|---|
| Layered configuration | Resolve global, workspace, session, and command overrides with origins and fingerprints. |
| Session lease | Ensure one agent or loop turn owns a VibeHack session at a time. |
| Middleware pipeline | Apply injection, trust, cancellation, and compaction decisions before each agent turn. |
| Plans | Persist task plans and step lifecycle transitions in the GOAR drive. |
| Checkpoints and rewind | Record workspace file changes and enable review/revert before destructive automation proceeds. |
| Trusted folders | Permit agent workspace operations only under explicitly trusted roots. |
| Hook registry | Run pre/post tool and post-agent hooks within the PRoot guest. |
| Scheduled loops | Persist session-scoped loops, enforce a 30-second minimum interval and 50-loop cap, and run turns serially under the session lease. |
| Event ledger | Emit append-only JSONL events while recording only digests of sensitive tool arguments. |
| Atomic compaction | Apply deterministic local history compaction only after the replacement context has been constructed successfully. |

The controls apply to VibeHack/GOAR agent turns and loop automation. They do not remove the user’s normal interactive Kali terminal or its standard outbound network access.

## References

[1]: https://kali.download/nethunter-images/current/rootfs/ "Official Kali NetHunter rootfs index"
[2]: https://www.kali.org/docs/nethunter/nethunter-rootless/ "Kali NetHunter Rootless documentation"
[3]: https://github.com/rasyiqi-code/VibeHack "VibeHack"
[4]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/core "Mistral Vibe core"
[5]: https://github.com/xai-org/grok-build/tree/main/crates/codegen/ptyctl/src "Grok Build ptyctl"

## Additional VibeHack Packaging Findings

The audited VibeHack `pyproject.toml` declares Python `>=3.11` and exposes the `vibehack` command through `vibehack.cli:app`. Its terminal UX depends on `typer`, `rich`, `prompt-toolkit`, `python-dotenv`, `pydantic`, and `PyYAML`. The vendored PRoot adaptation retains the agent runtime packages such as `litellm`, `google-auth`, `google-auth-oauthlib`, `nest-asyncio`, `httpx`, `numpy`, `psutil`, and `beautifulsoup4`, while removing desktop-only `pynput` and `keyring` requirements in favor of a PRoot-safe keyring implementation.

The official minimal Kali ARM64 rootfs was booted under PRoot/QEMU and verified to provide Python 3.13, Bash, APT, Git, and `script`. It does not include Python virtual-environment bootstrap support by default. A Python-only venv bootstrap using `python3 -m venv --without-pip` followed by the official PyPA `get-pip.py` succeeded; this avoids a cross-build-only `dpkg` access-check incompatibility under host QEMU/PRoot. That incompatibility is not treated as evidence of an Android native PRoot runtime limitation, and the final runtime remains configured for normal guest package management.

The final pinned VibeHack dependency installation has been built successfully against ARM64 Python 3.13 wheels. The product intentionally omits the desktop-only `pynput`/`evdev` path because Android’s native terminal is the input surface, and it replaces the desktop keyring path with a PRoot-safe implementation. The guest archive smoke test verified `goarctl`, the interactive GOAR wrapper import, the `goar-terminal --help` launcher path, and outbound HTTPS.

[6]: https://bootstrap.pypa.io/get-pip.py "PyPA get-pip bootstrap"
