import unittest
from unittest.mock import patch

import openai_math_model_identity as m


def fixtures():
    block = m.START + "\n" + "def experimental (x : Nat) : Nat := x\n" + m.END
    return {"challenge.lean": block.encode(), "model.lean": ("-- header\n" + block + "\n-- trailing\n").encode()}


def test_audit(files):
    config = {
        "challenge": ("challenge.lean", m.blob_sha(files["challenge.lean"])),
        "solution_model": ("model.lean", m.blob_sha(files["model.lean"])),
    }
    with patch.dict(m.SOURCES, config, clear=True):
        return m.audit(lambda path: files[path])


class ModelIdentityTests(unittest.TestCase):
    def test_matching_blocks_preserve_source_only_boundary(self):
        result = test_audit(fixtures())
        self.assertEqual(result["status"], "WARRANTED_PINNED_MODEL_TEXT_IDENTITY")
        self.assertIsNone(result["compiled_declarations_equal"])
        self.assertEqual(result["comparator_default_definition_holes"], 20)

    def test_different_definition_body_rejected(self):
        f = fixtures()
        f["model.lean"] = f["model.lean"].replace(b":= x", b":= x + 1")
        with self.assertRaisesRegex(ValueError, "MODEL_SOURCE_MISMATCH"):
            test_audit(f)

    def test_changed_pinned_blob_rejected(self):
        f = fixtures()
        refs = {
            "challenge": ("challenge.lean", m.blob_sha(f["challenge.lean"])),
            "solution_model": ("model.lean", m.blob_sha(f["model.lean"])),
        }
        f["model.lean"] += b"altered"
        with patch.dict(m.SOURCES, refs, clear=True):
            with self.assertRaisesRegex(ValueError, "SOURCE_BLOB_MISMATCH"):
                m.audit(lambda path: f[path])

    def test_missing_end_rejected(self):
        with self.assertRaisesRegex(ValueError, "MODEL_END_NOT_FOUND"):
            m.model_block(m.START)

    def test_duplicate_start_rejected(self):
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_MODEL_START"):
            m.model_block(m.START + m.END + m.START)


if __name__ == "__main__":
    unittest.main()
