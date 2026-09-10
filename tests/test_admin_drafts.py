"""Exercise browser draft lifecycle without contacting the application API."""
import subprocess
import unittest
from pathlib import Path


class AdminDraftTests(unittest.TestCase):
    def test_draft_switching_send_and_lock_lifecycle(self):
        result = subprocess.run(
            ['node', 'tests/admin_drafts_check.js'],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
