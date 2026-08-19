# GOAR OS Android v1.1.0 — Terminal-First Kali PRoot Release

This release replaces the former web-server, browser, VNC, and noVNC design with a compact Android launcher that downloads a verified **minimal Kali ARM64 PRoot guest** and opens it through a native monochrome terminal. The APK remains small because the complete guest is a separately verified first-run download.

## Included components

| Component | Release asset or behavior |
|---|---|
| Android package | `goar-os-v1.1.0-arm64-v8a.apk`, package `com.goar.os`, version code `5`, version name `1.1.0`. |
| Native runtime | ARM64 Kai-model PRoot payload: primary binary, arm64 and armv7 tracee loaders, and the compatible `libtalloc.so.2` materialization. |
| Terminal | Native JNI PTY bridge plus a monochrome ANSI/VT terminal surface. No WebView or browser renderer is used. |
| Guest | `goar-kali-terminal-arm64.tar.gz`: minimal Kali ARM64 base, adapted VibeHack terminal agent, GOAR terminal prompt, and durable GOAR control plane. |
| Control plane | Local plans, checkpoints, trusted roots, hooks, configuration layers, append-only events, session leases, compaction, and bounded durable loops. |

## First-run installation

Install the APK on an **arm64-v8a Android device running Android 8.0 or later**. On first launch, the application retrieves `goar-rootfs-arm64-v8a.json`, downloads the referenced Kali archive, verifies both the declared size and SHA-256 digest, extracts it only into app-private storage, and then exposes the native terminal workspace. The guest receives normal outbound network access through Android, but it does not expose a local HTTP service or public port.

The installer requires a network connection for the initial guest download. The user controls VibeHack provider credentials inside the contained terminal environment; credentials and durable agent state remain below the app’s private storage.

## Verified release assets

| Asset | SHA-256 | Size |
|---|---|---:|
| `goar-os-v1.1.0-arm64-v8a.apk` | `d77f1c3f42f29fe22060eb6692129ecb1cebcce6c21cd906907970db3a87392d` | 155,728 bytes |
| `goar-kali-terminal-arm64.tar.gz` | `7a8b7db631ee9a203d66ae57023c23916bbdf43e0b92f78c8a336ce9c208324c` | 322,092,086 bytes |

## Validation completed

The release rootfs was rebuilt reproducibly from the official minimal Kali ARM64 base with the vendored VibeHack and GOAR terminal overlays. The packaged guest was then independently executed under ARM64 PRoot emulation. That smoke test passed `goarctl status`, imported the interactive GOAR wrapper, launched `goar-terminal --help`, and completed an outbound HTTPS request. The repository regression suite passed all **24 tests**, including manifest/archive integrity, Kai-model PRoot loader contracts, native PTY presence, terminal-only runtime guards, GOAR core persistence, checkpoints, trust boundaries, events, leases, and loops.

The final APK was built cleanly, aligned, signed with APK Signature Scheme v2 and v3, and inspected to confirm package version `1.1.0`, `arm64-v8a` as the only ABI, the complete four-file PRoot native payload, and `libgoar_terminal_jni.so`.

## Important limitation

No physical Android device was connected to the build environment. The release has therefore been validated through source contracts, an actual ARM64 PRoot guest run, and APK structural/signature inspection, but **installation and interactive terminal behavior on a physical arm64 Android device remain the final external validation step**.

For implementation details, see [the terminal architecture](kali-terminal-architecture.md) and [the migration audit](kali-terminal-migration-audit.md).
