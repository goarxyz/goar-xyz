# GOAR OS for Android

## Release 1.0.0

GOAR OS for Android is an **arm64-v8a native Android application** that installs a compact local launcher and then downloads the complete Alpine Linux GOAR backend on first use. The APK does not replace GOAR with a remote client or a reduced feature set. Instead, it loads the full Flask/Gunicorn service, Chromium automation stack, Playwright client, VNC/noVNC components, Python runtime, Node runtime, and GOAR workspace/session APIs from an Alpine root filesystem stored inside the application’s private data directory.

| Component | Delivered how | Purpose |
|---|---|---|
| Android APK | Direct installation | Provides the native UI, local WebView, foreground runtime service, network permissions, and arm64 PRoot bootstrap. |
| Rootfs manifest | HTTPS on first use | Declares the required `arm64-v8a` architecture, archive URL, exact byte size, and SHA-256 digest. |
| Alpine GOAR rootfs | HTTPS on first use | Contains the full GOAR backend and its runtime dependencies. |
| App-private state and workspace | Created locally | Holds service state, sessions, uploads, downloads, skills, logs, temporary files, and user workspace data. |

## What happens on first launch

The app first retrieves the small release manifest over HTTPS. It rejects a manifest intended for any CPU architecture other than `arm64-v8a`, downloads the rootfs archive, checks its expected byte count, and calculates its SHA-256 digest before installation. The verified archive is extracted into `Context.getFilesDir()/goar/rootfs`, which is private to the Android app.

The extractor rejects archive paths that escape this directory and validates relative symbolic links so they cannot resolve outside the rootfs. Standard Alpine guest-root links such as `/bin/sh -> /bin/busybox` remain valid because PRoot resolves them within the guest filesystem rather than against Android’s host filesystem.

When you choose **Start**, the app starts its bundled arm64 PRoot launcher as a foreground service. PRoot uses the extracted rootfs as its guest root and binds only these app-private directories into it:

| Android app-private location | Guest location | Purpose |
|---|---|---|
| `files/goar/state` | `/data/goar` | GOAR service state, history, sessions, skills, tasks, and memory. |
| `files/goar/workspace` | `/data/workspace` | Your workspace plus uploads and downloads. |
| `files/goar/tmp` | `/tmp` | Temporary runtime data. |
| Generated DNS resolver | `/etc/resolv.conf` | Uses DNS servers reported by Android’s active network. |

The contained `/usr/local/bin/goar-serve` script starts the regular GOAR Flask application through Gunicorn at `127.0.0.1:8080`. The native UI displays that local interface through its WebView. The server is deliberately limited to loopback by default; it is not exposed to your Wi-Fi or mobile network. The contained process has normal outbound network access through Android’s `INTERNET` permission, including the network access required by the original GOAR backend and browser automation features.

## Included backend capabilities

The downloaded Alpine rootfs includes the normal GOAR production application and its Python dependencies, Gunicorn, Chromium, the Playwright client, Node, TigerVNC, noVNC, Fluxbox, websockify, and supporting system libraries. Browser automation remains local to the device runtime. The APK’s small size is intentional: the large, independently verified rootfs is fetched only when needed rather than embedded in every APK download.

The published arm64 rootfs is currently **425.7 MiB compressed**. Installation requires additional device storage for extraction and ongoing state. Use a stable network connection and leave ample free storage before the first launch.

## Installation

Download the release APK from the [GOAR Android release](https://github.com/goarxyz/goar-xyz/releases/tag/goar-android-v1), install it on an Android 8.0 (API 26) or newer **arm64** device, and permit installation from the browser or file manager when Android asks. Open the app, allow it to download and verify the rootfs, then start the local backend.

> **Important:** The earlier `app-debug.apk` was signed with Android’s debug certificate. If it is already installed, uninstall it before installing the 1.0.0 release APK because Android does not allow one signing identity to update an app installed by another.

## Reproducible release signing

The Gradle project reads release credentials from the ignored file `android/release-signing.properties`. This keeps signing secrets outside version control while allowing future versions to retain the same Android application identity and update path.

```properties
storeFile=/absolute/path/to/goar-os-release.jks
storePassword=your-keystore-password
keyAlias=goar-os-release
keyPassword=your-key-password
```

Build with:

```bash
cd android
./gradlew --no-daemon assembleRelease
```

The release keystore and credentials must be retained securely. Losing them prevents future APK versions from updating installations signed with this release identity.

## Release assets

| Asset | URL |
|---|---|
| Android release APK | Published with the `goar-android-v1` release. |
| Verified rootfs manifest | [`goar-rootfs-arm64-v8a.json`](https://github.com/goarxyz/goar-xyz/releases/download/goar-android-v1/goar-rootfs-arm64-v8a.json) |
| Full Alpine GOAR backend | [`goar-alpine-3.22.5-aarch64.tar.gz`](https://github.com/goarxyz/goar-xyz/releases/download/goar-android-v1/goar-alpine-3.22.5-aarch64.tar.gz) |
