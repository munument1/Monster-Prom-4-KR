"""Stage local loader and OFL font inputs from the existing Roadtrip project."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roadtrip', type=Path, default=ROOT.parent / 'Monster-Prom-3-KR')
    args = parser.parse_args()
    old = args.roadtrip.resolve()
    source = old / 'work/tools/BepInEx_win_x86_5.4.23.2'
    if not (source / 'BepInEx/core/BepInEx.dll').is_file():
        raise FileNotFoundError(source)
    shutil.copytree(source, ROOT / 'work/tools/BepInEx_win_x86_5.4.23.2', dirs_exist_ok=True)
    out = ROOT / 'build/fonts'
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old / 'build/public_fonts/roadtrip_korean_fonts.bundle', out / 'monstercon_korean_fonts.bundle')
    for name in ['Jua-OFL.txt', 'GamjaFlower-OFL.txt', 'PROVENANCE.json']:
        shutil.copy2(old / 'work/public_fonts' / name, out / name)
    records = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (ROOT / 'work/dependency_hashes.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('Prepared local loader and licensed Jua/GamjaFlower bundle. Game files were not modified.')


if __name__ == '__main__':
    main()
