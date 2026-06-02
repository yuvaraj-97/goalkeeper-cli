import unittest
from unittest.mock import patch, MagicMock
from goalkeeper_cli.core.event import GoalKeeperEvent
from goalkeeper_cli.core.dispatcher import dispatch_event

class TestNotificationDispatch(unittest.TestCase):
    @patch('goalkeeper_cli.core.dispatcher.load_config')
    @patch('goalkeeper_cli.providers.telegram.TelegramProvider.send')
    @patch('goalkeeper_cli.core.dispatcher.write_audit_log')
    def test_dispatch_session_start(self, mock_audit, mock_send, mock_load_config):
        mock_load_config.return_value = {
            "telegram_bot_token": "token",
            "telegram_chat_id": 12345
        }
        
        with patch('goalkeeper_cli.core.dispatcher.load_queue', return_value=[]), \
             patch('goalkeeper_cli.core.dispatcher.add_to_queue') as mock_add:
             
            event = GoalKeeperEvent(source="Claude", event_type="session_start", payload={})
            dispatch_event(event)
            
            # Session start should schedule proactive quota refresh
            mock_add.assert_called_once()
            mock_audit.assert_called_once()
            mock_send.assert_not_called()  # We don't send notification for session start itself

    @patch('goalkeeper_cli.core.dispatcher.load_config')
    @patch('goalkeeper_cli.providers.telegram.TelegramProvider.send')
    def test_dispatch_permission_required(self, mock_send, mock_load_config):
        mock_load_config.return_value = {
            "telegram_bot_token": "token",
            "telegram_chat_id": 12345
        }
        
        # Tool call requiring permission (not in list of allowed/trusted commands/paths)
        event = GoalKeeperEvent(
            source="Claude",
            event_type="permission_required",
            payload={
                "tool_name": "run_command",
                "tool_input": {"CommandLine": "rm -rf /"}
            }
        )
        dispatch_event(event)
        mock_send.assert_called_once()
        self.assertIn("Permission Required", mock_send.call_args[0][0])

    @patch('goalkeeper_cli.core.dispatcher.load_config')
    @patch('goalkeeper_cli.providers.telegram.TelegramProvider.send')
    def test_dispatch_task_completed(self, mock_send, mock_load_config):
        # 1. Completion alert disabled
        mock_load_config.return_value = {
            "telegram_bot_token": "token",
            "telegram_chat_id": 12345,
            "notify_on_completion": False
        }
        event = GoalKeeperEvent(source="Claude", event_type="task_completed", payload={})
        dispatch_event(event)
        mock_send.assert_not_called()

        # 2. Completion alert enabled
        mock_load_config.return_value = {
            "telegram_bot_token": "token",
            "telegram_chat_id": 12345,
            "notify_on_completion": True
        }
        dispatch_event(event)
        mock_send.assert_called_once()
        self.assertIn("Turn Completed", mock_send.call_args[0][0])

if __name__ == "__main__":
    unittest.main()
