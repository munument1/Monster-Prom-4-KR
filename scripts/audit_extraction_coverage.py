"""Independently audit Monster Con's text extraction *scope*, read-only.

Unlike audit_translation.py, this enumerates the game's English TextAssets and
derives display columns without calling extract_assets.ordinary_display_field.
The audit never writes to the game, its translation inputs, or release files.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import UnityPy

ROOT = Path(__file__).resolve().parents[1]
GAME_BUNDLES = Path(
    r"C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con"
    r"\MonsterCon_Data\StreamingAssets\aa\StandaloneWindows"
)
SOURCE = ROOT / "work/source"
META_FIELD = re.compile(
    r'^\s*"([A-Za-z0-9_]+)"\s*:\s*"((?:\\.|[^"\\])*)"', re.M
)
DIRECTIVES_WITH_DISPLAY_COL_3 = (">choice\t", ">action\t", ">comic_answer\t")
# Inspected in CoreParser.LoadChallenges: header field 1 is Challenge.name,
# body text (field 0 after Trim('\t')) is Challenge.lines. The unused 5th
# header category (e.g. ANIMAL) is not displayed by that parser.
TEXT_BUNDLE_NONLOCALIZABLE = {"conditions_secret_endings", "comic_panels_cutscenes"}


def display_field(name: str, line: str) -> int | None:
    """Independent source schema census; do not reuse the extraction helper."""
    fields = line.split("\t")
    if name == "english_prologue_likes" and line.startswith(">>>\t"):
        return 2 if len(fields) > 2 and fields[2].strip() else None
    if name == "english_prologue_conpopquiz":
        if line.startswith(">question\t"):
            return 1 if len(fields) > 1 and fields[1].strip() else None
        if line.startswith(">image\t"):
            return 2 if len(fields) > 2 and fields[2].strip() else None
    if line.startswith("\t") or line.startswith(DIRECTIVES_WITH_DISPLAY_COL_3):
        return 3 if len(fields) > 3 and fields[3].strip() else None
    return None


def expected_fields(name: str, source: str) -> list[tuple]:
    if name == "english_metatexts":
        return [(name, key) for key, _ in META_FIELD.findall(source)]
    return [
        (name, n, field)
        for n, line in enumerate(source.splitlines())
        if (field := display_field(name, line)) is not None
    ]


def collect_bundle_textassets(bundle_dir: Path) -> tuple[dict, dict]:
    """Scan *all* bundles, including the sprite-heavy bundles."""
    found: dict[str, tuple[str, str]] = {}
    inventory: dict[str, list[str]] = {}
    for bundle in sorted(bundle_dir.glob("*.bundle")):
        names = []
        for obj in UnityPy.load(str(bundle)).objects:
            if obj.type.name != "TextAsset":
                continue
            asset = obj.read()
            name = asset.m_Name
            if name in found:
                raise ValueError(f"Duplicate TextAsset {name}: {bundle.name}")
            data = asset.m_Script
            if isinstance(data, bytes):
                data = data.decode("utf-8-sig")
            if not isinstance(data, str):
                raise TypeError(f"Unexpected TextAsset data: {name}")
            found[name] = (bundle.name, data.replace("\r\n", "\n"))
            names.append(name)
        if names:
            inventory[bundle.name] = sorted(names)
    return found, inventory


def collect_registered_textfiles(bundle_dir: Path) -> tuple[set[str], set[str]]:
    """Get localized vs structural files from the game's TextFileProfile objects."""
    profiles = bundle_dir / "profilestextfiles_assets_all.bundle"
    if not profiles.is_file():
        raise FileNotFoundError(profiles)
    localized, structural = set(), set()
    for obj in UnityPy.load(str(profiles)).objects:
        if obj.type.name != "MonoBehaviour":
            continue
        data = obj.read_typetree()
        name = data["fileName"]
        target = localized if data["isLocalizedFile"] else structural
        target.add("english_" + name if data["isLocalizedFile"] else name)
    return localized, structural


