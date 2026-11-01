"""Source-only integrity checks with invented bytes, never private fixtures."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.verify_local_inputs import verify


class LocalInputReceiptTests(unittest.TestCase):
    def test_absent_and_corrupted_inputs_fail_without_modification(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            receipt = [{"path": "invented.json", "bytes": 2, "sha256": hashlib.sha256(b"{}").hexdigest()}]
            self.assertEqual(verify(root, receipt)[0]["status"], "missing")
            path = root / "invented.json"
            path.write_bytes(b"[]")
            self.assertEqual(verify(root, receipt)[0]["status"], "MISMATCH")
            self.assertEqual(path.read_bytes(), b"[]")

    def test_exact_bytes_and_size_both_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "invented.json").write_bytes(b"{}")
            receipt = [{"path": "invented.json", "bytes": 2, "sha256": hashlib.sha256(b"{}").hexdigest()}]
            self.assertEqual(verify(root, receipt)[0]["status"], "match")
            receipt[0]["bytes"] = 3
            self.assertEqual(verify(root, receipt)[0]["status"], "MISMATCH")
