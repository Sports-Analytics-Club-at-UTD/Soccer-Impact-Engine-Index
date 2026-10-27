"""Output safety for the optional local diagnostic exporter."""
from pathlib import Path
import tempfile
import unittest
from scripts.export_diagnostic_profiles import ROOT, validate_output


class DiagnosticExportTests(unittest.TestCase):
    def test_repository_outputs_rejected(self):
        for path in (ROOT / "frontend/public/diagnostic.json", ROOT / "data/new.json", ROOT / "new.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_output(path)

    def test_existing_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "existing.json"
            path.write_text("preserve", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_output(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")

    def test_explicit_external_new_json_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.json"
            self.assertEqual(validate_output(path), path.resolve())
            self.assertFalse(path.exists())

    def test_extension_and_parent_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in (Path(folder) / "new.parquet", Path(folder) / "absent/new.json"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    validate_output(path)
