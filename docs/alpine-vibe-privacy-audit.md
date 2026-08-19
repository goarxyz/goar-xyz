# Alpine Vibe Private Terminal Audit

## Upstream provenance

The Alpine terminal edition is derived from a fresh shallow source snapshot of [Mistral Vibe](https://github.com/mistralai/mistral-vibe) at commit `5e6aa0f6beb3454454f4c1de74a7652ba577ab05`, retrieved on 2026-08-19. The upstream project is licensed under **Apache License 2.0**. The GOAR derivative retains the required license and notice material in the guest distribution.

The guest base is independently refreshed from Alpine Linux 3.24.1 AArch64 minimal rootfs and validated against the SHA-256 file published with that official release. The resulting APK downloads only the final GOAR guest archive from its pinned release manifest; the Android app contains no embedded model key and no browser or remote-desktop stack.

## Audit conclusion

The upstream project contains product telemetry, OpenTelemetry dependencies, Sentry integration, version/update checks, account and feedback services, experiments, text-to-speech, microphone recording, audio playback, transcription, and app-server resource surfaces. The private fork retains only API-compatible local no-op boundaries where the complete upstream TUI requires them; no reporting, update, audio, account, or remote-experiment transport remains reachable.

| Upstream surface | Private Alpine edition disposition |
|---|---|
| `vibe/core/telemetry`, OpenTelemetry dependencies | Replaced with local no-op compatibility boundaries; no product, tool, session, startup, or prompt telemetry is emitted. |
| `vibe/observability/sentry.py`, `sentry-sdk` | Replaced with a local no-op; no crash reporting is initialized, queued, or flushed. |
| `vibe/cli/update_notifier`, update prompts, PyPI update gateway | Replaced with local no-ops; no automatic, background, manual, or startup version check is available. |
| `vibe/cli/audio_*`, concrete voice/narrator implementations, TTS, transcription, `sounddevice` | Removed or replaced by no-op managers; no microphone enumeration, recording, playback, voice UI, audio upload, or narration code is shipped. |
| Feedback, surveys, ratings, account, experiments, remote app-server resource calls | Made local no-ops; no feedback prompt, account lookup, experiment assignment, tracking, or remote reporting request is available. |
| Browser, WebView, Flask, VNC/noVNC, Chromium, desktop packages | Excluded from both Android and Alpine guest. |
| Model request client | Retained only for the operator-configured provider endpoint needed to answer an explicit CLI prompt. |
| Standard terminal networking | Retained only for commands explicitly launched by the operator or by an agent turn the operator initiated. |

## Runtime privacy contract

The final `/usr/local/bin/goar-alpine-vibe` launcher starts the preserved private terminal implementation directly. The retained local app-server is still used by the full upstream TUI for its normal session runtime, but its telemetry, feedback, account, identity, and experiment resource paths are local no-ops. There is no automatic network request at process start from telemetry, updates, account refresh, experiments, audio, or crash reporting. Network access remains available for explicit onboarding, operator-invoked model requests, terminal commands, and agent turns that the operator initiates.

The Android post-install surface is a single native PTY activity. It does not expose telemetry controls because no telemetry or tracking implementation exists in the shipped edition.

## Validation obligations

The release gate rejects the sensitive runtime modules and dependencies from the final guest archive, checks the private CLI import graph for forbidden package names, verifies the full Textual onboarding screen in a network-isolated terminal, validates the rootfs archive by checksum and clean extraction, and verifies the separate Android APK signature, package ID, launcher activity, and native PRoot payload.
