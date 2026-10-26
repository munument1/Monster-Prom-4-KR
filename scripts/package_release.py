"""Publishable archive wrapper around the byte-identical validated QA6 payload."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'v0.1.0'
SOURCE = ROOT / 'build/releases/Monster-Con-KR-test-QA6-Windows-DragDrop.zip'
SOURCE_SHA = 'b22a0c5bf3d8661ae581eb5258c3135bf82d2d7dd8668a0e7fae417657e4f311'
OUTPUT = ROOT / 'build/releases' / ('Monster-Con-KR-' + VERSION + '-Windows-DragDrop.zip')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if sha(SOURCE.read_bytes()) != SOURCE_SHA:
        raise ValueError('Validated QA6 archive changed')
    files = {}
    with zipfile.ZipFile(SOURCE) as archive:
        manifest = json.loads(archive.read('MONSTERCON_KR_MANIFEST.json'))
        for name, expected in manifest['files'].items():
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or ':' in name or '\\' in name:
                raise ValueError('Unexpected archive destination: ' + name)
            if any(part.lower() in {'userdata', 'work', 'backups'} for part in relative.parts):
                raise ValueError('Private data in archive')
            data = archive.read(name)
            if sha(data) != expected:
                raise ValueError('QA6 file hash mismatch: ' + name)
            if name != 'MONSTERCON-KR-사용법.txt':
                files[name] = data
    files['README-KO.md'] = (ROOT / 'docs/RELEASE_v0.1.0.md').read_bytes()
    hashes = {name: sha(data) for name, data in sorted(files.items())}
    release_manifest = {
        'kind': 'Windows-dragdrop-release', 'version': VERSION, 'bridge_version': '0.1.7',
        'text_fields': 24274, 'unique_image_textures': 49,
        'game_build_identities': manifest['game_build_identities'], 'files': hashes,
        'validation': 'QA6 game payload unchanged; user confirmed in-game play; further extraction audit ongoing.',
        'private_save_data_included': False,
    }
    files['MONSTERCON_KR_MANIFEST.json'] = (json.dumps(release_manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with zipfile.ZipFile(OUTPUT, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(OUTPUT) as archive:
        if len(archive.namelist()) != len(files) or set(archive.namelist()) != set(files):
            raise ValueError('Release ZIP member mismatch')
        for name, data in files.items():
            if sha(archive.read(name)) != sha(data):
                raise ValueError('Release ZIP integrity mismatch: ' + name)
    checksum = sha(OUTPUT.read_bytes())
    checksum_path = OUTPUT.parent / ('SHA256SUMS-' + VERSION + '.txt')
    checksum_path.write_text(checksum + '  ' + OUTPUT.name + '\n', encoding='ascii')
    print('ZIP=' + str(OUTPUT))
    print('CHECKSUMS=' + str(checksum_path))
    print(f'PASS files={len(files)} bytes={OUTPUT.stat().st_size} SHA256={checksum}; QA6 game payload unchanged')


if __name__ == '__main__':
    main()
