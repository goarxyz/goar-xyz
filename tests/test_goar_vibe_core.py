import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "goar-production" / "goar_vibe_core.py"
SPEC = importlib.util.spec_from_file_location("goar_vibe_core_test", MODULE_PATH)
CORE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)


class GoarVibeCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "state"
        self.workspace = Path(self.tmp.name) / "workspace"
        self.workspace.mkdir(parents=True)
        self.core = CORE.GoarVibeCore(self.root, self.workspace, "session_test", owner="test-owner")

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_layers_are_trusted_deterministic_and_fingerprinted(self):
        resolver = CORE.GoarConfigResolver({"profile", "max_turns"})
        config = resolver.resolve([
            CORE.ConfigLayer("default", {"profile": "operator", "max_turns": 10}),
            CORE.ConfigLayer("untrusted", {"profile": "plan"}, trusted=False),
            CORE.ConfigLayer("session", {"profile": "accept-edits"}),
        ])
        self.assertEqual(config.values["profile"], "accept-edits")
        self.assertEqual(config.origins["profile"], "session")
        self.assertEqual(len(config.fingerprint), 64)

    def test_plan_requires_valid_lifecycle_transitions_and_persists(self):
        plan = self.core.plan.create("Ship GOAR", ["Test", "Release"])
        self.assertEqual(plan.state, "draft")
        with self.assertRaises(ValueError):
            self.core.plan.transition("executing")
        self.core.plan.transition("approved")
        running = self.core.plan.transition("executing")
        changed = self.core.plan.update_step("step_1", "completed", "passed")
        self.assertEqual(running.state, "executing")
        self.assertEqual(changed.steps[0].status, "completed")
        self.assertEqual(self.core.plan.load().title, "Ship GOAR")

    def test_checkpoint_ledger_captures_workspace_change_and_rejects_escape(self):
        target = self.workspace / "note.txt"
        target.write_text("before", encoding="utf-8")
        self.core.begin_turn("turn_1")
        self.core.ledger.capture_before("note.txt")
        target.write_text("after", encoding="utf-8")
        self.core.ledger.capture_after("note.txt")
        self.core.seal_turn("unit")
        events = self.core.ledger.events()
        self.assertEqual(len(events), 1)
        change = events[0]["changes"][0]
        self.assertNotEqual(change["before"]["digest"], change["after"]["digest"])
        review = self.core.ledger.review(events[0]["id"], "revert")
        self.assertEqual(review["restored"], ["note.txt"])
        self.assertEqual(target.read_text(encoding="utf-8"), "before")
        with self.assertRaises(ValueError):
            self.core.ledger.capture_before("../../escape.txt")

    def test_workspace_trust_grants_and_revokes_explicit_roots(self):
        extra = Path(self.tmp.name) / "trusted-extra"
        extra.mkdir()
        self.assertFalse(self.core.trust.allows(str(extra / "x.txt")))
        self.core.trust.trust(str(extra))
        self.assertTrue(self.core.trust.allows(str(extra / "x.txt")))
        self.core.trust.revoke(str(extra))
        self.assertFalse(self.core.trust.allows(str(extra / "x.txt")))

    def test_loop_manager_validates_persists_and_marks_due_items(self):
        with self.assertRaises(ValueError):
            self.core.loops.create("10s", "too soon")
        loop = self.core.loops.create("30s", "check status")
        self.assertEqual(self.core.loops.due(loop["next_fire_at"] - 1), [])
        due = self.core.loops.due(loop["next_fire_at"] + 1)
        self.assertEqual(due[0]["id"], loop["id"])
        fired = self.core.loops.mark_fired(loop["id"], now=loop["next_fire_at"] + 1)
        self.assertGreater(fired["next_fire_at"], loop["next_fire_at"])
        self.assertTrue(self.core.loops.delete(loop["id"]))

    def test_middleware_and_session_lease_are_enforced(self):
        ok, message = self.core.acquire()
        self.assertTrue(ok, message)
        other = CORE.GoarVibeCore(self.root, self.workspace, "session_test", owner="other-owner")
        second_ok, second_message = other.acquire()
        self.assertFalse(second_ok)
        self.assertIn("active", second_message)
        self.core.release()
        self.assertTrue(other.acquire()[0])
        decision, _ = self.core.before_turn(
            profile="plan", turns=0, max_turns=3, tokens=0, token_budget=100,
            compact_threshold=80, history_size=5,
        )
        self.assertEqual(decision.action, "inject")
        stop, _ = self.core.before_turn(
            profile="operator", turns=3, max_turns=3, tokens=0, token_budget=100,
            compact_threshold=80, history_size=5,
        )
        self.assertEqual(stop.action, "stop")

    def test_event_log_redacts_tool_arguments_to_digests(self):
        self.core.record_tool("secret_tool", {"token": "do-not-store"})
        self.core.record_tool("secret_tool", {"token": "do-not-store"}, "ok")
        events = self.core.events.read()
        material = str(events)
        self.assertNotIn("do-not-store", material)
        self.assertEqual([event["kind"] for event in events], ["tool_call", "tool_result"])


if __name__ == "__main__":
    unittest.main()
