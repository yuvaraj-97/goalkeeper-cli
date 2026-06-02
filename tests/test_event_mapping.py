import unittest
from goalkeeper_cli.adapters.claude import ClaudeAdapter
from goalkeeper_cli.adapters.codex import CodexAdapter
from goalkeeper_cli.adapters.antigravity import AntigravityAdapter
from goalkeeper_cli.core.event import GoalKeeperEvent

class TestEventMapping(unittest.TestCase):
    def test_claude_adapter_mapping(self):
        adapter = ClaudeAdapter()
        
        # SessionStart -> session_start
        ev = adapter.translate_event("SessionStart", {"conversationId": "123"})
        self.assertEqual(ev.event_type, "session_start")
        self.assertEqual(ev.source, "Claude")
        self.assertEqual(ev.payload.get("conversationId"), "123")
        
        # PermissionRequest -> permission_required
        ev = adapter.translate_event("PermissionRequest", {"tool_name": "run_command"})
        self.assertEqual(ev.event_type, "permission_required")
        
        # Stop -> task_completed
        ev = adapter.translate_event("Stop", {})
        self.assertEqual(ev.event_type, "task_completed")

        # StopFailure -> task_failed
        ev = adapter.translate_event("StopFailure", {"stop_reason": "error"})
        self.assertEqual(ev.event_type, "task_failed")

    def test_codex_adapter_mapping(self):
        adapter = CodexAdapter()
        
        # SessionStart -> session_start
        ev = adapter.translate_event("SessionStart", {})
        self.assertEqual(ev.event_type, "session_start")
        
        # PermissionRequest -> permission_required
        ev = adapter.translate_event("PermissionRequest", {})
        self.assertEqual(ev.event_type, "permission_required")
        
        # Stop -> task_completed
        ev = adapter.translate_event("Stop", {})
        self.assertEqual(ev.event_type, "task_completed")

    def test_antigravity_adapter_mapping(self):
        adapter = AntigravityAdapter()
        
        # PreToolUse -> permission_required
        ev = adapter.translate_event("PreToolUse", {})
        self.assertEqual(ev.event_type, "permission_required")
        
        # Stop -> task_completed
        ev = adapter.translate_event("Stop", {})
        self.assertEqual(ev.event_type, "task_completed")

if __name__ == "__main__":
    unittest.main()
