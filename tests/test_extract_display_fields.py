import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('extractor', Path(__file__).resolve().parents[1] / 'scripts/extract_assets.py')
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


class DisplayFields(unittest.TestCase):
    def test_comic_answer_includes_choice_and_all_replacement_variants(self):
        line = '>comic_answer\tcharm\t\t[choice]3 memes.[n][r1]3 memes.[n][r2]3 memes'
        column = extractor.ordinary_display_field(line)
        self.assertEqual(column, 3)
        self.assertEqual(line.split('\t')[column], '[choice]3 memes.[n][r1]3 memes.[n][r2]3 memes')

    def test_non_display_directives_are_not_translated(self):
        self.assertIsNone(extractor.ordinary_display_field('>comic_type\tshonen'))
        self.assertIsNone(extractor.ordinary_display_field('>special_command\tcomic\t\tcommand argument'))


if __name__ == '__main__':
    unittest.main()
