"""Build the UI text file loaded by MonsterConKoreanBridge."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from build_playtest import verify_line

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/source/english_metatexts.txt"
INPUT = ROOT / "translations/english_metatexts_ko.json"
OUTPUT = ROOT / "build/preview/english_metatexts.txt"
PATTERN = re.compile(r'(?m)^(\s*"([A-Za-z0-9_]+)"\s*:\s*)"((?:\\.|[^"\\])*)"')


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    doc = json.loads(INPUT.read_text(encoding="utf-8"))
    assert doc["source_sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()
    seen = set()

    def substitute(match: re.Match[str]) -> str:
        prefix, key, raw_value = match.groups()
        if key not in doc["translations"]:
            return match.group(0)
        if key in seen:
            raise ValueError(f"duplicate metatext id: {key}")
        seen.add(key)
        english = json.loads('"' + raw_value + '"')
        ko = doc["translations"][key]
        verify_line(english, ko, key)
        return prefix + json.dumps(ko, ensure_ascii=False)

    patched = PATTERN.sub(substitute, source)
    missing = set(doc["translations"]) - seen
    if missing:
        raise ValueError(f"unknown metatexts: {sorted(missing)}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(patched, encoding="utf-8", newline="\n")
    assert patched.count("\n") == source.count("\n")
    print(f"BUILT metatexts translated={len(seen)} output={OUTPUT}")
    print("Install beside MonsterConKoreanBridge.dll; engine-only loose overrides do not cover UI.")


if __name__ == "__main__":
    main()
