---
name: GOAR Chromium lib bundling
description: How to find and bundle Playwright Chromium headless shell libs on Replit/NixOS without slow /nix/store scans
---

## Problem
Playwright's chrome-headless-shell needs libgbm.so.1, libxkbcommon.so.0, and others not on LD_LIBRARY_PATH.
ldd hangs on Chrome (special ELF). find /nix/store takes 12+ seconds (721k entries).

## Solution

### Get NEEDED libs (static, cannot hang)
readelf -d with compatible awk (no lookbehind, no gensub):
```bash
readelf -d "$binary" | awk '/\(NEEDED\)/ {
  line=$0; idx=index(line,"[")
  if(idx>0){rest=substr(line,idx+1); end=index(rest,"]")
    if(end>0) print substr(rest,1,end-1)}}'
```

### Find Nix lib dirs (instant — parse PATH)
PATH has /nix/store/<hash>-<pkg>/bin for every activated package. Strip /bin to get pkg root, add /lib:
```bash
IFS=: read -ra PDIRS <<< "$PATH"
for d in "${PDIRS[@]}"; do
  [[ "$d" != /nix/store/* ]] && continue
  pkg_root="${d%/bin}"
  [ -d "$pkg_root/lib" ] && NIX_LIB_DIRS+=("$pkg_root/lib")
done
```

### The mesa-libgbm exception
libgbm.so.1 is in a SEPARATE output with no /bin dir — not in PATH.
Find it via the Nix store DB (instant):
```bash
mesa_pkg=$(printf '%s\n' "${PDIRS[@]}" | grep '/nix/store/[^/]*-mesa-[0-9]' | grep -v 'cross_tools\|spirv\|opencl' | head -1)
mesa_root="${mesa_pkg%/bin}"
nix-store --query --references "$mesa_root" | grep gbm
# Returns: /nix/store/wilz94hzz4q3fss6qvv625zvww4a6s4s-mesa-libgbm-25.0.1
```

### Files
- artifacts/api-server/bundle-libs.sh — build-time bundler (uses above approach)
- artifacts/api-server/build-goar.sh — calls bundle-libs.sh after playwright install
- artifacts/api-server/run-goar.sh — prepends bundled-libs/ to LD_LIBRARY_PATH
- goar-production/bundled-libs/ — .gitignored dir with .so files

**Why:** ls /nix/store takes 12s; ldd hangs on Chrome; readelf + PATH is instant and correct.
**How to apply:** Any time Playwright Chromium fails with missing .so on Replit/NixOS.
