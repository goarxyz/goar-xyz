# GOAR production package

This package contains the cleaned GOAR autonomous agent, its dependency-free terminal wrapper, and a production Flask service entry point. The Flask service is intended to run behind a reverse proxy or private network boundary; it binds to loopback by default.

## Installation

Create a dedicated service account and install the package under `/opt/goar`. Create a virtual environment and install the pinned dependency ranges:

```bash
sudo useradd --system --home /var/lib/goar --shell /usr/sbin/nologin goar || true
sudo install -d -o goar -g goar /opt/goar /var/lib/goar /var/lib/goar/workspace /etc/goar
sudo cp -a . /opt/goar/
cd /opt/goar
sudo -u goar python3 -m venv .venv
sudo -u goar .venv/bin/pip install --upgrade pip
sudo -u goar .venv/bin/pip install -r requirements.txt
sudo cp .env.example /etc/goar/goar.env
sudo chown goar:goar /etc/goar/goar.env
sudo chmod 600 /etc/goar/goar.env
```

Edit `/etc/goar/goar.env` and provide the selected provider credentials. Do not place credentials in source files, command-line arguments, service definitions, or logs. Set `GOAR_REQUIRE_KEY` when the service is reachable by any network other than a trusted local reverse proxy.

## Flask service

For a foreground production launch:

```bash
cd /opt/goar
set -a; . /etc/goar/goar.env; set +a
./run_flask.sh
```

For persistent operation with systemd:

```bash
sudo install -m 0644 goar.service /etc/systemd/system/goar.service
sudo systemctl daemon-reload
sudo systemctl enable --now goar.service
sudo systemctl status goar.service
curl --fail http://127.0.0.1:8080/health
```

The service deliberately uses one Gunicorn worker because GOAR maintains durable job recovery, browser/VNC state, and an in-process agent loop. Multiple workers would create independent stateful runtimes. Threaded request handling remains enabled for concurrent health, API, and streaming requests.

## CLI wrapper

Run an interactive terminal session:

```bash
cd /opt/goar
set -a; . /etc/goar/goar.env; set +a
./run_cli.sh
```

Run an initial task and then remain interactive:

```bash
./run_cli.sh "Inspect the workspace and summarize pending work"
```

The wrapper invokes `goar.py -cli`. When Textual is installed, the legacy terminal interface is used; otherwise GOAR uses its standard-library terminal interface with reasoning, tool-call, tool-result, and response output.

## Operational checks

The primary readiness endpoint is `GET /health`. Confirm the JSON response has `status: "ok"`, a ready agent, and the expected provider. The job state is available through `GET /v1/jobs`; protect this and all other API endpoints with `GOAR_REQUIRE_KEY` when the service is not strictly local.

Logs are emitted to standard output and standard error for systemd or container collection. GOAR's durable runtime data is stored under `GOAR_HOME`, and agent workspace files are stored under `GOAR_WORKSPACE`. Back up these directories before upgrades or migrations.

## Upgrade and rollback

Stop the service, replace the application files while preserving `/var/lib/goar`, reinstall dependencies, and restart the service. To roll back, restore the previous package directory and restart systemd. Verify `/health`, `/v1/jobs`, and a read-only workspace request after every change.
