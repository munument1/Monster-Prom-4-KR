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


if __name__ == '__main__':
    unittest.main()
