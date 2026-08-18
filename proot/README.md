# GOAR OS Alpine PRoot Distribution

This directory builds and runs **GOAR OS as a contained Alpine Linux application environment**. The generated root filesystem includes the existing GOAR Flask backend, its Python dependencies, Chromium, the VNC/noVNC desktop stack, and the embedded web console. The host only supplies a maintained `proot` executable and a browser for the local interface.

> PRoot is a user-space filesystem boundary rather than a virtual machine. The contained application uses the host kernel and network stack, while its Alpine filesystem, GOAR state, and operator workspace remain separated through explicit rootfs and bind-mount paths. [1]

## Quick start

Install PRoot using your operating system’s maintained package manager. Build the Alpine root filesystem, then invoke the application command. The launcher opens `http://127.0.0.1:8080/` in the default browser when possible.

```bash
# Debian or Ubuntu host
sudo apt-get install proot

# From the repository root
./goar-proot build
./goar-proot app
```

The first launch creates `proot/goar.env`. Add a provider configuration there before submitting tasks that require live model access. GOAR can still start without a provider, but it will return its built-in setup guidance rather than execute live agent calls. A successful build writes an architecture-specific archive named `proot/goar-alpine-<version>-<arch>.tar.gz`; `./goar-proot load` restores that archive without rebuilding.

| Command | Purpose |
| --- | --- |
| `./goar-proot build` | Downloads a verified Alpine mini-rootfs, installs the contained runtime, and emits a portable rootfs archive. |
| `./goar-proot load` | Restores `proot/rootfs/` from the generated archive when the directory is absent. |
| `./goar-proot app` | Starts the complete Flask backend in the background, verifies readiness, and opens the local web application. |
| `./goar-proot serve` | Runs the full backend in the foreground and writes output to the terminal. |
| `./goar-proot status` | Displays the launcher process and authenticated health response. |
| `./goar-proot stop` | Stops the background service started by `app`. |
| `./goar-proot shell` | Opens a shell inside the Alpine PRoot filesystem with GOAR data and workspace mounted. |

## Filesystem and persistence

The rootfs is based on Alpine’s official mini-rootfs distribution, which Alpine documents for container and minimal-chroot use cases. [2] The launcher does not bind the host source repository into the running environment. It binds only the persistent state, workspace, temporary area, device files, system information, and resolver required by the contained service.

| Host path | Guest path | Contents |
| --- | --- | --- |
| `proot/rootfs/` | `/` | Generated Alpine system and GOAR application runtime. |
| `proot/state/goar/` | `/data/goar` | Sessions, jobs, skills, configuration, logs, and other durable GOAR state. |
| `proot/workspace/` | `/data/workspace` | Files exposed to the GOAR workspace API and operator. |
| `proot/state/tmp/` | `/tmp` | Ephemeral browser, VNC, and temporary application files. |
| `proot/goar.env` | Loaded by launcher | Local provider and access-key configuration; never committed. |

## Service boundary

`goar-serve` in the rootfs starts the same `wsgi:application` Flask service that the Compose distribution uses. It defaults to `127.0.0.1:8080`, checks that non-local bindings have a `GOAR_REQUIRE_KEY`, and passes the Alpine Chromium path to GOAR’s Playwright fallback. The complete control surface remains available through the normal GOAR web application: chat and task execution, sessions, workspace files and downloads, durable jobs, setup and providers, skills, MCP configuration, browser operations, and the agent-desktop/noVNC fallback.

The rootfs includes VNC/noVNC and Chromium so the backend has all of its existing desktop dependencies. Alpine does not provide a compatible prebuilt Python Playwright wheel for its musl environment. The build therefore combines Alpine’s native `greenlet`, `pyee`, Chromium, and Node packages with the portable Playwright client, and uses a small contained driver wrapper so browser automation works through GOAR’s shared Chromium/CDP desktop path. This is assembled at build time; no host package manager is invoked after launch.

PRoot cannot supply a separate kernel, hardware virtualization, or Android application packaging. It is a local Linux application distribution for systems that can run PRoot and an architecture-matched Alpine mini-rootfs. [1] [2]

## Security and operating considerations

The default listener is loopback-only. Set `GOAR_REQUIRE_KEY` before changing `GOAR_HOST` to any non-loopback value. The PRoot launcher binds no host directory except the specific state and workspace paths shown above; nevertheless, PRoot is not a hardened virtual-machine security boundary because it uses the host kernel and explicitly passes through the selected host resources. [1]

The build script verifies the published Alpine SHA-256 checksum before extracting the mini-rootfs. It then installs all normal runtime packages at build time. The resulting runtime does not invoke a host package manager, and `GOAR_AUTO_INSTALL_DESKTOP` remains disabled so GOAR does not attempt package installation after launch. The generated rootfs archive and local `state/`, `workspace/`, and `goar.env` contents are ignored by Git because they may contain operational data or credentials.

## References

[1] [PRoot project documentation](https://proot-me.github.io/)

[2] [Alpine Linux downloads](https://alpinelinux.org/downloads/)
