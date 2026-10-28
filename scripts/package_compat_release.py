"""Rebuild Monster Con Korean release for the pinned Steam build from a validated v0.1.0 ZIP.

Requires only Python stdlib. Generate the staged six replacement assets first:
python scripts/manage_image_patch.py build --game <game-directory>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v0.2.0"
BUILD_ID = 26248979
SOURCE_SHA256 = "a26949670b2806ed3a8b061d7a8e95dc4cde715140537dccd12e20a7860b0916"
ASSEMBLY_SHA256 = "66af90b44ca5d8f88ee69d1b4f1d49310476200f4682a6c27e55c615d57d20eb"
GAME_ASSEMBLY = "MonsterCon_Data/Managed/Assembly-CSharp.dll"
DEFAULT_STAGE = ROOT / "build/image_patch"
README = ROOT / "docs/RELEASE_v0.2.0.md"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        name != ""
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and ":" not in name
        and not any(part.lower() in {"userdata", "work", "backups"} for part in path.parts)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--base-zip", type=Path, required=True, help="Official v0.1.0 release ZIP")
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build/releases")
    args = parser.parse_args()
    if sha(args.base_zip.read_bytes()) != SOURCE_SHA256:
        raise ValueError("Original release ZIP hash mismatch")
    if sha((args.game / GAME_ASSEMBLY).read_bytes()) != ASSEMBLY_SHA256:
        raise ValueError("Target game Assembly-CSharp.dll differs from tested build")
    stage_manifest = json.loads((args.stage / "manifest.json").read_text(encoding="utf-8"))
    if len(stage_manifest["files"]) != 6 or stage_manifest["unique_textures"] != 49:
        raise ValueError("Expected exactly six rebuilt Unity assets and 49 Korean textures")
    replacements: dict[str, bytes] = {}
    for row in stage_manifest["files"]:
        name = "MonsterCon_Data/" + row["file"].replace("\\", "/")
        if not valid_path(name):
            raise ValueError("Invalid staged file name: " + name)
        if sha((args.game / name).read_bytes()) != row["before_sha256"]:
            raise ValueError("Source asset hash does not match staged build: " + name)
        data = (args.stage / row["file"]).read_bytes()
        if sha(data) != row["after_sha256"]:
            raise ValueError("Rebuilt asset hash mismatch: " + name)
        replacements[name] = data

    with zipfile.ZipFile(args.base_zip) as original:
        names = original.namelist()
        if len(names) != 56 or len(names) != len(set(names)):
            raise ValueError("Original release entries changed")
        if not set(replacements).issubset(names):
            raise ValueError("One of six replacement assets is missing in original")
        for name in names:
            if not valid_path(name):
                raise ValueError("Unsafe original archive entry: " + name)
        manifest = json.loads(original.read("MONSTERCON_KR_MANIFEST.json"))
        if manifest["version"] != "v0.1.0":
            raise ValueError("Not the expected base release")
        for name, expected in manifest["files"].items():
            if sha(original.read(name)) != expected:
                raise ValueError("Original release entry checksum mismatch: " + name)
        files = {
            name: replacements.get(name, original.read(name))
            for name in names
            if name not in {"README-KO.md", "MONSTERCON_KR_MANIFEST.json"}
        }

    files["README-KO.md"] = README.read_bytes()
    manifest["version"] = VERSION
    manifest["source_game_build"] = BUILD_ID
    manifest["rebuilt_unity_assets"] = 6
    manifest["rebuilt_image_textures"] = 49
    manifest["validation"] = (
        "All six image assets regenerated from Steam build 26248979; "
        "49 textures and unrelated-object integrity verified; "
        "patched game clone reached Title and remained running for 152 seconds. "
        "Full gameplay and saves not validated."
    )
    found_assembly = False
    for identity in manifest["game_build_identities"]:
        if identity["relative"].replace("\\", "/") == GAME_ASSEMBLY:
            identity["sha256"] = ASSEMBLY_SHA256
            found_assembly = True
    if not found_assembly:
        raise ValueError("Missing Assembly-CSharp.dll version identity")

    manifest["files"] = {name: sha(data) for name, data in sorted(files.items())}
    files["MONSTERCON_KR_MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    if len(files) != 56:
        raise ValueError("Unexpected release file count")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / ("Monster-Con-KR-" + VERSION + "-Windows-DragDrop.zip")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as check:
        if set(check.namelist()) != set(files):
            raise ValueError("Mismatch in ZIP members")
        for name, data in files.items():
            if sha(check.read(name)) != sha(data):
                raise ValueError("ZIP checksum mismatch: " + name)
    checksum = sha(output.read_bytes())
    sums = args.output_dir / ("SHA256SUMS-" + VERSION + ".txt")
    sums.write_text(checksum + "  " + output.name + "\n", encoding="ascii")
    print("ZIP=" + str(output))
    print("CHECKSUMS=" + str(sums))
    print("PASS files=" + str(len(files)) + " textures=49 sha256=" + checksum)


if __name__ == "__main__":
    main()
