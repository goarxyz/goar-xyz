from __future__ import annotations

import hashlib
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
KAI_MODEL_ARM64_SHA256 = {
    "libproot.so": "452fcfe761d398e6d1180e60c9b5039fcabdba06d8d73e803c5bb866905d2a8c",
    "libproot-loader.so": "cb5e5b6900e198ca8160e9d355ea5b98d646333887a769411ff74132c1cec5df",
    "libproot-loader32.so": "35a88fcbec6a3d54914c7a056a2a8a93e098722a0165e3d58eb174c63acd66d8",
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


if __name__ == "__main__":
    unittest.main()
