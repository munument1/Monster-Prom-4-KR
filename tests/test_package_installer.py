import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('package_installer', Path(__file__).resolve().parents[1] / 'scripts/package_installer.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PackageInstaller(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'package'
        self.game = self.root / 'game'
        self.game.mkdir()
        (self.game / 'MonsterCon.exe').write_bytes(b'fixture only; never executed')
        (self.game / 'identity.dll').write_bytes(b'fixture build identity')
        self.manifest = {'identities': [{'relative': 'identity.dll', 'sha256': installer.sha(self.game / 'identity.dll')}], 'files': []}
        self.addCleanup(patch.stopall)
        patch.object(installer, 'ROOT', self.package).start()
        patch.object(installer, 'game_closed').start()

    def file(self, name, payload, before=None):
        target = self.package / 'payload' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        allowed = []
        if before is not None:
            old = self.game / name
            old.parent.mkdir(parents=True, exist_ok=True)
            old.write_bytes(before)
            allowed.append(installer.sha(old))
        self.manifest['files'].append({'relative': name, 'sha256': installer.sha(target), 'allowed_before_sha256': allowed})

    def test_install_restores_existing_preview_and_removes_new_files(self):
        self.file('mod/old.txt', b'full Korean', b'preview Korean')
        self.file('mod/new.txt', b'new event')
        self.file('image.bundle', b'already translated image', b'already translated image')
        installer.install(self.game, self.manifest)
        state = json.loads((self.game / '.monstercon-kr-test/state.json').read_text(encoding='utf-8'))
        self.assertEqual(len(state['changes']), 2)
        self.assertEqual((self.game / 'mod/old.txt').read_bytes(), b'full Korean')
        installer.restore(self.game)
        self.assertEqual((self.game / 'mod/old.txt').read_bytes(), b'preview Korean')
        self.assertFalse((self.game / 'mod/new.txt').exists())
        self.assertEqual((self.game / 'image.bundle').read_bytes(), b'already translated image')
        self.assertFalse((self.game / '.monstercon-kr-test').exists())

    def test_unknown_existing_file_is_rejected_before_writes(self):
        self.file('new.txt', b'new')
        (self.game / 'new.txt').write_bytes(b'unknown mod')
        with self.assertRaisesRegex(ValueError, 'Unknown existing file'):
            installer.install(self.game, self.manifest)
        self.assertEqual((self.game / 'new.txt').read_bytes(), b'unknown mod')

    def test_changed_installed_file_is_preserved(self):
        self.file('new.txt', b'new')
        installer.install(self.game, self.manifest)
        (self.game / 'new.txt').write_bytes(b'user edit')
        with self.assertRaisesRegex(ValueError, 'later changes'):
            installer.restore(self.game)
        self.assertEqual((self.game / 'new.txt').read_bytes(), b'user edit')

    def test_failed_copy_rolls_back_and_backups_can_be_cleaned(self):
        self.file('old.txt', b'full Korean', b'preview')
        self.file('new.txt', b'new event')
        original_copy = installer.shutil.copy2
        def broken_copy(source, destination):
            if Path(source) == self.package / 'payload/new.txt':
                Path(destination).write_bytes(b'partial')
                raise OSError('simulated write failure')
            return original_copy(source, destination)
        with patch.object(installer.shutil, 'copy2', side_effect=broken_copy):
            with self.assertRaises(OSError):
                installer.install(self.game, self.manifest)
        self.assertEqual((self.game / 'old.txt').read_bytes(), b'preview')
        self.assertFalse((self.game / 'new.txt').exists())
        installer.restore(self.game)
        self.assertFalse((self.game / '.monstercon-kr-test').exists())

    def test_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'escapes'):
            installer.inside(self.game, '../outside.txt')


if __name__ == '__main__':
    unittest.main()
