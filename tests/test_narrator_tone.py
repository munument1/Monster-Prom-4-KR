import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('narrator_audit', Path(__file__).resolve().parents[1] / 'scripts/audit_narrator_tone.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class NarratorTone(unittest.TestCase):
    def check(self, text, speaker='narrator'):
        return audit.inspect_tone([{'asset': 'events', 'line': 1, 'speaker': speaker}], {'events': {'entries': [{'line': 1, 'ko': text}]}})

    def test_polite_npc_quote_does_not_make_narrator_polite(self):
        self.assertEqual(self.check('간호사가 물어. "헌혈하러 오셨나요?"')['status'], 'pass')
        self.assertEqual(self.check('간호사가 물어요. "헌혈하러 오셨나요?"')['status'], 'fail')

    def test_alternate_narrator_and_formal_address_are_checked(self):
        self.assertEqual(self.check('당신은 준비됐어.', 'narratorzoe')['status'], 'fail')
        self.assertEqual(self.check('너는 준비됐어.', 'narratorzoe')['status'], 'pass')

    def test_ordinary_nouns_and_infinitives_are_not_polite_endings(self):
        self.assertEqual(self.check('고요 속에서 돌아다니다 담요를 찾아. 중요한 건 죠죠가 아니야.')['status'], 'pass')


if __name__ == '__main__':
    unittest.main()
