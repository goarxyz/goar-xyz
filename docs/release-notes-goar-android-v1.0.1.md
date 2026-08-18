# GOAR OS for Android v1.0.1

This release replaces the initial Android APK with a corrected, release-signed **v1.0.1** build and publishes the matching full arm64 Alpine backend.

## Fixed Android Installation

The installer now correctly supports GNU tar `L` and `K` extended records, which carry paths and link targets longer than the fixed USTAR header fields. This resolves the first-run extraction failure reported as an `EISDIR` error under Python’s `cryptography/.../__pycache__` path. The extractor continues to enforce archive path-boundary protections, symbolic-link validation, byte-size verification, and SHA-256 verification.

## Upgraded GOAR Core

The local backend now adds a Mistral Vibe-inspired, enforced operating-profile model while retaining GOAR’s complete default operator capability.

| Profile | Purpose |
|---|---|
| `operator` | Full GOAR backend and existing unattended operator behavior. |
| `plan` | Read-only exploration and planning. |
| `accept-edits` | Workspace reads and edits only; broad external/system actions are blocked. |
| `explore` | Minimal read-only investigation. |

Profiles are stored with the local GOAR session and are enforced immediately before model-requested tool execution. The loopback API exposes `GET` and `POST /v1/operator/profile` for profile inspection and selection.

## Verification

The exact downloadable rootfs was processed using an installer-equivalent integration harness. The test extracted **23,841 filesystem entries** and handled **3,341 GNU long-path/link records**. GOAR was then launched from that extracted aarch64 filesystem under PRoot/QEMU; the health endpoint returned HTTP 200 and the profile selection persisted across separate loopback API requests.

The repository regression suite passed all 6 tests. The APK package is `com.goar.os`, version code `2`, version name `1.0.1`, arm64-v8a only, and is verified with Android APK Signature Scheme v2 and v3.

| Artifact | SHA-256 |
|---|---|
| `goar-os-android-arm64-v8a-release-1.0.1.apk` | `a445aa641547faa812aaa69ef2c38b9f9cf5ac73c5751de5024d04c48969a463` |
| `goar-alpine-3.22.5-aarch64.tar.gz` | `53d3d7ef4deb0d045ed88a530dff3d5307cf96d02694774ecf1cdc5515b2ba36` |

The Android app fetches the manifest and backend archive from this release on its first run. Existing users who have the faulty 1.0.0 release build should install v1.0.1 and use **Download full GOAR backend and start**; the installer creates a fresh verified `rootfs.pending` staging directory before activation.
