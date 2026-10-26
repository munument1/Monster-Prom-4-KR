"""Read-only extraction of Monster Con English TextAssets to ignored work/.

Requires UnityPy. Does not modify, launch, or inject into the installed game.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import UnityPy

GAME = Path(r"C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con")
BUNDLE = GAME / "MonsterCon_Data/StreamingAssets/aa/StandaloneWindows/texts_assets_all.bundle"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/source"
CATALOG = ROOT / "work/catalog.jsonl"
INDEX = ROOT / "work/source_manifest.json"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    manifest = {}
    rows = 0
    events = 0
    if not BUNDLE.is_file():
        raise FileNotFoundError(BUNDLE)
    env = UnityPy.load(str(BUNDLE))
    for asset in env.objects:
        if asset.type.name != "TextAsset":
            continue
        obj = asset.read()
        name = obj.m_Name
        if not name.startswith("english_"):
            continue
        data = obj.m_Script
        if isinstance(data, bytes):
            data = data.decode("utf-8-sig")
        assert isinstance(data, str)
        data = data.replace("\r\n", "\n")
        assert "\r" not in data, f"unexpected CR in {name}"
        raw = data.encode("utf-8")
        (OUT / f"{name}.txt").write_bytes(raw)
        manifest[name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "length": len(raw),
            "game_asset": name,
        }
        if name == "english_metatexts":
            # Meta-texts are an array of JSON-style objects with comments.
            for key, source in re.findall(r'^\s*"([A-Za-z0-9_]+)"\s*:\s*"((?:\\.|[^"\\])*)"', data, flags=re.M):
                records.append({"asset": name, "id": key, "english": source, "kind": "metatext"})
            continue

        event = None
        for n, line in enumerate(data.splitlines()):
            if line.startswith(">>>\t"):
                event = line.split("\t", 2)[1]
                events += 1
                if name == "english_prologue_likes":
                    fields = line.split("\t")
                    if len(fields) > 2 and fields[2].strip():
                        original = fields[2]
                        records.append({"asset": name, "event": event, "line": n, "field_index": 2,
                            "english": original, "english_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                            "kind": "event", "row_type": "like"})
                        rows += 1
                continue
            if name == "english_prologue_conpopquiz" and (line.startswith(">question\t") or line.startswith(">image\t")):
                fields = line.split("\t")
                field = 1 if fields[0] == ">question" else 2
                original = fields[field]
                records.append({"asset": name, "event": event, "line": n, "field_index": field,
                    "english": original, "english_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                    "kind": "event", "row_type": "quiz"})
                rows += 1
                continue
            # The game's event parser also displays the *fourth* field of
            # >choice and >action directives as player-facing choice/action
            # text. The preceding three columns remain structural metadata.
            # Skipping these lines silently leaves whole dialogue branches in
            # English, so include all three human-facing row categories.
            if not (line.startswith("\t") or line.startswith(">choice\t") or line.startswith(">action\t")):
                continue
            fields = line.split("\t")
            if len(fields) < 4 or not fields[3].strip():
                continue
            original = fields[3]
            records.append({
                "asset": name,
                "event": event,
                "line": n,
                "speaker": fields[1],
                "expression": fields[2],
                "english": original,
                "english_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                "kind": "event",
                "row_type": "choice" if line.startswith(">choice\t") else ("action" if line.startswith(">action\t") else "dialogue"),
            })
            rows += 1
    assert manifest and "english_metatexts" in manifest, manifest
    CATALOG.parent.mkdir(exist_ok=True)
    with CATALOG.open("w", encoding="utf-8", newline="\n") as out:
        for rec in records:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    INDEX.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EXTRACTED assets={len(manifest)} events={events} event_rows={rows} total_catalog={len(records)}")
    print(f"META_KEYS={sum(r['kind']=='metatext' for r in records)}")
    print(f"SOURCE={OUT}")
    print(f"CATALOG={CATALOG}")


if __name__ == "__main__":
    main()
