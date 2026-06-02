import unittest
from unittest.mock import patch
from pathlib import Path
from goalkeeper_cli.adapters.claude import ClaudeAdapter
from goalkeeper_cli.adapters.codex import CodexAdapter
from goalkeeper_cli.adapters.antigravity import AntigravityAdapter

class TestAdapterDetection(unittest.TestCase):
    @patch('pathlib.Path.is_dir')
    def test_claude_adapter_detection(self, mock_is_dir):
        adapter = ClaudeAdapter()
        
        # We need to make sure the call is checking for the specific folder
        # Path.home() / ".claude"
        def side_effect(path_self):
            # If the path ends with .claude, return our mocked value
            if path_self.name == ".claude":
                return True
            return False
            
        with patch.object(Path, 'is_dir', side_effect):
            self.assertTrue(adapter.is_installed())

        def side_effect_false(path_self):
            return False
            
        with patch.object(Path, 'is_dir', side_effect_false):
            self.assertFalse(adapter.is_installed())

    def test_codex_adapter_detection(self):
        adapter = CodexAdapter()
        
        def side_effect(path_self):
            if path_self.name == ".codex":
                return True
            return False
            
        with patch.object(Path, 'is_dir', side_effect):
            self.assertTrue(adapter.is_installed())

        def side_effect_false(path_self):
            return False
            
        with patch.object(Path, 'is_dir', side_effect_false):
            self.assertFalse(adapter.is_installed())

    def test_antigravity_adapter_detection(self):
        adapter = AntigravityAdapter()
        
        def side_effect(path_self):
            if path_self.name == ".gemini":
                return True
            return False
            
        with patch.object(Path, 'is_dir', side_effect):
            self.assertTrue(adapter.is_installed())

        def side_effect_false(path_self):
            return False
            
        with patch.object(Path, 'is_dir', side_effect_false):
            self.assertFalse(adapter.is_installed())

if __name__ == "__main__":
    unittest.main()
