# PRoot Deployment and VNC Verification — 2026-08-18

The arm64 Alpine GOAR rootfs was freshly extracted to `/tmp/goar-proot-deploy-rootfs` and deployed through PRoot with QEMU aarch64 emulation, isolated `/data` state/workspace mounts, and the local service bound to `127.0.0.1:18084`.

## Verified Results

| Check | Result |
|---|---|
| GOAR health endpoint | HTTP 200 with `status: ok` |
| Full local workspace route `/` | HTTP 200 |
| Desktop route `/desktop/` | HTTP 200; rendered `GOAR Agent Desktop` |
| noVNC client route `/novnc/vnc.html` | HTTP 200 |
| VNC desktop start endpoint | Returned `mode: novnc_realtime`, `ready: true`, no error |
| RFB port | `127.0.0.1:5900` reachable |
| noVNC WebSocket proxy port | `127.0.0.1:6080` reachable |
| Chromium CDP port | `127.0.0.1:9222` reachable |
| Browser inspection | Desktop page showed `novnc_realtime` and `VNC realtime ready`; the noVNC route opened successfully |

## Repairs Validated During Deployment

The GOAR VNC binary finder now recognizes `/usr/bin/Xvnc` and `/usr/bin/websockify` inside the PRoot guest even when Python's `os.access`/`shutil.which` reports false under QEMU-backed PRoot. The guest shell was able to execute Xvnc and, after the repair, the complete VNC/noVNC stack started successfully.

This evidence covers PRoot deployment and the browser-facing desktop routes. It does not substitute for a physical Android installation test, which remains a separate release gate.

## Browser-Facing noVNC Connection Defect

A direct browser navigation to `/novnc/vnc.html?autoconnect=true&reconnect=true&resize=scale&path=websockify` rendered the noVNC client but showed **“Failed to connect to server”**. This occurred despite the RFB, noVNC WebSocket proxy, and CDP TCP ports being open. The VNC test therefore remains **incomplete**: the WebSocket upgrade/proxy route must be diagnosed and corrected before release.

## Direct noVNC Rendering Result

The same noVNC client was then opened directly through the live websockify service at `http://127.0.0.1:6080/vnc.html?autoconnect=true&reconnect=true&resize=scale&path=websockify`. It completed the connection, exposed a noVNC canvas and disconnect controls, and rendered the guest Chromium desktop. The VNC/noVNC stack is therefore functional.

The remaining issue is limited to GOAR's same-port Flask `/websockify` proxy: it does not complete a browser WebSocket upgrade under the Gunicorn deployment. The Android Computer screen will use the verified direct loopback noVNC endpoint on port 6080, and the GOAR browser UI should be updated to use the same endpoint rather than the failing proxy route.

## Final Loopback noVNC Deployment Check

After changing the noVNC bridge to bind `127.0.0.1:6080` and updating both GOAR and the native Android Computer screen to the direct noVNC route, the rootfs was freshly extracted and redeployed again under PRoot. `POST /v1/desktop/start` returned `mode: novnc_realtime`, `ready: true`, and no error. The PRoot deployment had listeners on RFB port 5900, CDP port 9222, and **loopback-only** noVNC port 6080. The GOAR interface published the direct `:6080/vnc.html` route and the desktop/noVNC HTTP routes returned 200.

The direct noVNC client had already rendered the live Chromium desktop. The PRoot VNC/noVNC deployment gate now passes. Physical Android installation remains a separate release gate.

## Final Vibe-Integrated Release-Candidate Validation — 2026-08-19

**Release-candidate archive:** `goar-alpine-3.22.5-aarch64.tar.gz`

**SHA-256:** `ee8a16a762ceabdc414853c4b0366c9cf1d1d50c908a29e94a335cb61f56b101`

**Size:** `446,072,389` bytes

The final arm64 Alpine archive, including the GOAR Vibe-style control plane, was tested from the archive itself. It was first subjected to an archive safety audit, then extracted using the Java implementation that mirrors the Android installer, and finally deployed through PRoot with QEMU aarch64 emulation. The validation mount set provided the guest its normal `/data` state/workspace mount, `/dev`, `/proc`, `/sys`, and DNS configuration; the GOAR and noVNC HTTP services remained loopback-only.

| Gate | Result | Evidence |
|---|---:|---|
| Archive safety audit | Pass | 23,842 members; 0 unsafe names, 0 unresolved hard-link targets, 0 symlink escapes, and 0 staging symlinks. |
| Android-equivalent extraction | Pass | Java probe extracted all 23,842 members, including 3,341 GNU long-name/link records. |
| Vibe core after extraction | Pass | `/opt/goar/goar_vibe_core.py` was present in the exact extracted rootfs. |
| GOAR health and Vibe status | Pass | `/health` responded and `/v1/core/status` returned `{"ok": true}`. |
| Durable plan API | Pass | `POST /v1/core/plan` created `plan_d1432ca91653` in `draft` state. |
| Scheduled-loop API | Pass | `POST /v1/core/loops` accepted the release-validation loop. |
| Desktop startup API | Pass | `POST /v1/desktop/start` returned `ready: true`. |
| VNC/noVNC transport | Pass | noVNC was served by websockify on `127.0.0.1:6080`; the GOAR backend was live on `127.0.0.1:18085`. |
| Visual desktop rendering | Pass | The browser reported **“Connected (unencrypted) to chrome”** and painted the guest Chromium desktop canvas. |

This final host evidence validates the release archive, Android-installer-equivalent extraction behavior, PRoot startup, GOAR Vibe-core APIs, and noVNC rendering. It does **not** replace the outstanding mandatory physical arm64 Android 8.0+ device gate: first-run download, checksum verification, extraction in app-private storage, foreground-service survival, Android WebView workspace/noVNC interaction, and device logs/screenshots.
