# Alpine Rootfs Build Notes

The Alpine Linux downloads page identifies the **mini root filesystem** as the distribution form intended for containers and minimal chroots. The current page lists Alpine Linux 3.24.1 and provides mini rootfs artifacts for x86_64 and aarch64 among other architectures. The GOAR OS rootfs build will use an official Alpine minirootfs base and Alpine package repositories rather than a host-managed installation.

The official Android build guidance reviewed earlier is no longer the delivery target. The incomplete Android scaffold is intentionally excluded from the Alpine rootfs implementation.

The GOAR rootfs needs Python, Chromium, VNC/noVNC, an X server, a lightweight window manager, and process supervision. Package availability must be verified against the selected stable Alpine repository during the rootfs build, with unsupported desktop elements documented or replaced by GOAR's existing agent-desktop fallback.

PRoot provides a rootless user-space filesystem boundary and bind-mount facility. The launcher can use a contained Alpine rootfs while binding an operator-owned state directory and workspace into that rootfs. PRoot translates guest system requests to the host kernel, so the contained Flask process can bind a local host port and use network resources; it is not a virtual machine or a separate kernel.

The PRoot project’s historical `proot-static-build` releases page is archived and its listed static binary is old. The GOAR distribution will therefore require a maintained host PRoot package, instead of embedding that stale binary. This keeps the rootfs reproducible while allowing the host platform to provide an architecture-appropriate PRoot implementation.

## Sources

[1] [Alpine Linux downloads](https://alpinelinux.org/downloads/)

[2] [Alpine noVNC package listing](https://pkgs.alpinelinux.org/package/v3.21/community/x86/novnc)

[3] [PRoot project](https://proot-me.github.io/)

## Android embedded-runtime findings

PRoot documents that it provides user-space `chroot` and bind-mount behavior using unprivileged `ptrace`, operates against the host kernel, and can execute a command against a supplied guest rootfs. Its bind mappings can relocate guest paths to selected host locations. This supports an APK architecture that unpacks an ABI-matched Alpine rootfs into the app-private files directory and launches it through an app-private PRoot executable, rather than replacing the GOAR backend with a thin remote client. Source: [PRoot documentation](https://proot-me.github.io/).

Android's `ProcessBuilder` documentation specifies that an app can launch an operating-system program with an explicit argument list, environment map, working directory, and redirected standard output/error. This supports a native Android service controller that starts the app-private PRoot executable, provides GOAR runtime paths as arguments and environment variables, and captures backend logs inside app-private storage. Source: [Android ProcessBuilder reference](https://developer.android.com/reference/java/lang/ProcessBuilder).

The Termux `proot-distro` project documents rootless Linux userlands on Android using PRoot and a local rootfs archive, demonstrating the underlying model is compatible with Android when the guest rootfs matches the device CPU architecture. The final APK must therefore include separate ABI assets, at minimum `arm64-v8a` for modern Android devices, rather than the existing x86_64 sandbox artifact. Source: [Termux proot-distro](https://github.com/termux/proot-distro).
