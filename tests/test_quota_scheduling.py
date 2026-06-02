import unittest
from unittest.mock import patch, MagicMock
from goalkeeper_cli.core.dispatcher import parse_limit_duration, add_to_queue, schedule_reset_alert

class TestQuotaScheduling(unittest.TestCase):
    def test_parse_limit_duration_relative(self):
        # 45 minutes
        self.assertEqual(parse_limit_duration("resets in 45m"), 45 * 60)
        # 2 hours 15 minutes
        self.assertEqual(parse_limit_duration("try again in 2h 15m"), 2 * 3600 + 15 * 60)
        # 1 hour
        self.assertEqual(parse_limit_duration("resets in 1h"), 3600)

    def test_parse_limit_duration_fallback(self):
        # Keyword match
        self.assertEqual(parse_limit_duration("you hit a rate limit error"), 5 * 3600)
        # No match
        self.assertIsNone(parse_limit_duration("just a regular completion message"))

    @patch('goalkeeper_cli.core.dispatcher.load_queue')
    @patch('goalkeeper_cli.core.dispatcher.save_queue')
    def test_add_to_queue(self, mock_save, mock_load):
        mock_load.return_value = [
            {"source": "Claude", "text": "previous quota alert", "timestamp": 100}
        ]
        
        add_to_queue("token", 12345, 200, "Claude", "⏰ *[Claude] Rate Limit Reset!* Your Claude quota has refreshed.")
        
        # Should deduplicate Claude quota alerts
        mock_save.assert_called_once()
        saved_queue = mock_save.call_args[0][0]
        self.assertEqual(len(saved_queue), 1)
        self.assertIn("quota", saved_queue[0]["text"].lower())

if __name__ == "__main__":
    unittest.main()
