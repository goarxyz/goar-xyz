from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
GOAR_SOURCE = REPO_ROOT / "goar-production" / "goar.py"


class GoarOsIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.goar_home = Path(cls.temp_dir.name) / "state"
        cls.workspace = Path(cls.temp_dir.name) / "workspace"
        cls.goar_home.mkdir()
        cls.workspace.mkdir()

        cls.original_env = {
            name: os.environ.get(name)
            for name in ("GOAR_HOME", "GOAR_WORKSPACE", "GOAR_AUTO_INSTALL_DESKTOP", "GOAR_API_BASE")
        }
        os.environ.update(
            {
                "GOAR_HOME": str(cls.goar_home),
                "GOAR_WORKSPACE": str(cls.workspace),
                "GOAR_AUTO_INSTALL_DESKTOP": "0",
                "GOAR_API_BASE": "http://127.0.0.1:1",
            }
        )

        spec = importlib.util.spec_from_file_location("goar_under_test", GOAR_SOURCE)
        assert spec and spec.loader
        cls.goar = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.goar
        spec.loader.exec_module(cls.goar)

        with (
            patch.object(cls.goar, "apply_setup_to_provider", return_value={}),
            patch.object(cls.goar.JOB_RUNNER, "on_startup", return_value={}),
        ):
            cls.app = cls.goar.create_flask_app()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        browser = getattr(cls.goar, "SHARED_BROWSER", None)
        if browser is not None:
            browser.close()
        for name, value in cls.original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        cls.temp_dir.cleanup()

    def test_branding_is_served_locally(self) -> None:
        response = self.client.get("/brand/logo.png")
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/svg+xml", response.content_type)
        self.assertIn(b"<svg", response.data)

    def test_workspace_file_round_trip_uses_mounted_workspace(self) -> None:
        payload = {"path": "notes.txt", "content": "GOAR OS workspace"}
        created = self.client.post("/v1/workspace/file", json=payload)
        self.assertEqual(created.status_code, 200)
        self.assertTrue((self.workspace / "uploads" / "notes.txt").is_file())

        fetched = self.client.get("/v1/workspace/file?path=uploads/notes.txt")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["content"], "GOAR OS workspace")

    def test_workspace_rejects_path_escape(self) -> None:
        response = self.client.post(
            "/v1/workspace/file",
            json={"path": "../outside.txt", "content": "blocked"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse((Path(self.temp_dir.name) / "outside.txt").exists())

    def test_runtime_does_not_auto_install_desktop_dependencies_by_default(self) -> None:
        self.assertEqual(self.goar.VNC_DESKTOP._bootstrap_binaries(), {"skipped": "GOAR_AUTO_INSTALL_DESKTOP disabled"})

    def test_operator_profiles_enforce_tool_policy(self) -> None:
        self.assertTrue(self.goar.operator_profile_allows_tool("operator", "bash")[0])
        self.assertTrue(self.goar.operator_profile_allows_tool("plan", "read_file")[0])
        allowed, denial = self.goar.operator_profile_allows_tool("plan", "write_file")
        self.assertFalse(allowed)
        self.assertIn("PROFILE POLICY DENIED", denial)
        self.assertTrue(self.goar.operator_profile_allows_tool("accept-edits", "write_file")[0])
        self.assertFalse(self.goar.operator_profile_allows_tool("accept-edits", "bash")[0])
        self.assertFalse(self.goar.operator_profile_allows_tool("explore", "web_fetch")[0])

    def test_operator_profile_api_persists_per_session(self) -> None:
        agent = SimpleNamespace(
            _operator_profile="operator",
            _session_id="profile_api_test",
            _history=[],
            _session_tokens=0,
            model="test-model",
        )
        with patch.object(self.goar, "get_or_create_agent", return_value=agent):
            changed = self.client.post("/v1/operator/profile", json={"profile": "plan", "session_id": "profile_api_test"})
            self.assertEqual(changed.status_code, 200)
            self.assertEqual(changed.get_json()["profile"]["id"], "plan")
            inspected = self.client.get("/v1/operator/profile?session_id=profile_api_test")
            self.assertEqual(inspected.status_code, 200)
        self.assertEqual(inspected.get_json()["profile"]["id"], "plan")
        stored = self.goar.SESSION_STORE.load("profile_api_test")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["profile"], "plan")


if __name__ == "__main__":
    unittest.main()
