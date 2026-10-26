"""Local combined test-patch installer. Uses only the Python standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
DEFAULT_GAME = Path(r'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f'Path escapes installation root: {relative}')
    return path


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def game_closed():
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq MonsterCon.exe', '/FO', 'CSV', '/NH'],
                            check=True, capture_output=True)
    if b'"MonsterCon.exe"' in result.stdout:
        raise RuntimeError('Close Monster Con before installing/restoring. The game was not stopped.')


def preflight(game, manifest):
    if not (game / 'MonsterCon.exe').is_file():
        raise ValueError(f'MonsterCon.exe not found: {game}')
    for record in manifest['identities']:
        target = inside(game, record['relative'])
        if not target.is_file() or sha(target) != record['sha256']:
            raise ValueError(f'Unsupported or changed game build: {record["relative"]}')
    seen = set()
    for record in manifest['files']:
        relative = record['relative']
        if relative.casefold() in seen:
            raise ValueError(f'Duplicate destination: {relative}')
        seen.add(relative.casefold())
        payload = inside(ROOT / 'payload', relative)
        if not payload.is_file() or sha(payload) != record['sha256']:
            raise ValueError(f'Package integrity mismatch: {relative}')
        target = inside(game, relative)
        if target.exists():
            if not target.is_file() or sha(target) not in {record['sha256'], *record['allowed_before_sha256']}:
                raise ValueError(f'Unknown existing file; refusing to overwrite: {relative}')
        elif record.get('required_existing'):
            raise ValueError(f'Missing original image asset: {relative}')


def install(game, manifest):
    game_closed()
    state_root = game / '.monstercon-kr-test'
    state_path = state_root / 'state.json'
    if state_root.exists():
        raise ValueError('Prior test-patch backup exists. Restore that package first: ' + str(state_root))
    preflight(game, manifest)
    changes = []
    # Complete and verify every required backup before modifying any game file.
    try:
        for record in manifest['files']:
            target = inside(game, record['relative'])
            if target.exists() and sha(target) == record['sha256']:
                continue
            change = {'relative': record['relative'], 'sha256': record['sha256'], 'before_sha256': sha(target) if target.exists() else None}
            if target.exists():
                backup = inside(state_root / 'backup', record['relative'])
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                if sha(backup) != change['before_sha256']:
                    raise ValueError('Backup integrity mismatch: ' + record['relative'])
            changes.append(change)
        write_json(state_path, {'game': str(game), 'status': 'prepared', 'changes': changes})
    except BaseException:
        # No game files have changed at this stage. Preserve any successful backups.
        raise
    copied = []
    try:
        for change in changes:
            copied.append(change)
            target = inside(game, change['relative'])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inside(ROOT / 'payload', change['relative']), target)
            if sha(target) != change['sha256']:
                raise ValueError('Installed integrity mismatch: ' + change['relative'])
        write_json(state_path, {'game': str(game), 'status': 'installed', 'changes': changes})
    except BaseException:
        for change in reversed(copied):
            target = inside(game, change['relative'])
            if change['before_sha256'] is None:
                target.unlink(missing_ok=True)
            else:
                shutil.copy2(inside(state_root / 'backup', change['relative']), target)
        write_json(state_path, {'game': str(game), 'status': 'rolled_back', 'changes': changes})
        raise
    print(f'INSTALLED: {len(changes)} changed files; text + UI + manual. Game was not launched.')
    print('Backup/state: ' + str(state_path))


def restore(game):
    game_closed()
    root = inside(game, '.monstercon-kr-test')
    path = root / 'state.json'
    state = json.loads(path.read_text(encoding='utf-8'))
    if Path(state['game']).resolve() != game:
        raise ValueError('Backup belongs to a different game directory')
    changes = state['changes']
    for change in changes:
        target = inside(game, change['relative'])
        current = sha(target) if target.is_file() else None
        if current not in {change['sha256'], change['before_sha256']}:
            raise ValueError('Refusing to overwrite later changes: ' + change['relative'])
        if change['before_sha256'] is not None:
            backup = inside(root / 'backup', change['relative'])
            if not backup.is_file() or sha(backup) != change['before_sha256']:
                raise ValueError('Backup integrity mismatch: ' + change['relative'])
    for change in reversed(changes):
        target = inside(game, change['relative'])
        current = sha(target) if target.is_file() else None
        if current == change['before_sha256']:
            continue
        if change['before_sha256'] is None:
            target.unlink()
        else:
            backup = inside(root / 'backup', change['relative'])
            shutil.copy2(backup, target)
            if sha(target) != change['before_sha256']:
                raise ValueError('Restore integrity mismatch: ' + change['relative'])
    # Never recursively delete: remove only verified package backup files.
    for change in changes:
        if change['before_sha256'] is not None:
            inside(root / 'backup', change['relative']).unlink()
    path.unlink()
    for directory in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if not any(root.iterdir()):
        root.rmdir()
    print('RESTORED: state before this test package (which may include the earlier preview/image patch).')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'install', 'restore'])
    parser.add_argument('--game', type=Path, default=DEFAULT_GAME)
    args = parser.parse_args()
    game = args.game.resolve()
    if args.action == 'restore':
        restore(game)
    else:
        manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
        if args.action == 'check':
            preflight(game, manifest)
            print(f'CHECK PASS: {len(manifest["files"])} payload files; no game files changed.')
        else:
            install(game, manifest)


if __name__ == '__main__':
    main()
