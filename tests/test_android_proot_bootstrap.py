from __future__ import annotations

import hashlib
import json
import tarfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_SOURCE = (
    REPO_ROOT
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "com"
    / "goar"
    / "os"
    / "GoarRuntimeController.java"
)
JNI_ARM64_DIR = REPO_ROOT / "android" / "app" / "src" / "main" / "jniLibs" / "arm64-v8a"
ROOTFS_MANIFEST = REPO_ROOT / "android" / "goar-rootfs-arm64-v8a.json"
KALI_ROOTFS = REPO_ROOT / "proot" / "goar-kali-terminal-arm64.tar.gz"
PTY_BRIDGE_SOURCE = REPO_ROOT / "android" / "app" / "src" / "main" / "cpp" / "goar_terminal_jni.c"
PTY_BRIDGE_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarPtyBridge.java"
TERMINAL_VIEW_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarTerminalView.java"
RUNTIME_SERVICE_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarRuntimeService.java"
MANIFEST_XML = REPO_ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
LOOP_DAEMON_SOURCE = REPO_ROOT / "proot" / "kali-terminal-overlay" / "opt" / "goar-terminal" / "goar_loopd.py"
WORKSPACE_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarWorkspaceActivity.java"
CONSOLE_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarConsoleActivity.java"
CONFIG_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarConfigActivity.java"
PACKAGE_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarPackageActivity.java"
CONTROL_JAVA = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "goar" / "os" / "GoarControlActivity.java"
KAI_MODEL_ARM64_SHA256 = {
    "libproot.so": "452fcfe761d398e6d1180e60c9b5039fcabdba06d8d73e803c5bb866905d2a8c",
    "libproot-loader.so": "cb5e5b6900e198ca8160e9d355ea5b98d646333887a769411ff74132c1cec5df",
    "libtalloc.so": "15a8101160fee241e15b241d49bc288c3bd902b0334e34020a1c54e47760a1f7",
}


class AndroidProotBootstrapContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = CONTROLLER_SOURCE.read_text(encoding="utf-8")

    def test_versioned_talloc_soname_is_materialized_for_proot(self) -> None:
        self.assertIn('new File(nativeRuntimeDir, "libtalloc.so.2")', self.source)
        self.assertIn("prepareNativeRuntimeLibraries(talloc)", self.source)
        self.assertIn('"LD_LIBRARY_PATH"', self.source)
        self.assertIn(
            "runtimeLibraryDirectory.getAbsolutePath() + File.pathSeparator + nativeDirectory.getAbsolutePath()",
            self.source,
        )

    def test_complete_kai_model_dual_loader_payload_is_required(self) -> None:
        for name in ("libproot.so", "libproot-loader.so", "libproot-loader32.so", "libtalloc.so"):
            self.assertIn(f'"{name}"', self.source)
        self.assertNotIn('"libgoar_proot.so"', self.source)
        self.assertNotIn('"libgoar_loader.so"', self.source)
        self.assertNotIn('"libandroid-shmem.so"', self.source)

    def test_native_directory_contains_exactly_the_complete_dual_loader_set(self) -> None:
        self.assertEqual(
            {entry.name for entry in JNI_ARM64_DIR.iterdir() if entry.is_file()},
            {"libproot.so", "libproot-loader.so", "libproot-loader32.so", "libtalloc.so"},
        )

    def test_native_payload_matches_the_pinned_kai_model_build(self) -> None:
        for name, expected_hash in KAI_MODEL_ARM64_SHA256.items():
            actual_hash = hashlib.sha256((JNI_ARM64_DIR / name).read_bytes()).hexdigest()
            self.assertEqual(actual_hash, expected_hash, name)

    def test_launcher_has_standard_android_proot_mounts_and_working_directory(self) -> None:
        self.assertIn('command.add("/dev");', self.source)
        self.assertIn('command.add("/proc");', self.source)
        self.assertIn('command.add("/sys");', self.source)
        self.assertIn('command.add("-w");', self.source)
        self.assertIn('command.add("/data/workspace");', self.source)

    def test_launcher_supplies_complete_guest_bootstrap_environment(self) -> None:
        for name in ("PATH", "TERM", "LANG", "TMPDIR", "PROOT_TMP_DIR", "PROOT_LOADER"):
            self.assertIn(f'"{name}"', self.source)

    def test_installer_requires_terminal_first_kali_assets(self) -> None:
        for asset in (
            '"usr/local/bin/goar-terminal"',
            '"opt/vibehack/.venv/bin/vibehack"',
            '"opt/goar-terminal/GOAR_TERMINAL_PROMPT.md"',
        ):
            self.assertIn(asset, self.source)
        self.assertIn("openTerminal", self.source)
        for retired in ("waitForHealth", "goar-serve", "127.0.0.1:8080"):
            self.assertNotIn(retired, self.source)

    def test_kali_literal_backslash_filename_is_not_rejected(self) -> None:
        self.assertNotIn('name.contains("\\\\")', self.source)
        self.assertIn('name.contains("../")', self.source)
        self.assertIn("getCanonicalFile", self.source)

    def test_manifest_pins_existing_kali_terminal_archive(self) -> None:
        manifest = json.loads(ROOTFS_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["architecture"], "arm64-v8a")
        self.assertTrue(manifest["rootfs_url"].endswith("/goar-kali-terminal-arm64.tar.gz"))
        self.assertRegex(manifest["rootfs_sha256"], r"^[0-9a-f]{64}$")
        self.assertGreater(manifest["rootfs_size"], 0)
        self.assertEqual(manifest["version"], "kali-terminal-v1.1.1")
        if KALI_ROOTFS.is_file():
            self.assertEqual(manifest["rootfs_size"], KALI_ROOTFS.stat().st_size)
            self.assertEqual(manifest["rootfs_sha256"], hashlib.sha256(KALI_ROOTFS.read_bytes()).hexdigest())

    @unittest.skipUnless(KALI_ROOTFS.is_file(), "large Kali release asset is published outside Git")
    def test_kali_terminal_archive_contains_required_guest_entrypoints(self) -> None:
        with tarfile.open(KALI_ROOTFS, mode="r:gz") as archive:
            members = {item.name.lstrip("./") for item in archive.getmembers()}
        required = {
            "usr/local/bin/goar-terminal",
            "usr/local/bin/goarctl",
            "opt/goar-terminal/goar_interactive.py",
            "opt/goar-terminal/goar_loopd.py",
            "opt/goar-terminal/goar_vibe_core.py",
            "opt/vibehack/.venv/bin/vibehack",
        }
        self.assertTrue(required.issubset(members), sorted(required - members))
        self.assertIn("etc/systemd/user/app-org.kde.plasma\\x2dwelcome@autostart.service", members)
        forbidden = ("flask", "novnc", "websockify", "chromium")
        self.assertFalse(any(any(term in member.lower() for term in forbidden) for member in members))

    def test_foreground_service_owns_durable_loop_runtime(self) -> None:
        service = RUNTIME_SERVICE_JAVA.read_text(encoding="utf-8")
        manifest = MANIFEST_XML.read_text(encoding="utf-8")
        loopd = LOOP_DAEMON_SOURCE.read_text(encoding="utf-8")
        self.assertIn("startDurableLoopDaemon", self.source)
        self.assertIn('environment.put("GOAR_DISABLE_LOOPS", "1")', self.source)
        self.assertIn("ensureLoopDaemon", service)
        self.assertIn("START_STICKY", service)
        self.assertIn('android:stopWithTask="false"', manifest)
        self.assertIn('GOAR_LOOP_TURN_TIMEOUT", "0"', loopd)
        self.assertIn("if TURN_TIMEOUT > 0", loopd)

    def test_operator_console_keeps_terminal_and_agent_chat_isolated(self) -> None:
        workspace = WORKSPACE_JAVA.read_text(encoding="utf-8")
        console = CONSOLE_JAVA.read_text(encoding="utf-8")
        manifest = MANIFEST_XML.read_text(encoding="utf-8")
        self.assertIn("openDirectTerminal", self.source)
        self.assertIn('command.add("exec /bin/bash -l")', self.source)
        self.assertIn("MODE_TERMINAL", workspace)
        self.assertIn("MODE_AGENT", workspace)
        self.assertIn("runtime.openDirectTerminal", workspace)
        self.assertIn("runtime.openTerminal", workspace)
        self.assertIn("Direct Terminal never receives agent", console)
        for activity in ("GoarConsoleActivity", "GoarControlActivity", "GoarConfigActivity", "GoarPackageActivity"):
            self.assertIn(activity, manifest)

    def test_native_configuration_and_package_workflows_are_private_and_explicit(self) -> None:
        config = CONFIG_JAVA.read_text(encoding="utf-8")
        package = PACKAGE_JAVA.read_text(encoding="utf-8")
        control = CONTROL_JAVA.read_text(encoding="utf-8")
        self.assertIn("saveAgentConfiguration", self.source)
        self.assertIn("home/.vibehack/.env", self.source)
        self.assertIn("TYPE_TEXT_VARIATION_PASSWORD", config)
        self.assertIn("CUSTOM PACKAGE NAMES ARE REQUIRED", package)
        self.assertIn("apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --", package)
        self.assertIn("goarctl loop list", control)
        self.assertIn("goarctl events --limit 25", control)

    def test_native_pty_bridge_and_terminal_surface_are_present(self) -> None:
        bridge = PTY_BRIDGE_SOURCE.read_text(encoding="utf-8")
        bridge_java = PTY_BRIDGE_JAVA.read_text(encoding="utf-8")
        terminal_view = TERMINAL_VIEW_JAVA.read_text(encoding="utf-8")
        self.assertIn("openpty", bridge)
        self.assertIn("fork", bridge)
        self.assertIn("exec", bridge)
        self.assertIn("System.loadLibrary(\"goar_terminal_jni\")", bridge_java)
        self.assertIn("interface InputSink", terminal_view)
        self.assertIn("setInputSink", terminal_view)


if __name__ == "__main__":
    unittest.main()
