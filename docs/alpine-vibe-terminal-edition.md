# GOAR Alpine Private Vibe Edition

## Product contract

This is a separate Android edition built from a freshly downloaded and checksum-verified official **Alpine Linux 3.24.1 AArch64 minirootfs** and a fresh upstream **Mistral Vibe** source snapshot. It preserves the full upstream terminal user interface, onboarding, session behavior, agent loop, tools, planning, workspace interaction, configuration model, and ordinary terminal operation.

The Android product surface is deliberately narrow. On first launch, the single terminal activity automatically retrieves the release manifest, downloads the rootfs, verifies the expected byte size and SHA-256 digest, and extracts it into app-private storage. A temporary centered status overlay is shown only during this verified installation. It has no buttons, manifest editor, console, tabs, or controls. On completion—and on every subsequent launch—the same full-screen native PTY terminal runs the full Mistral Vibe TUI immediately, including its upstream onboarding flow.

> After boot, there is one Android terminal activity. The Mistral Vibe TUI runs inside it; there are no separate Android tabs, cards, dashboard screens, or operator-console controls.

The requested privacy removals do not replace or simplify the upstream Vibe operational model. They remove only analytics and nonessential reporting or media capabilities. Normal operator-initiated model-provider calls, terminal tool execution, workspace handling, sessions, and user-selected Vibe features are otherwise preserved. Update checks, update prompts, and automatic updates are disabled rather than deferred to an Android control surface.

## Preserved upstream behavior

| Upstream capability | Private Alpine edition |
|---|---|
| Terminal TUI and rendering | Preserved inside the one native Android PTY terminal. |
| First-run onboarding | Preserved; configuration prompts appear in the terminal TUI. |
| Agent loop, sessions, plans, tools, permissions, hooks, workspace handling | Preserved. |
| Model provider configuration and explicit prompt-to-provider requests | Preserved. |
| Normal terminal tool execution and filesystem operations | Preserved. |
| Text interaction, history, autocompletion, project handling, worktrees | Preserved where supported by the Alpine guest. |

## Removed privacy-sensitive behavior

| Upstream surface | Private Alpine edition |
|---|---|
| Product telemetry, OpenTelemetry, analytics, usage events, tool/session tracking | Removed. |
| Sentry and crash reporting | Removed. |
| Automatic/startup/PyPI update checks and update prompts | Removed. |
| Audio playback, microphone enumeration, recording, transcription, voice mode, narration/TTS | Removed. |
| Feedback surveys, account reporting, remote experiments, product diagnostics | Removed. |
| Nonessential background network services | Removed. |

The build does not include Flask, Chromium, WebView, VNC/noVNC, desktop packages, browser stack, or Android analytics SDKs.

## Fresh base provenance

The builder verifies `alpine-minirootfs-3.24.1-aarch64.tar.gz` against Alpine’s published SHA-256 before extraction. It fails if the calculated digest differs from the verified source checksum. The final rootfs records Alpine 3.24.1 AArch64 provenance and the exact upstream Mistral Vibe commit `5e6aa0f6beb3454454f4c1de74a7652ba577ab05`.

## Release identity

| Item | Value |
|---|---|
| Android package ID | `com.goar.alpine` |
| Android surface | One immersive native PTY terminal activity, with an installation-only status overlay on first run. |
| Rootfs archive | `goar-alpine-vibe-3.24.1-aarch64.tar.gz` |
| Rootfs size | `389,770,281` bytes |
| Rootfs SHA-256 | `407810d6d63703c7089e44a84cb68d1d8055747641a33675613be03eecf5ebad` |
| Guest entrypoint | `/usr/local/bin/goar-alpine-vibe` |
| Preserved upstream version | Mistral Vibe `2.24.2` |

## Validation target

The release gate verifies the fresh Alpine base, upstream Mistral Vibe revision, preserved full TUI launch and onboarding, absence of the requested privacy-sensitive modules and packages, no automatic outbound request before an operator-driven model action, ordinary explicit model-provider requests, direct Android terminal dispatch after installation, native PRoot ABI, and APK signature.
