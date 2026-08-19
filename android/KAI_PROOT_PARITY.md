# Kai-Model Android PRoot Runtime Contract

This document freezes the Android PRoot model reproduced for GOAR. It is based on the audited implementation in [`SimonSchubert/Kai`](https://github.com/SimonSchubert/Kai), specifically `build-proot.sh`, `LinuxPaths.kt`, `ProotLauncher.kt`, and `LinuxSandboxManager.kt` as read on 2026-08-19.

## Pinned Native Build Inputs

| Input | Required value |
|---|---|
| PRoot source | `https://github.com/termux/proot.git` |
| PRoot revision | `4dba3afbf3a63af89b4d9c1a59bf2bda10f4d10f` |
| Talloc version | `2.4.3` |
| Android minimum API | `26` |
| Primary GOAR APK ABI | `arm64-v8a` |
| Companion loader ABI | `armeabi-v7a` for the arm64 package's 32-bit tracee loader |

The source build must configure PRoot with a relative `PROOT_UNBUNDLE_LOADER` fallback and package matching artifacts from the same build. The old GOAR Termux-derived payload is not compatible with this contract and must not remain in the APK.

## Required APK Native Payload

The repaired arm64 package must contain exactly this matching PRoot set below `lib/arm64-v8a/`:

| File | Purpose |
|---|---|
| `libproot.so` | PRoot executable, built against `libtalloc.so.2`. |
| `libproot-loader.so` | Matching arm64 PRoot tracee loader. |
| `libproot-loader32.so` | Matching armv7 tracee loader for 32-bit binaries encountered from the arm64 host process. |
| `libtalloc.so` | Talloc library whose ELF soname is `libtalloc.so.2`. |

Android strips the `.so.2` suffix when packaging JNI artifacts. Before PRoot starts, GOAR must copy the packaged `libtalloc.so` to `Context.getFilesDir()/goar/native-runtime/libtalloc.so.2`, then put that app-private directory first in `LD_LIBRARY_PATH`. The PRoot executable itself and both loader files remain executable from `ApplicationInfo.nativeLibraryDir`.

## Required Launch Contract

GOAR must launch the matching `libproot.so` directly from `nativeLibraryDir`, with these PRoot invariants: `--rootfs=<app-private rootfs>`, binds for `/dev`, `/proc`, `/sys`, and the app-private temporary directory at `/tmp`; `-0`; an explicit guest working directory; and the matching `PROOT_LOADER` path. The process environment must include `HOME`, guest `PATH`, `TERM`, `LANG`, `TMPDIR`, `PROOT_TMP_DIR`, `PROOT_LOADER`, and `LD_LIBRARY_PATH`.

The rootfs, workspace, service state, temporary files, compatibility talloc copy, and logs stay below app-private `filesDir/goar`. Only Android virtual system mounts and loopback networking are exposed to the guest. The app-private runtime directory is used only to provide Bionic a filename matching PRoot’s required talloc soname; it does not expose host storage to the guest.

## Parity Gates

The build is not accepted until the following hold:

1. The source-build provenance matches the pinned PRoot revision, talloc version, and API level in this document.
2. The four required native files are present in the arm64 APK.
3. `libproot.so` requires `libtalloc.so.2`, `libproot-loader.so` is present, and `libproot-loader32.so` is present.
4. GOAR materializes `libtalloc.so.2` in its app-private runtime directory and launches the exact names above.
5. The native payload contains no old `libgoar_*` or `libandroid-shmem.so` artifacts.
6. Repository regression tests and a signed APK package verification pass.

## Reference

Kai is licensed under Apache-2.0. This document records an independently implemented compatibility contract; GOAR does not copy Kai application code. The PRoot and talloc components retain their own upstream licensing and notices.
