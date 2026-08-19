# Third-Party Notices

## VibeHack

The Kali terminal distribution includes a modified copy of VibeHack from `https://github.com/rasyiqi-code/VibeHack` at revision `579714b848625b26bb5765f37a0c40818293c54f`.

The upstream repository does not publish a license file. The Operator explicitly confirmed permission to modify and redistribute VibeHack for this GOAR project on 2026-08-19. GOAR changes are limited to the Android/PRoot adaptation: the Docker execution adapter is replaced by the app-private Kali PRoot guest, the desktop keyring is disabled by default, the unavailable global keyboard-listener dependency is removed, LiteLLM is loaded lazily to speed mobile terminal startup, and the GOAR terminal launcher/prompt/control plane are added separately.

## Mistral Vibe Core

GOAR's `goar_vibe_core.py` is an independently written standard-library adaptation of public Mistral Vibe core architecture concepts. It preserves Apache License 2.0 attribution for the source reference:

- Source: `https://github.com/mistralai/mistral-vibe/tree/main/vibe/core`
- License: Apache License 2.0

The copied implementation does not include Mistral cloud credentials, model-specific prompts, terminal UI, or server code.

## Grok Build ptyctl

The Android terminal design uses Grok Build `ptyctl` as the behavioral reference for PTY ownership, ANSI/VT terminal state, scrollback, resize, terminal-generated replies, and lifecycle handling:

- Source: `https://github.com/xai-org/grok-build/tree/main/crates/codegen/ptyctl/src`
- Revision inspected: `d92c5b0b8582fda358de1f97446aa74af44a464f`
- License: Apache License 2.0

Any source copied from this reference must retain the Apache 2.0 license and applicable notices.
