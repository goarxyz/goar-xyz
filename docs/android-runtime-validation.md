# Android Runtime Validation Record

This document distinguishes completed verification from work that requires a physical Android device. It is a release-control record, not a claim that an emulator test passed.

## Completed Independent Checks

| Validation item | Result |
|---|---|
| Android SDK build of the arm64 APK | Successful |
| Archive semantic audit of the full arm64 rootfs | Passed: 23,841 records; 3,164 directories; 19,702 regular files; 974 symbolic links; 1 hard link; no unsafe member, target, or staging-path link |
| Installer-equivalent extraction of the full arm64 archive | Passed after GNU long-record and forward-hard-link handling were added |
| Fresh PRoot deployment of the arm64 rootfs | Passed: GOAR health, workspace, VNC, and noVNC exercised |
| noVNC browser rendering through direct loopback websockify | Passed; live Chromium desktop rendered |
| Android x86_64 emulator validation APK | Built with an ABI-matched x86_64 PRoot bootstrap and a full local x86_64 rootfs test manifest |

## Emulator Constraints Observed

No physical Android device is attached to this environment (`adb devices` returned no devices).

An Android 35 ARM64 Test Device image was provisioned, but the host Android Emulator rejected it because an ARM64 guest image is not supported by the x86_64 QEMU2 emulator on this host. An x86_64 Android 35 Test Device image was then provisioned to test the installer logic with an ABI-matched PRoot bootstrap and x86_64 rootfs. That emulator could not start because the sandbox host does not expose `/dev/kvm`, and this emulator version requires hardware acceleration for x86_64 guests.

## Mandatory Final Device Gate

The arm64 release cannot be called complete until it has been installed on a real Android arm64 device, the first-run download and extraction have completed, GOAR health has started, the native Workspace screen has loaded the local GOAR UI, and the Computer screen has rendered the loopback noVNC desktop. The release process must retain the resulting device log and screenshot evidence.
