---
name: GOAR Replit workflow env
description: How Replit injects LD_LIBRARY_PATH and where nix package libs live for the workflow process
---

## Key findings (from /proc/<pid>/environ of running gunicorn)

1. Replit AUTOMATICALLY sets LD_LIBRARY_PATH=<workspace>/goar-production/bundled-libs in the workflow env
2. PATH has /nix/store/<hash>-<pkg>/bin for EVERY activated nix package from .replit
3. ~/.nix-profile is essentially empty — Replit does not use standard nix-env
4. nix-store --query works against the Nix store DB and is fast for reference queries
5. uv pip install --python .pythonlibs/bin/python3 -r requirements.txt installs into the workspace venv
   (.pythonlibs has no pip module; raw "pip install" hits the NixOS externally-managed guard)

## Nix package paths (stable-25_05, Aug 2026)
- mesa main: /nix/store/cpwib3zazj49fm0y04y53w4xkbqsgrgm-mesa-25.0.7
- mesa-libgbm: /nix/store/wilz94hzz4q3fss6qvv625zvww4a6s4s-mesa-libgbm-25.0.1
- libxkbcommon: /nix/store/sisfq9wihyqqjzmrpik9b4xksifw97ha-libxkbcommon-1.8.1

**Why:** Knowing this prevents hours debugging why standard nix commands don't find installed packages.
**How to apply:** Whenever working with native binaries or Playwright on Replit.
