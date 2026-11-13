#!/usr/bin/env python3
"""Offline negative controls: invalid or missing pinned bytes must never PASS."""
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import audit


class SourceIntegrityTests(unittest.TestCase):
    def test_empty_git_blob_matches_git_spec(self):
        self.assertEqual(
            audit.git_blob_sha(b""),
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
        )

    def test_wrong_blob_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "tampered.txt").write_text("unexpected bytes\n")
            with patch.dict(audit.SOURCES, {"tampered.txt": "0" * 40}, clear=True):
                result, clean = audit.run_audit(root)
            self.assertFalse(clean)
            self.assertEqual(result["source_files"][0]["integrity"], "FAIL")
            self.assertEqual(
                result["epistemic_state"]["source_byte_integrity"], "UNKNOWN"
            )

    def test_missing_blob_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(audit.SOURCES, {"missing.txt": "0" * 40}, clear=True):
                result, clean = audit.run_audit(pathlib.Path(directory))
            self.assertFalse(clean)
            self.assertEqual(result["source_files"][0]["integrity"], "ERROR")


if __name__ == "__main__":
    unittest.main()
