"""Check narrator voice separately from quoted NPC speech and ordinary nouns."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUOTED = re.compile(r'"[^"\n]*"|“[^”]*”|「[^」]*」|『[^』]*』|\x27[^\x27\n]*\x27')
ENDING = re.compile(r'[가-힣]+(?:요|죠|니다|십시오|시다|습니까|입니까)(?=$|[^가-힣])')
# These words end in the same syllables without being polite sentence endings.
LEXICAL = {'필요', '아니요', '요요', '주요', '중요', '고요', '담요', '뿌요뿌요', '죠죠', '아니다', '돌아다니다'}


def inspect_tone(catalog, documents):
    indexes = {name: {row['line']: row['ko'] for row in doc.get('entries', [])} for name, doc in documents.items()}
    errors, voices, quoted_polite = [], Counter(), []
    for c in catalog:
        voice = c.get('speaker', '')
        if not voice.startswith('narrator'):
            continue
        voices[voice] += 1
        text = indexes[c['asset']][c['line']]
        outside = QUOTED.sub(' ', text)
        outside = re.sub(r'\[[^]]*\]|%[^%]*%', ' ', outside)
        matches = [word for word in ENDING.findall(outside) if word not in LEXICAL]
        addresses = re.findall('여러분|당신', outside)
        ident = f"{c['asset']}:{c['line']}"
        if matches or addresses:
            errors.append({'id': ident, 'error': 'narrator polite ending or formal player address remains', 'matches': matches + addresses})
        if any(word not in LEXICAL for quoted in QUOTED.findall(text) for word in ENDING.findall(quoted)):
            quoted_polite.append(ident)
    return {'status': 'pass' if not errors else 'fail', 'scope': 'All catalog speakers beginning with narrator; polite-ending/formal-address scan outside paired quotes. Targeted manual review; not a proof of every stylistic nuance.',
            'narrator_fields_scanned': sum(voices.values()), 'voices': dict(voices), 'errors': errors,
            'quoted_speech_with_polite_forms_preserved': quoted_polite}


def main():
    catalog = [json.loads(line) for line in (ROOT / 'work/catalog.jsonl').read_text(encoding='utf-8').splitlines()]
    documents = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'translations').glob('english_*.json')}
    report = inspect_tone(catalog, documents)
    report['changed_fields'] = json.loads((ROOT / 'docs/NARRATOR_TONE_CHANGES.json').read_text(encoding='utf-8'))['changed_fields']
    (ROOT / 'docs/NARRATOR_TONE_QA.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{report['status'].upper()} narrator_fields={report['narrator_fields_scanned']} corrected={report['changed_fields']} errors={len(report['errors'])}")
    if report['errors']:
        print(report['errors'])
        raise SystemExit(1)


if __name__ == '__main__':
    main()
