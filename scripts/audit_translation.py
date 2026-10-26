"""Audit translated fields and built output without running or changing the game."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont
from build_playtest import ROOT, verify_line, game_safe_stat_effects
from audit_narrator_tone import inspect_tone


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def main():
    catalog = [json.loads(line) for line in (ROOT / 'work/catalog.jsonl').read_text(encoding='utf-8').splitlines()]
    documents = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'translations').glob('english_*.json')}
    sources = {p.stem: p.read_text(encoding='utf-8') for p in (ROOT / 'work/source').glob('english_*.txt')}
    indexes = {name: {row['line']: row for row in doc.get('entries', [])} for name, doc in documents.items()}
    errors, unchanged, long_rows, texts = [], [], [], []
    expected, actual = set(), set()
    import UnityPy
    game_bundle = Path(r'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con\MonsterCon_Data\StreamingAssets\aa\StandaloneWindows\texts_assets_all.bundle')
    installed_sources = {}
    for obj in UnityPy.load(str(game_bundle)).objects:
        if obj.type.name != 'TextAsset':
            continue
        asset = obj.read()
        if asset.m_Name in sources:
            script = asset.m_Script
            if isinstance(script, bytes):
                script = script.decode('utf-8-sig')
            installed_sources[asset.m_Name] = script.replace('\r\n', '\n')
    if installed_sources != sources:
        errors.append({'error': 'installed English assets differ from extracted source'})
    for name, doc in documents.items():
        source_name = name.removesuffix('_ko')
        if digest(sources[source_name]) != doc['source_sha256']:
            errors.append({'id': name, 'error': 'asset source hash changed'})
        if 'entries' in doc:
            lines = [row['line'] for row in doc['entries']]
            if lines != sorted(set(lines)):
                errors.append({'id': name, 'error': 'duplicate or unsorted source lines'})
            actual.update(f'{name}:{line}' for line in lines)
        else:
            actual.update(doc['translations'])
    for c in catalog:
        name = c['asset']
        if name == 'english_metatexts':
            ident = c['id']
            english = json.loads('"' + c['english'] + '"')
            ko = documents[name + '_ko']['translations'].get(ident)
        else:
            ident = f"{name}:{c['line']}"
            english = c['english']
            row = indexes[name].get(c['line'])
            ko = row['ko'] if row else None
            if row and (row['english_sha256'] != digest(english) or row['event'] != c['event'] or row.get('field_index', 3) != c.get('field_index', 3)):
                errors.append({'id': ident, 'error': 'source metadata/hash mismatch'})
        expected.add(ident)
        if ko is None:
            errors.append({'id': ident, 'error': 'missing translation'})
            continue
        try:
            verify_line(english, ko, ident)
        except ValueError as error:
            errors.append({'id': ident, 'error': str(error)})
        # Preserve formatting order as well as counts. Source has a handful of
        # legacy unclosed superscripts, so compare the actual tag sequence.
        tags = r'\[/?(?:b|i|sub|sup|sha|sin|ras|rai|sta)\]'
        if re.findall(tags, english) != re.findall(tags, ko):
            errors.append({'id': ident, 'error': 'formatting tag order changed'})
        texts.append(ko)
        if english == ko:
            unchanged.append(ident)
        if len(ko) > 230:
            long_rows.append({'id': ident, 'characters': len(ko)})
        if re.search(r'%(?:VERB_[A-Z_\']+|HESHE|HIMHER|HISHER|GUYGIRL|MANWOMAN|SIRMAAM|MRMRS|BOYGIRL|FATHERMOTHER)%', ko):
            errors.append({'id': ident, 'error': 'English grammar/gender expansion remains'})
        if '몬스터 컨' in ko or '몬스터컨' in ko:
            errors.append({'id': ident, 'error': 'incorrect Monster Con Korean title'})
    if expected != actual:
        errors.append({'error': 'catalog coverage mismatch', 'missing': sorted(expected - actual), 'extra': sorted(actual - expected)})
    narrator_tone = inspect_tone(catalog, documents)
    errors.extend(narrator_tone['errors'])
    # Reconstruct every event output and compare all bytes, including commands,
    # branches, speakers and all fields outside the chosen display field.
    output_rows = 0
    for name, doc in documents.items():
        if 'entries' not in doc:
            continue
        lines = sources[name].splitlines(keepends=True)
        for row in doc['entries']:
            n = row['line']; eol = '\n' if lines[n].endswith('\n') else ''
            fields = lines[n].removesuffix('\n').split('\t')
            fields[row.get('field_index', 3)] = game_safe_stat_effects(row['ko'])
            lines[n] = '\t'.join(fields) + eol
            output_rows += 1
        out = ROOT / 'build/playtest/game_assets/texts' / (name + '.txt')
        if not out.exists() or out.read_bytes() != ''.join(lines).encode('utf-8'):
            errors.append({'id': name, 'error': 'built event output differs from allowed display-field substitutions'})
    chars = set(''.join(texts))
    hangul = {c for c in chars if '\uac00' <= c <= '\ud7a3'}
    fonts = []
    for filename in ['Jua.ttf', 'GamjaFlower.ttf']:
        path = ROOT / 'work/ui_images/fonts' / filename
        if not path.exists():
            path = ROOT.parent / 'Monster-Prom-3-KR/work/public_fonts' / filename
        font = TTFont(path)
        cmap = set(map(chr, font.getBestCmap()))
        fonts.append({'font': filename, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'missing_hangul': ''.join(sorted(hangul - cmap)),
                      'missing_non_ascii': ''.join(sorted(c for c in chars - cmap if ord(c) > 127))})
        font.close()
    report = {'status': 'pass' if not errors else 'fail', 'scope': 'All extracted fields: source identity, coverage, contract and built event structure. Targeted language fixes; full literary proofreading and in-game layout/branch QA remain pending.',
              'translation_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / 'translations').glob('*.json'))},
              'assets': len(sources), 'fields': len(catalog), 'built_event_fields': output_rows,
              'counts_by_asset': dict(Counter(c['asset'] for c in catalog)), 'errors': errors,
              'narrator_tone_fields_scanned': narrator_tone['narrator_fields_scanned'],
              'unchanged_literal_or_control_fields': unchanged, 'hangul_characters': len(hangul), 'fonts': fonts,
              'long_strings_for_user_screen_test': sorted(long_rows, key=lambda x: -x['characters']),
              'installed_source_assets_compared': len(installed_sources),
              'game_launched': False, 'game_installed_or_modified': False}
    destination = ROOT / 'docs/TEXT_QA_REPORT.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{report['status'].upper()} fields={len(catalog)} assets={len(sources)} errors={len(errors)} Hangul={len(hangul)} long_strings={len(long_rows)}")
    for error in errors[:20]:
        print(error)
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
