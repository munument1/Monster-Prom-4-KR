import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build_playtest.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class TranslationContract(unittest.TestCase):
    def test_missing_control_token_rejected(self):
        with self.assertRaisesRegex(ValueError, 'control token'):
            builder.verify_line('Hello %PLAYERNAME%', '안녕', 'test')

    def test_changed_stat_rejected(self):
        with self.assertRaisesRegex(ValueError, 'stat effect'):
            builder.verify_line('+2 FUN', '+2 CHARM 증가', 'test')

    def test_changed_number_rejected(self):
        with self.assertRaisesRegex(ValueError, 'number'):
            builder.verify_line('Choose 3', '2개 선택', 'test')

    def test_fun_particle_boundary(self):
        self.assertEqual(builder.game_safe_stat_effects('+2 FUN을 얻었다'), '+2 FUN\u200b을 얻었다')

    def test_control_only_and_quoted_silence(self):
        builder.verify_line('%CURRENTPLAYERNAME%!', '%CURRENTPLAYERNAME%!', 'test')
        builder.verify_line('"..."', '"..."', 'test')

    def test_untranslated_stage_direction_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing Hangul'):
            builder.verify_line('[LOUD NOISES]', '[LOUD NOISES]', 'test')

    def test_reviewed_number_localization_is_hash_pinned(self):
        import hashlib
        english, korean = 'Five minutes', '5분'
        builder.CONTRACT_EXCEPTIONS['test'] = {
            'english_sha256': hashlib.sha256(english.encode()).hexdigest(),
            'korean_sha256': hashlib.sha256(korean.encode()).hexdigest(),
            'allow_number_localization': True,
        }
        try:
            builder.verify_line(english, korean, 'test')
            with self.assertRaisesRegex(ValueError, 'exception source/translation changed'):
                builder.verify_line(english, '6분', 'test')
        finally:
            del builder.CONTRACT_EXCEPTIONS['test']


if __name__ == '__main__':
    unittest.main()
