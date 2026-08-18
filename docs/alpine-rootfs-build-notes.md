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
