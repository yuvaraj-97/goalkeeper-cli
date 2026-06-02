from goalkeeper_cli.adapters.claude import ClaudeAdapter
from goalkeeper_cli.adapters.codex import CodexAdapter
from goalkeeper_cli.adapters.antigravity import AntigravityAdapter

def get_all_adapters():
    return [
        ClaudeAdapter(),
        CodexAdapter(),
        AntigravityAdapter()
    ]