def audit(bundle_dir: Path = GAME_BUNDLES) -> dict:
    errors = []
    assets, inventory = collect_bundle_textassets(bundle_dir)
    registered_localized, registered_structural = collect_registered_textfiles(bundle_dir)
    manifest = json.loads((ROOT / "work/source_manifest.json").read_text("utf-8"))
    catalog = [
        json.loads(row)
        for row in (ROOT / "work/catalog.jsonl").read_text("utf-8").splitlines()
    ]
    english_names = {name for name in assets if name.startswith("english_")}
    manifest_names = set(manifest)
    if english_names != registered_localized | {"english_metatexts"}:
        errors.append({
            "reason": "TextFileProfile localized assets differ from extraction scope",
            "missing": sorted(registered_localized - english_names),
            "extra": sorted(english_names - registered_localized - {"english_metatexts"}),
        })
    if registered_structural != TEXT_BUNDLE_NONLOCALIZABLE:
        errors.append({
            "reason": "Unlocalized TextFileProfile set changed",
            "registered": sorted(registered_structural),
            "expected": sorted(TEXT_BUNDLE_NONLOCALIZABLE),
        })
    if english_names != manifest_names:
        errors.append({
            "reason": "English asset inventory differs from source manifest",
            "missing": sorted(english_names - manifest_names),
            "stale": sorted(manifest_names - english_names),
        })

    texts_names = {
        name for name, (bundle, _) in assets.items()
        if bundle == "texts_assets_all.bundle"
    }
    unknown_texts = texts_names - english_names - TEXT_BUNDLE_NONLOCALIZABLE
    if unknown_texts:
        errors.append({"reason": "Unclassified TextAsset in texts bundle",
                       "assets": sorted(unknown_texts)})

    expected, actual = set(), set()
    counts = Counter()
    for name in sorted(english_names & manifest_names):
        bundle, raw = assets[name]
        if bundle != "texts_assets_all.bundle":
            errors.append({"reason": "English text moved to another bundle",
                           "asset": name, "bundle": bundle})
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        saved = SOURCE / (name + ".txt")
        if sha != manifest[name]["sha256"] or not saved.is_file() or saved.read_text("utf-8") != raw:
            errors.append({"reason": "Source or manifest differs from game",
                           "asset": name})
        fields = expected_fields(name, raw)
        if len(fields) != len(set(fields)):
            errors.append({"reason": "Duplicate source field", "asset": name})
        expected.update(fields)
        counts[name] = len(fields)
        if name == "english_metatexts":
            # Detect keys that the anchored match may have skipped.
            for n, line in enumerate(raw.splitlines()):
                if line.strip().startswith('"') and ":" in line and not META_FIELD.match(line):
                    errors.append({"reason": "Unparsed metatext key", "line": n + 1})

    for row in catalog:
        name = row["asset"]
        if row["kind"] == "metatext":
            key = (name, row["id"])
            if name in assets:
                actual_value = dict(META_FIELD.findall(assets[name][1])).get(row["id"])
                if actual_value != row["english"]:
                    errors.append({"reason": "Metatext source changed", "key": key})
        else:
            key = (name, row["line"], row.get("field_index", 3))
            if name in assets:
                raw_lines = assets[name][1].splitlines()
                if not 0 <= row["line"] < len(raw_lines):
                    errors.append({"reason": "Catalog line outside source", "key": key})
                else:
                    fields = raw_lines[row["line"]].split("\t")
                    field = row.get("field_index", 3)
                    if field >= len(fields) or fields[field] != row["english"]:
                        errors.append({"reason": "Catalog display field changed", "key": key})
        if key in actual:
            errors.append({"reason": "Duplicate catalog field", "key": key})
        actual.add(key)

    if expected != actual:
        errors.append({
            "reason": "Independent display-field coverage mismatch",
            "unextracted": sorted(expected - actual),
            "extra": sorted(actual - expected),
        })
    return {
        "status": "pass" if not errors else "fail",
        "scope": "TextAssets across all StandaloneWindows bundles and parser-backed "
                 "event/metatext display fields. Does not certify artwork text, "
                 "runtime-generated strings or every possible screen.",
        "bundles_scanned": len(list(bundle_dir.glob("*.bundle"))),
        "textassets_found": len(assets),
        "bundles_with_textassets": inventory,
        "english_assets": sorted(english_names),
        "localized_registered_textfiles": sorted(registered_localized),
        "nonlocalized_registered_textfiles": sorted(registered_structural),
        "structural_nonenglish_text_assets": sorted(texts_names - english_names),
        "catalog_fields": len(catalog),
        "independently_expected_fields": len(expected),
        "by_asset": dict(sorted(counts.items())),
        "errors": errors,
        "game_launched": False,
        "game_modified": False,
    }


if __name__ == "__main__":
    report = audit()
    out = ROOT / "docs/EXTRACTION_COVERAGE_AUDIT.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{report['status'].upper()}: bundles={report['bundles_scanned']} "
          f"TextAssets={report['textassets_found']} English={len(report['english_assets'])} "
          f"source_fields={report['independently_expected_fields']} "
          f"catalog={report['catalog_fields']} errors={len(report['errors'])}")
    for error in report["errors"][:8]:
        print(error)
    if report["errors"]:
        raise SystemExit(1)
