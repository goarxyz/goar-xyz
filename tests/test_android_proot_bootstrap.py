from __future__ import annotations

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
