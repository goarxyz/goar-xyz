# GOAR Terminal Kali PRoot Architecture

**Status:** Implemented terminal-first Android release architecture (v1.1.0).
**Scope:** This replaces the earlier Flask, browser, Chromium, VNC, and noVNC runtime. The Android application remains a compact launcher; the Kali guest remains a separately downloaded and verified archive.

## Runtime Topology

The Android package contains only the native application shell and the complete Android PRoot loader set. At installation time Android extracts `libproot.so`, `libproot-loader.so`, `libproot-loader32.so`, and `libtalloc.so` from the APK native-library directory. The launcher copies `libtalloc.so` to the app-private compatibility name `filesDir/goar/native-runtime/libtalloc.so.2`; this is the soname expected by the PRoot executable. The downloaded Kali archive is separately verified and extracted below `filesDir/goar/rootfs`.

| Layer | Responsibility | Persistent location |
|---|---|---|
| Android application | Installation UI, archive download/checksum/extraction, foreground service, native terminal view, keyboard and resize events. | Android app-private storage. |
| Android PRoot runtime | Starts the Kali ARM64 guest with the full matching arm64 and armv7 tracee loader set. | APK native-library directory plus `filesDir/goar/native-runtime`. |
| Kali minimal rootfs | Bash, Python 3.13, Git, APT, VibeHack, its declared runtime dependencies, GOAR terminal adapter, and no web/desktop stack. | `filesDir/goar/rootfs`. |
| GOAR drive | Workspace, prompt, configuration, plans, sessions, checkpoints, event log, trusted roots, hooks, and loops. | Mounted from `filesDir/goar/state` to `/data/goar`; workspace mounted to `/data/workspace`. |

The process launch target is a PRoot command with the app-private guest root, explicit `/dev`, `/proc`, and `/sys` binds, plus the durable `/data/goar` and `/data/workspace` mounts. It starts `/usr/local/bin/goar-terminal` rather than a web server. The guest has Android’s normal outbound networking path. No ports are exposed and no browser is started.

## Native Terminal Contract

The Android front end is a real terminal session, not a scrollable command-output page. Its behavior is modeled on ptyctl: the JNI bridge allocates a pseudoterminal, forks and executes the PRoot command under that PTY, streams raw bytes into the monochrome ANSI/VT surface, and returns UTF-8 keyboard input, interrupt signals, and terminal-resize events to the same PTY.

| Implemented behavior | Android terminal implementation |
|---|---|
| Full-screen applications | The ANSI/VT renderer implements cursor movement, erase operations, alternate-screen entry/exit, save/restore cursor state, and a bounded scrollback buffer for the VibeHack `prompt-toolkit` dashboard. |
| Input | The view sends UTF-8 input plus Enter, Backspace, Tab, Escape, and standard arrow, home/end, and page-navigation sequences to the PTY. |
| Resize | View geometry becomes terminal rows/columns and invokes the native PTY window-size operation so the guest can receive its resize signal. |
| Output | The renderer keeps the product deliberately monochrome while accepting the terminal control sequences used by Bash and VibeHack. |
| Lifecycle | `GoarPtyBridge` owns the spawned child descriptor and process; the workspace activity closes it explicitly, so neither a web server nor a browser lifecycle exists. |

The implementation uses a dedicated Android JNI terminal bridge informed by ptyctl behavior and contains no WebView, HTTP bridge, Flask process, VNC/noVNC component, or browser dependency.

## Kali Guest Layout

```text
/
├── data/
│   ├── goar/                  # mounted durable drive
│   │   ├── home/              # HOME and VibeHack config/session/memory state
│   │   ├── control/           # plans, loops, checkpoints, hooks, events
│   │   ├── tmp/               # managed guest temporary area
│   │   └── logs/
│   └── workspace/             # mounted trusted default workspace
├── opt/
│   ├── vibehack/              # Python virtual environment and adapted source
│   └── goar-terminal/         # prompt, control adapter, launcher, notices
└── usr/local/bin/goar-terminal
```

`goar-terminal` exports `GOAR_PROOT_GUEST=1`, `VH_SANDBOX=true`, `VH_SYSTEM_PROMPT=/opt/goar-terminal/GOAR_TERMINAL_PROMPT.md`, `HOME=/data/goar/home`, `GOAR_WORKSPACE=/data/workspace`, and `GOAR_RUNTIME_TMP=/data/goar/tmp`, then starts VibeHack. The VibeHack Docker adapter is replaced by a persistent guest-native Bash session. Its desktop keyring adapter is disabled by default; VibeHack obtains configured provider credentials from the app-private `.env` file or environment instead.

## Control Plane and Durable Loops

The reusable Mistral Vibe-style core remains local and library-only. It is not a Flask API. Every normal interactive VibeHack turn is wrapped by the GOAR facade for session leasing, middleware, deterministic local compaction, workspace checkpoint capture, events, hooks, sealing, and release; the bounded loop runner uses the same facade and session identity.

| Capability | Terminal behavior |
|---|---|
| Layered configuration | Resolves global, workspace, session, and temporary-command overrides with origin/fingerprint metadata. |
| Session lease | Serializes agent turns and scheduled loop turns. |
| Plans and checkpoints | Captures multi-step intent, lifecycle evidence, file-change ledgers, review, and safe reversion. |
| Trusted roots | Restricts agent workspace operations to explicitly trusted paths. |
| Hooks and middleware | Applies pre-tool/post-tool/post-agent policy, injection resistance, cancellation, and event capture. |
| Loop manager | Persists up to 50 session-scoped loops, enforces a 30-second minimum interval, evaluates completion/block conditions, and runs only one bounded turn per firing. |
| Event ledger | Keeps append-only JSONL events and argument digests without storing raw secrets. |
| Atomic compaction | Commits session summaries only after validation succeeds. |

The rewritten GOAR terminal prompt directs the agent to discover tools, install or compile missing capabilities, keep installations inside the guest, test results, optimize disk/cache use, and recover from errors rather than stopping at explanations. These controls apply to the automated agent and loops; the Operator retains a normal interactive Kali terminal with outbound network access.

## Package Budget and Reproducibility

The verified official minimal Kali ARM64 archive is 137,313,840 bytes compressed before GOAR additions. The reproducibly rebuilt terminal payload is **322,092,086 bytes** compressed with SHA-256 `7a8b7db631ee9a203d66ae57023c23916bbdf43e0b92f78c8a336ce9c208324c`. It remains a minimal Kali base plus the requested full terminal agent—not the older full desktop/browser distribution.

The build records the upstream source revisions, base-archive checksum, adapted-source changes, dependency lock, final archive checksum, manifest size, and archive safety audit. The Android installer downloads the final archive rather than embedding it in the compact signed APK.

## References

[1]: https://kali.download/nethunter-images/current/rootfs/ "Official Kali NetHunter rootfs index"
[2]: https://github.com/rasyiqi-code/VibeHack "VibeHack source"
[3]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/core "Mistral Vibe core"
[4]: https://github.com/xai-org/grok-build/tree/main/crates/codegen/ptyctl/src "Grok Build ptyctl"
