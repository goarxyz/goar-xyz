# GOAR OS Android v1.2.2 — Byte-Accurate PAX Extractor Correction

This upgrade corrects the POSIX PAX parser to use byte-counted records exactly as encoded by the Kali archive, including non-ASCII paths. It retains the GOAR launcher icon, restrained monochrome native operator console, and compact APK plus separately downloaded, checksum-verified Kali ARM64 PRoot backend introduced in v1.2.0.

## What changed

| Area | v1.2.2 behavior |
|---|---|
| Rootfs installer | Accepts valid literal-backslash Linux filenames such as Kali systemd `\\x2d` unit names and parses POSIX PAX extended paths using their declared byte lengths, including real non-ASCII Kali certificate paths, while retaining canonical path-containment checks against traversal. |
| Launcher icon | The actual Android application and round icon use the GOAR monochrome mark at every Android launcher density. |
| Durable loops | The foreground service owns a separate PRoot `goar_loopd` process. It is restart-eligible, persists state in app-private storage, and has no implicit five-minute agent-turn cutoff. |
| Operator Console | A sparse monochrome console routes into six dedicated workspaces: Terminal, Agent Chat, Control, Kali Packages, Configuration, and Runtime. |
| Direct Terminal | Runs an ordinary interactive Kali `/bin/bash -l` shell. No agent messages, package output, plan data, control records, or application status text is injected into it. |
| Agent Chat | A separate native PTY launches the GOAR/VibeHack terminal agent and contains only the agent conversation and its tool output. |
| Configuration | Stores the provider key and model in the app-private VibeHack configuration. The key is masked after saving. |
| Kali Packages | Provides explicit operator-approved APT presets and validated custom package names. Package output remains on the package screen. |

## Installation

Install `goar-os-v1.2.2-arm64-v8a.apk` on an **arm64-v8a Android device running Android 8.0 or later**. On first launch, GOAR retrieves `goar-rootfs-arm64-v8a.json`, downloads the Kali terminal rootfs, validates both its byte size and SHA-256 digest, and extracts it only under app-private storage. The guest has normal outbound Android networking and exposes neither a browser nor an HTTP/VNC service.

The Direct Terminal is an operator shell. Agent Chat requires the operator to configure a compatible provider key from the Configuration screen or within the private guest environment.

## Verified assets

| Asset | SHA-256 | Size |
|---|---|---:|
| `goar-os-v1.2.2-arm64-v8a.apk` | `4cc0613b91697c4bc45a7f149ea2a232999bdb34bff7f21d64b940a4ae3cad1d` | 185,203 bytes |
| `goar-kali-terminal-arm64.tar.gz` | `f688825035b2c8e287367cd575fe5b2d7217dffc1809ff72af2f4a83d703cf32` | 322,088,301 bytes |

## Validation completed

The Kali release archive was reproducibly rebuilt, independently extracted, and run under ARM64 PRoot emulation. Guest validation passed `goarctl status`, direct agent-launcher help with duplicate loop startup disabled, and outbound HTTPS. The archive audit verified the durable-loop policy, the valid systemd filename that caused the prior Android error, and the absence of traversal entries.

The repository regression suite passed all **29 tests**, including the exact long Kali JSON-schema PAX path and a real Unicode Kali certificate path. The archive audit found 3,217 real PAX records, including non-ASCII entries; the parser now reads those records as raw bytes rather than Java characters. The signed APK passed v2 and v3 signature verification, declares package version `1.2.2` with version code `8`, restricts native code to `arm64-v8a`, includes the complete Kai-model PRoot payload plus `libgoar_terminal_jni.so`, and contains Android launcher icon resources at every standard density.

## Remaining limitation

No physical Android device was connected to the build environment. The release has been validated through source contracts, an actual ARM64 guest run, APK signature and structure checks, and the full regression suite. A physical arm64 Android device remains necessary to complete first-run extraction, foreground-service behavior under device battery policy, launcher appearance, and interactive terminal validation.

For implementation detail, see [the terminal architecture](kali-terminal-architecture.md), [the premium operator-console design](operator-console-design.md), and [the migration audit](kali-terminal-migration-audit.md).
