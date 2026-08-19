import hashlib
import json
import tarfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANDROID = REPO_ROOT / "android-alpine"
JAVA = ANDROID / "app" / "src" / "main" / "java" / "com" / "goar" / "alpine"
CONTROLLER = JAVA / "GoarRuntimeController.java"
ACTIVITY = JAVA / "GoarAlpineActivity.java"
SERVICE = JAVA / "GoarRuntimeService.java"
MANIFEST_XML = ANDROID / "app" / "src" / "main" / "AndroidManifest.xml"
BUILD_GRADLE = ANDROID / "app" / "build.gradle"
ROOTFS_MANIFEST = ANDROID / "goar-alpine-vibe-rootfs-arm64-v8a.json"
ROOTFS_ARCHIVE = REPO_ROOT / "proot" / "goar-alpine-vibe-3.24.1-aarch64.tar.gz"
ROOTFS_BUILDER = REPO_ROOT / "proot" / "build-alpine-vibe-rootfs.sh"


class AlpineVibeAndroidContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controller = CONTROLLER.read_text(encoding="utf-8")
        cls.activity = ACTIVITY.read_text(encoding="utf-8")
        cls.service = SERVICE.read_text(encoding="utf-8")
        cls.manifest = MANIFEST_XML.read_text(encoding="utf-8")
        cls.gradle = BUILD_GRADLE.read_text(encoding="utf-8")

    def test_is_a_separate_alpine_application(self) -> None:
        self.assertIn("namespace 'com.goar.alpine'", self.gradle)
        self.assertIn("applicationId 'com.goar.alpine'", self.gradle)
        self.assertIn("goar-alpine-vibe-v1", self.gradle)
        self.assertNotIn("com.goar.os", self.gradle)

    def test_manifest_exposes_only_the_single_terminal_activity(self) -> None:
        self.assertIn('android:name=".GoarAlpineActivity"', self.manifest)
        self.assertIn('android:name=".GoarRuntimeService"', self.manifest)
        for retired_surface in (
            "MainActivity",
            "GoarConsoleActivity",
            "GoarWorkspaceActivity",
            "GoarControlActivity",
            "GoarConfigActivity",
            "GoarPackageActivity",
        ):
            self.assertNotIn(retired_surface, self.manifest)
        self.assertIn('android:stopWithTask="true"', self.manifest)

    def test_activity_starts_only_the_full_upstream_tui_terminal(self) -> None:
        self.assertIn("runtime.openVibeTerminal", self.activity)
        self.assertIn("GoarTerminalView", self.activity)
        self.assertIn("SYSTEM_UI_FLAG_IMMERSIVE_STICKY", self.activity)
        self.assertNotIn("appendSystemLine", self.activity)
        self.assertNotIn("Button", self.activity)
        self.assertNotIn("GoarConsoleActivity", self.activity)

    def test_runtime_requires_alpine_full_tui_markers_and_launcher(self) -> None:
        for asset in (
            '"usr/local/bin/goar-alpine-vibe"',
            '"opt/goar-alpine-vibe/.venv/bin/vibe"',
            '"etc/goar-alpine-vibe/rootfs-release"',
            'command.add("exec /usr/local/bin/goar-alpine-vibe")',
        ):
            self.assertIn(asset, self.controller)
        for retired_asset in (
            '"usr/local/bin/goar-terminal"',
            '"opt/vibehack/.venv/bin/vibehack"',
            '"exec /usr/local/bin/goar-terminal"',
        ):
            self.assertNotIn(retired_asset, self.controller)
        self.assertIn('command.add("/bin/sh")', self.controller)
        self.assertIn('command.add("-ec")', self.controller)
        for forbidden in (
            "openDirectTerminal",
            "startDurableLoopDaemon",
            "/opt/vibehack/",
            "GOAR_DISABLE_LOOPS",
            "goar_loopd.py",
        ):
            self.assertNotIn(forbidden, self.controller)

    def test_runtime_keeps_verified_proot_and_network_mount_contract(self) -> None:
        for marker in (
            '"libproot.so"',
            '"libproot-loader.so"',
            '"libproot-loader32.so"',
            '"libtalloc.so"',
            'command.add("/dev")',
            'command.add("/proc")',
            'command.add("/sys")',
            '":/etc/resolv.conf"',
            '"PROOT_LOADER"',
        ):
            self.assertIn(marker, self.controller)
        self.assertIn("type == 'x'", self.controller)
        self.assertIn("parsePaxAttributes(byte[] value)", self.controller)

    def test_service_is_installer_only_without_a_background_guest_loop(self) -> None:
        self.assertIn("ACTION_INSTALL", self.service)
        self.assertIn("START_NOT_STICKY", self.service)
        self.assertIn("stopSelf()", self.service)
        for forbidden in ("loopDaemon", "ensureLoopDaemon", "startDurableLoopDaemon", "START_STICKY"):
            self.assertNotIn(forbidden, self.service)

    def test_manifest_matches_the_final_alpine_archive(self) -> None:
        manifest = json.loads(ROOTFS_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["architecture"], "arm64-v8a")
        self.assertTrue(manifest["rootfs_url"].endswith("/goar-alpine-vibe-3.24.1-aarch64.tar.gz"))
        self.assertEqual(manifest["version"], "alpine-private-vibe-v1.0.0")
        self.assertRegex(manifest["rootfs_sha256"], r"^[0-9a-f]{64}$")
        if ROOTFS_ARCHIVE.is_file():
            self.assertEqual(manifest["rootfs_size"], ROOTFS_ARCHIVE.stat().st_size)
            self.assertEqual(
                manifest["rootfs_sha256"],
                hashlib.sha256(ROOTFS_ARCHIVE.read_bytes()).hexdigest(),
            )

    @unittest.skipUnless(ROOTFS_ARCHIVE.is_file(), "large Alpine release asset is built outside Git")
    def test_archive_retains_full_tui_but_excludes_requested_runtime_removals(self) -> None:
        with tarfile.open(ROOTFS_ARCHIVE, mode="r:gz") as archive:
            members = {item.name.lstrip("./") for item in archive.getmembers()}
        required = {
            "usr/local/bin/goar-alpine-vibe",
            "opt/goar-alpine-vibe/vibe/cli/textual_ui/app.py",
            "opt/goar-alpine-vibe/vibe/core/agent_loop/_loop.py",
            "opt/goar-alpine-vibe/vibe/setup/onboarding/__init__.py",
            "etc/goar-alpine-vibe/rootfs-release",
        }
        self.assertTrue(required.issubset(members), sorted(required - members))
        forbidden_fragments = (
            "opt/goar-alpine-vibe/tests/",
            "opt/goar-alpine-vibe/scripts/",
            "vibe/cli/audio_player/",
            "vibe/cli/audio_recorder/",
            "vibe/cli/transcribe/",
            "site-packages/opentelemetry",
            "site-packages/mistralai/extra/tests/",
        )
        self.assertFalse(
            any(fragment in member for member in members for fragment in forbidden_fragments)
        )

    def test_builder_prunes_non_runtime_privacy_fixtures(self) -> None:
        builder = ROOTFS_BUILDER.read_text(encoding="utf-8")
        for marker in (
            '"$ROOTFS/opt/goar-alpine-vibe/tests"',
            '"$ROOTFS/opt/goar-alpine-vibe/scripts"',
            "opentelemetry-api",
            "-name tests -prune -exec rm -rf {} +",
        ):
            self.assertIn(marker, builder)


if __name__ == "__main__":
    unittest.main()
