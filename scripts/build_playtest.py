"""Build source-faithful loose event text files from reviewed Korean translations.

Only translated files are output. The game installation is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "work/source"
DEST = ROOT / "build/playtest/game_assets/texts"
# Match actual variable placeholders rather than any text between percent
# signs. Literal percentages adjacent to placeholders (e.g. `100% OBJECTIFY
# %HISHERCAPS%`) otherwise create false `% ... %` tokens and reject valid
# translations. The source catalog's real percent placeholders use this
# identifier alphabet, including apostrophes in tokens such as `%VERB_'S_'VE%`.
TOKEN = re.compile(r"%[A-Za-z0-9_']+%|\[[^\[\]\r\n]+\]|<[^<>\r\n]+>")
NUMBER = re.compile(r"(?<!\d)[+-]?\d+(?:\.\d+)?")

# Source stat effects are executable event syntax, not translatable prose.
# The game finds effect tokens using word boundaries. Korean postpositions
# directly after the ASCII enum name (e.g. +N2 MAGIC을) prevent that parse,
# even though the underlying code bytes are otherwise correct. A U+200B
# boundary is invisible to players and was checked against a live Steam game
# load: 345 event-parser errors dropped to the single legacy wrong-enum row.
STAT_EFFECT = re.compile(r"(?<![A-Za-z])([+-])(N?[0-9]+)\s*(SMARTS|BOLDNESS|CHARM|CREATIVITY|FUN|MONEY)(?![A-Za-z])")
STAT_EFFECT_GLUED_TO_HANGUL = re.compile(r"(?P<code>[+-]N?[0-9]+[ ]*(?:SMARTS|BOLDNESS|CHARM|CREATIVITY|FUN|MONEY))(?P<postposition>[\uac00-\ud7a3])")
GAME_STAT_BOUNDARY = "\u200b"
# Exact reviewed source/translation pairs may omit redundant English pronoun
# and copula macros. Other placeholders still have to match exactly.
GRAMMAR_EXCEPTIONS = json.loads((ROOT / "translations/grammar_exceptions.json").read_text(encoding="utf-8"))



def game_safe_stat_effects(korean: str) -> str:
    """Insert an invisible word boundary AFTER valid stat syntax in game TXT.

    Reviewed JSON remains natural Korean and contains no hidden characters.
    This is idempotent, preserves exactly all stat codes and Hangul text, and
    cannot affect UI strings or non-stat conversation.
    """
    return STAT_EFFECT_GLUED_TO_HANGUL.sub(
        lambda hit: hit.group("code") + GAME_STAT_BOUNDARY + hit.group("postposition"),
        korean,
    )

def verify_line(english: str, korean: str, ident: str) -> None:
    if not korean or any(c in korean for c in "\t\r\n\ufffd"):
        raise ValueError(f"invalid translated field: {ident}")
    punctuation_only = bool(re.fullmatch(r"[.?!…]+", english.strip())) and bool(re.fullmatch(r"[.?!…]+", korean.strip()))
    if not re.search("[가-힣]", korean) and not punctuation_only and (ident, english, korean) != ("RES_NEX", "[0] of [1]", "[0] / [1]"):
        raise ValueError(f"translation missing Hangul: {ident}")
    expected_tokens = Counter(TOKEN.findall(english))
    exception = GRAMMAR_EXCEPTIONS.get(ident)
    if exception:
        if (hashlib.sha256(english.encode("utf-8")).hexdigest() != exception["english_sha256"] or
                hashlib.sha256(korean.encode("utf-8")).hexdigest() != exception["korean_sha256"]):
            raise ValueError(f"grammar exception source/translation changed: {ident}")
        expected_tokens.subtract(exception["omitted_tokens"])
        expected_tokens = +expected_tokens
    if Counter(TOKEN.findall(korean)) != expected_tokens:
        raise ValueError(f"control token mismatch: {ident}")
    if Counter(NUMBER.findall(korean)) != Counter(NUMBER.findall(english)):
        raise ValueError(f"number mismatch: {ident}")
    if Counter(STAT_EFFECT.findall(korean)) != Counter(STAT_EFFECT.findall(english)):
        raise ValueError(f"stat effect mismatch: {ident}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create verified Monster Con event text overrides")
    parser.add_argument(
        "--only",
        metavar="ASSET",
        help="Verify/build only a given english_events_* asset (supports concurrent translation work)",
    )
    args = parser.parse_args()
    files = sorted(f for f in (ROOT / "translations").glob("english_*.json") if f.stem != "english_metatexts_ko")
    if args.only:
        name = args.only.removesuffix(".json")
        files = [f for f in files if f.stem == name]
    if not files:
        raise RuntimeError("No translation files")
    n_total = 0
    outputs: list[tuple[Path, str, int]] = []
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        name = f.stem
        original = (SRC / f"{name}.txt").read_text(encoding="utf-8")
        sha = hashlib.sha256(original.encode("utf-8")).hexdigest()
        if sha != doc["source_sha256"]:
            raise ValueError(f"source asset changed: {name}")
        lines = original.splitlines(keepends=True)
        visited = set()
        previous_num = -1
        safe_delimiters = 0
        for row in doc["entries"]:
            num = row["line"]
            if not isinstance(num, int) or not (0 <= num < len(lines)):
                raise ValueError(f"out of range source row: {name}:{num}")
            if num <= previous_num:
                raise ValueError(f"translated lines are not in source order: {name}:{num}")
            previous_num = num
            if num in visited:
                raise ValueError(f"duplicate line: {name}:{num}")
            visited.add(num)
            line = lines[num]
            eol = "\n" if line.endswith("\n") else ""
            fields = (line[:-1] if eol else line).split("\t")
            field = row.get("field_index", 3)
            if len(fields) <= field:
                raise ValueError(f"bad source row: {name}:{num}")
            source = fields[field]
            source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
            if source_hash != row["english_sha256"]:
                raise ValueError(f"source sentence changed: {name}:{num}")
            event = next((x.split("\t")[1].rstrip("\r\n") for x in reversed(lines[:num + 1]) if x.startswith(">>>\t")), None)
            if event != row["event"]:
                raise ValueError(f"event changed: {name}:{num}")
            verify_line(source, row["ko"], f"{name}:{num}")
            game_text = game_safe_stat_effects(row["ko"])
            safe_delimiters += game_text.count(GAME_STAT_BOUNDARY)
            fields[field] = game_text
            lines[num] = "\t".join(fields) + eol
        content = "".join(lines)
        assert len(content.splitlines()) == len(original.splitlines())
        outputs.append((DEST / (name + ".txt"), content, len(visited), safe_delimiters))
        n_total += len(visited)
    # Validate the entire requested selection before writing any output.
    DEST.mkdir(parents=True, exist_ok=True)
    for out, content, count, delimiters in outputs:
        out.write_text(content, encoding="utf-8", newline="\n")
        print(f"BUILT {out.name} translated={count} original_lines={len(content.splitlines())} parser_safe_stat_boundaries={delimiters}")
    print(f"PASS translated_lines={n_total} output={DEST}")


if __name__ == "__main__":
    main()
