"""Regression tests for the independent field census."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "audit_extraction_coverage",
    Path(__file__).resolve().parents[1] / "scripts/audit_extraction_coverage.py",
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ExtractionCoverageSchema(unittest.TestCase):
    def test_comic_answer_and_choice(self):
        self.assertEqual(audit.display_field("english_events_comic",
                         ">comic_answer\t0\t\t[choice]Hello[n][r1]Goodbye"), 3)
        self.assertEqual(audit.display_field("english_events_maingame",
                         ">choice\t0\t\tAsk for directions"), 3)

    def test_separate_prologue_formats(self):
        self.assertEqual(audit.display_field("english_prologue_likes",
                         ">>>\tlike_01\tCollecting Katanas\tomen"), 2)
        self.assertEqual(audit.display_field("english_prologue_conpopquiz",
                         ">question\tChoose 3\t\t"), 1)
        self.assertEqual(audit.display_field("english_prologue_conpopquiz",
                         ">image\tasset\tCute animal"), 2)

    def test_structural_fields_not_mistaken_for_dialogue(self):
        self.assertIsNone(audit.display_field("english_events_challenge",
                         ">>>\tchallenge 1\t\t\tANIMAL"))
        self.assertIsNone(audit.display_field("english_events_comic",
                         ">special_command\tcomic\t\tcmd"))
        self.assertIsNone(audit.display_field("english_events_chibidates",
                         "\tplayer\tdefault"))

    def test_independent_census_counts(self):
        fields = audit.expected_fields(
            "english_events_comic",
            ">>>\tcomic_a\n>comic_answer\tcharm\t\t[choice]Hello[n][r1]Bye\n",
        )
        self.assertEqual(fields, [("english_events_comic", 1, 3)])


if __name__ == "__main__":
    unittest.main()
