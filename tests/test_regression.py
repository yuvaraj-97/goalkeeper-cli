import unittest
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

class TestRegression(unittest.TestCase):
    def test_adapter_modules_import(self):
        # Verify adapter modules import successfully
        from goalkeeper_cli.adapters.claude import ClaudeAdapter
        from goalkeeper_cli.adapters.codex import CodexAdapter
        from goalkeeper_cli.adapters.antigravity import AntigravityAdapter
        
        self.assertIsNotNone(ClaudeAdapter())
        self.assertIsNotNone(CodexAdapter())
        self.assertIsNotNone(AntigravityAdapter())

    def test_install_hook_valid_python_booleans(self):
        # Verify install hook JSON uses valid Python booleans before serialization
        # (This is tested by ensuring that calling install_hooks does not raise NameError due to lowercase true/false)
        from goalkeeper_cli.adapters.claude import ClaudeAdapter
        from goalkeeper_cli.adapters.codex import CodexAdapter
        from goalkeeper_cli.adapters.antigravity import AntigravityAdapter

        claude = ClaudeAdapter()
        codex = CodexAdapter()
        antigravity = AntigravityAdapter()

        # Mock path existence checks and write operations to check install_hooks
        # For Claude
        with patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data='{}')) as mock_file:
            try:
                claude.install_hooks()
            except NameError as e:
                self.fail(f"ClaudeAdapter.install_hooks failed with NameError: {e}")

        # For Codex
        with patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data='{}')) as mock_file:
            try:
                codex.install_hooks()
            except NameError as e:
                self.fail(f"CodexAdapter.install_hooks failed with NameError: {e}")

        # For Antigravity
        with patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data='{}')) as mock_file:
            try:
                antigravity.install_hooks()
            except NameError as e:
                self.fail(f"AntigravityAdapter.install_hooks failed with NameError: {e}")

    def test_manual_schedule_preserves_multi_token_times(self):
        # Verify manual schedule preserves multi-token times when parsed
        from goalkeeper_cli.notify import run_manual_schedule
        
        # Mock sys.argv for --schedule-manual
        with patch('sys.argv', ['notify.py', '--schedule-manual', 'Claude', '5h', '15m']), \
             patch('goalkeeper_cli.notify.run_manual_schedule') as mock_run:
            from goalkeeper_cli.notify import main
            try:
                main()
                mock_run.assert_called_once_with('Claude', '5h 15m')
            except Exception as e:
                self.fail(f"Failed parsing multi-token schedule: {e}")

    @patch('goalkeeper_cli.notify.load_queue')
    @patch('goalkeeper_cli.providers.telegram.TelegramProvider.send_with_config')
    def test_cron_processing_sends_queued_credentials(self, mock_send_with_config, mock_load_queue):
        # Verify cron processing sends queued item credentials, not current global config
        import time
        from goalkeeper_cli.notify import run_cron_processing
        
        mock_load_queue.return_value = [
            {
                "timestamp": int(time.time()) - 10,
                "token": "queued_token",
                "chat_id": 99999,
                "text": "Alert text",
                "proxy_url": "https://queued.proxy/notify"
            }
        ]
        
        with patch('sys.exit') as mock_exit:
            run_cron_processing()
            mock_send_with_config.assert_called_once_with(
                text="Alert text",
                token="queued_token",
                chat_id=99999,
                proxy_url="https://queued.proxy/notify"
            )

    def test_readme_no_home_trader_links(self):
        # Verify README does not contain "file:///home/trader"
        readme_path = Path(__file__).parent.parent / "README.md"
        self.assertTrue(readme_path.exists())
        content = readme_path.read_text()
        self.assertNotIn("file:///home/trader", content)

if __name__ == "__main__":
    unittest.main()
