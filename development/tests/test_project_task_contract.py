import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEXT = '\n'.join(
    (ROOT / 'ask-claude-and-sol-for-codex' / path).read_text(encoding='utf-8')
    for path in ('SKILL.md', 'agents/openai.yaml')
)


class ProjectTaskContractTest(unittest.TestCase):
    def test_normal_task_lifecycle(self):
        normalized = ' '.join(TEXT.split())
        for marker in ('currently selected saved project', 'normal task',
                       'Archive the normal task', 'task ID', 'read-only'):
            self.assertIn(marker, normalized)
        self.assertNotIn('spawn_agent', TEXT)
        self.assertNotIn('close_agent', TEXT)


if __name__ == '__main__':
    unittest.main()
