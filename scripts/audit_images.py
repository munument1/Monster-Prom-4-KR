"""Verify staged UI/manual assets against the final PNGs without installing."""
import hashlib
import json
from pathlib import Path

import UnityPy
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    specs = {x['texture']: x['image'] for x in json.loads((ROOT / 'artwork/ui/texture_patch.json').read_text(encoding='utf-8'))['textures']}
    manifest = json.loads((ROOT / 'build/image_patch/manifest.json').read_text(encoding='utf-8'))
    seen, count = set(), 0
    for record in manifest['files']:
        path = ROOT / 'build/image_patch' / record['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['after_sha256'], path
        env = UnityPy.load(str(path))
        for obj in env.objects:
            if obj.type.name != 'Texture2D':
                continue
            texture = obj.read()
            if texture.m_Name not in specs:
                continue
            with Image.open(ROOT / specs[texture.m_Name]) as final:
                assert texture.image.convert('RGBA').tobytes() == final.convert('RGBA').tobytes(), texture.m_Name
            seen.add(texture.m_Name)
            count += 1
    assert seen == set(specs), set(specs) - seen
    report = {'status': 'pass', 'unique_textures': len(seen), 'texture_occurrences': count,
              'manifest_sha256': hashlib.sha256((ROOT / 'build/image_patch/manifest.json').read_bytes()).hexdigest(),
              'final_png_sha256': {filename: hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() for filename in sorted(set(specs.values()))},
              'asset_files': len(manifest['files']), 'checks': ['staged asset SHA256', 'decoded RGBA matches each final PNG'],
              'screen_test': 'pending user', 'installed_game_modified': False}
    (ROOT / 'docs/IMAGE_QA_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS unique_textures={len(seen)} occurrences={count} asset_files={len(manifest["files"])}; screen test pending user')


if __name__ == '__main__':
    main()
