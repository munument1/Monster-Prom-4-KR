"""Create a verified local Windows overwrite ZIP from the combined test package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=ROOT / 'build/releases/MonsterCon-KR-test-20261026-QA4')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/releases/Monster-Con-KR-test-QA4-Windows-DragDrop')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--bridge-only', action='store_true', help='Package only the updated bridge for an existing Korean installation')
    mode.add_argument('--narrator-hotfix', action='store_true', help='Include bridge and event files changed by the narrator voice review')
    args = parser.parse_args()
    package, out = args.package.resolve(), args.output.resolve()
    source_manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    bridge = 'BepInEx/plugins/MonsterConKoreanBridge/MonsterConKoreanBridge.dll'
    changed_assets = set()
    if args.narrator_hotfix:
        changed_assets = {row['asset'] for row in json.loads((ROOT / 'docs/NARRATOR_TONE_CHANGES.json').read_text(encoding='utf-8'))['entries']}
    hotfix_names = {bridge} | {'MonsterCon_Data/StreamingAssets/game_assets/texts/' + name + '.txt' for name in changed_assets}
    # The byte-identical payload already passed the full text/image audits.
    files = {}
    for record in source_manifest['files']:
        name = record['relative']
        if args.bridge_only and name != bridge:
            continue
        if args.narrator_hotfix and name not in hotfix_names:
            continue
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or ':' in name or '\\' in name:
            raise ValueError('Invalid archive destination: ' + name)
        path = package / 'payload' / name
        if digest(path) != record['sha256']:
            raise ValueError('Combined payload changed: ' + name)
        if name in files:
            raise ValueError('Duplicate archive destination: ' + name)
        files[name] = path
    out.mkdir(parents=True, exist_ok=False)
    for name, source in files.items():
        destination = out / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    readme = out / 'MONSTERCON-KR-사용법.txt'
    readme_source = 'docs/NARRATOR_AND_STATS_HOTFIX_KO.txt' if args.narrator_hotfix else ('docs/STAT_LABEL_HOTFIX_KO.txt' if args.bridge_only else 'docs/DRAGDROP_INSTALL_KO.txt')
    shutil.copy2(ROOT / readme_source, readme)
    is_hotfix = args.bridge_only or args.narrator_hotfix
    for source in ([] if is_hotfix else sorted((ROOT / 'docs/licenses').glob('*.txt'))):
        destination = out / 'licenses' / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    packaged = {p.relative_to(out).as_posix(): digest(p) for p in sorted(out.rglob('*')) if p.is_file()}
    field_count = sum(json.loads((ROOT / 'docs/TEXT_QA_REPORT.json').read_text(encoding='utf-8'))['counts_by_asset'][name] for name in changed_assets)
    kind = 'narrator-and-stat-hotfix-for-existing-installation' if args.narrator_hotfix else ('bridge-hotfix-for-existing-installation' if args.bridge_only else 'local-Windows-dragdrop-playtest')
    manifest = {'kind': kind, 'title': source_manifest['title'],
                'text_fields': field_count if args.narrator_hotfix else (0 if args.bridge_only else source_manifest['text_fields']),
                'unique_image_textures': 0 if is_hotfix else source_manifest['unique_image_textures'],
                'game_build_identities': source_manifest['identities'], 'files': packaged,
                'game_launched': False, 'game_modified_during_packaging': False,
                'automatic_backup': False, 'contains_patched_game_assets': not is_hotfix}
    manifest_path = out / 'MONSTERCON_KR_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    expected = {**packaged, manifest_path.name: digest(manifest_path)}
    archive_path = out.parent / (out.name + '.zip')
    with zipfile.ZipFile(archive_path, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(expected):
            archive.write(out / name, name)
    with zipfile.ZipFile(archive_path) as archive:
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise ValueError('Unexpected ZIP members')
        for name, expected_sha in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                raise ValueError('ZIP member hash mismatch: ' + name)
    checksum = digest(archive_path)
    archive_path.with_suffix('.zip.sha256.txt').write_text(checksum + '  ' + archive_path.name + '\n', encoding='ascii')
    print('FOLDER=' + str(out))
    print('ZIP=' + str(archive_path))
    print(f'PASS files={len(expected)} bytes={archive_path.stat().st_size} SHA256={checksum}')


if __name__ == '__main__':
    main()
