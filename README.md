# GOAR OS

**GOAR OS** is a local-first autonomous-agent environment packaged as one reproducible service. It combines the GOAR web console, durable sessions and jobs, an editable workspace, a shared browser, and an optional browser-accessible desktop. The distribution now starts as an isolated container rather than requiring a host-level service installation, package-manager access, or a system-wide Python environment.

> GOAR OS contains the **agent operating environment**. It does not embed model weights or credentials. Configure an OpenAI-compatible provider, including a local provider, before asking the agent to perform model-backed work.

| Component | Responsibility | Persistence boundary |
| --- | --- | --- |
| GOAR service | Web console, API, sessions, tools, browser orchestration, and agent loop | `goar-state` container volume |
| Workspace | Files the operator and agent are intended to create, read, and modify | `./workspace` host directory |
| Desktop | Xvnc, noVNC, Chromium, and the shared browser control surface | Ephemeral runtime state |
| Provider configuration | API endpoint, model choice, and optional credential | `.env` or the local setup flow |

## Quick start

Install Docker Engine together with the Docker Compose plugin. Copy the template, create the local workspace, set a model provider, and launch the operating environment. The default network binding is loopback-only, so the console is reachable on the same machine at `http://127.0.0.1:8080/`.

```bash
git clone https://github.com/goarxyz/goar-xyz.git goar-os
cd goar-os
make init

# Edit .env and set GOAR_API_KEY, GOAR_API_BASE, and GOAR_MODEL as appropriate.
# Generate a key before exposing GOAR beyond the local machine:
# openssl rand -hex 32

make up
make status
```

The first build downloads the base image and Python dependencies. Later starts reuse the local image and the `goar-os-state` volume. Use `make logs` for service logs, `make shell` for an administrative shell inside the running container, and `make down` to stop the service without deleting durable agent state.

## Configuration

The checked-in [`.env.example`](.env.example) contains the supported startup variables. Copy it to `.env`; this local file is intentionally ignored by Git. GOAR accepts the generic `GOAR_API_*` values and the `FREEAI_*` aliases already supported by the original runtime.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOAR_BIND_ADDRESS` | `127.0.0.1` | Host interface published by Compose. Keep this loopback-only unless a trusted reverse proxy is used. |
| `GOAR_PORT` | `8080` | Host port for the GOAR console and API. |
| `GOAR_UID` / `GOAR_GID` | `1000` / `1000` | Linux user and group IDs used inside the container so new workspace files remain host-editable. Set them to `id -u` and `id -g` when needed. |
| `GOAR_REQUIRE_KEY` | Empty | Shared API key required by protected endpoints. Set this for any non-local deployment. |
| `GOAR_API_KEY` | Empty | Credential for an OpenAI-compatible provider. |
| `GOAR_API_BASE` | Empty | Provider base URL, such as a locally hosted OpenAI-compatible endpoint. |
| `GOAR_MODEL` | Empty | Provider model identifier. |
| `FREEAI_API_*` | Empty/template values | Compatibility aliases for the existing Free.ai configuration path. |

## Security model

The Compose service binds only to `127.0.0.1` by default, runs as an unprivileged user, drops Linux capabilities, uses a read-only application filesystem, and writes only to the named state volume, mounted workspace, and ephemeral `/tmp`. The container never invokes a package manager after startup; its desktop/browser dependencies are baked into the image. Cross-origin access is disabled unless `GOAR_CORS_ORIGINS` is explicitly configured.

`GOAR_REQUIRE_KEY` protects API routes with an `X-API-Key` or `Authorization: Bearer` header. The browser console is designed for same-origin use, so the simplest secure deployment is local access or a reverse proxy that handles TLS and authentication. Do not bind GOAR directly to a public interface without an access key and a deliberate reverse-proxy policy.

The workspace API now exposes only `GOAR_WORKSPACE` (`/workspace` in the container). It no longer offers the application source tree or GOAR configuration directory through the file browser. State, credentials configured through the user interface, session history, and job data are kept in the private state volume rather than the editable workspace.

## Daily operation

The agent console is served at the root URL. Its local desktop fallback is available at `/desktop/`; when the bundled desktop stack is available, the console can also open a noVNC-backed shared browser desktop. The service health endpoint is `/health`, and its OpenAI-compatible model listing is `/v1/models`.

```bash
# View service state and health response.
make status

# Follow logs while the agent works.
make logs

# Stop without deleting workspace or agent state.
make down

# Rebuild after pulling changes.
git pull --ff-only
make up
```

To reset all durable agent state, explicitly remove the named volume. This does not remove the checked-out repository or `./workspace`.

```bash
docker volume rm goar-os-state
```

## Development and validation

The runtime lives in [`goar-production/`](goar-production/). The root scaffolding is intentionally not required for operation; Docker Compose is the canonical run path. The test suite validates that branding is served from the local image, agent file operations stay inside the mounted workspace, and desktop dependency installation is disabled during normal runtime.

```bash
make test
make check
```

| Path | Role |
| --- | --- |
| [`compose.yaml`](compose.yaml) | Local-first service definition, network binding, volume mounts, and runtime hardening. |
| [`goar-production/Dockerfile`](goar-production/Dockerfile) | Reproducible GOAR OS image containing Python, Chromium, VNC/noVNC, and runtime libraries. |
| [`goar-production/docker-entrypoint.sh`](goar-production/docker-entrypoint.sh) | Minimal state initialization; it never installs packages. |
| [`goar-production/goar.py`](goar-production/goar.py) | GOAR’s main agent runtime, API, desktop integration, and console. |
| [`workspace/`](workspace/) | Operator-managed project files exposed to the agent. |
| [`tests/test_goar_os.py`](tests/test_goar_os.py) | Offline regression tests for local asset delivery and workspace isolation. |

## Native deployment

A systemd-oriented native installation remains available in [`goar-production/README.md`](goar-production/README.md) for operators who intentionally manage dependencies on the host. The container path is recommended for a self-contained installation because it packages the desktop, browser, Python dependencies, and application runtime together.
