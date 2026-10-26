"""Assemble verified text, runtime, fonts and UI/manual into a local test package."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(r'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    out = args.output or ROOT / 'build/releases' / ('MonsterCon-KR-test-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for filename in ['TEXT_QA_REPORT.json', 'IMAGE_QA_REPORT.json']:
        assert json.loads((ROOT / 'docs' / filename).read_text(encoding='utf-8'))['status'] == 'pass'
    text_qa = json.loads((ROOT / 'docs/TEXT_QA_REPORT.json').read_text(encoding='utf-8'))
    for filename, expected in text_qa['translation_sha256'].items():
        assert sha(ROOT / 'translations' / filename) == expected, ('Translation changed since QA', filename)
    image_qa = json.loads((ROOT / 'docs/IMAGE_QA_REPORT.json').read_text(encoding='utf-8'))
    assert sha(ROOT / 'build/image_patch/manifest.json') == image_qa['manifest_sha256']
    for filename, expected in image_qa['final_png_sha256'].items():
        assert sha(ROOT / filename) == expected, ('Image changed since QA', filename)
    # Package only known previous-preview hashes; an arbitrary installed file
    # is never blessed merely because it happens to exist on this computer.
    prior_path = ROOT / 'work/install/installed_files.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8-sig')) if prior_path.exists() else {'files': []}
    previous = {r['relative'].replace('\\', '/'): r['sha256'].lower() for r in prior['files']}
    records = []

    def add(source, relative, allowed=(), required=False):
        relative = relative.replace('\\', '/')
        target = out / 'payload' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        old = set(allowed)
        if relative in previous:
            old.add(previous[relative])
        records.append({'relative': relative, 'sha256': sha(target), 'allowed_before_sha256': sorted(old), 'required_existing': required})

    loader = ROOT / 'work/tools/BepInEx_win_x86_5.4.23.2'
    for name in ['winhttp.dll', 'doorstop_config.ini', '.doorstop_version']:
        add(loader / name, name)
    for path in sorted((loader / 'BepInEx').rglob('*')):
        if path.is_file():
            source = ROOT / 'build/runtime_compat/MonoMod.Utils.dll' if path.name == 'MonoMod.Utils.dll' else path
            add(source, path.relative_to(loader).as_posix())
    plugin = 'BepInEx/plugins/MonsterConKoreanBridge/'
    add(ROOT / 'src/MonsterConKoreanBridge/bin/Release/MonsterConKoreanBridge.dll', plugin + 'MonsterConKoreanBridge.dll')
    add(ROOT / 'build/preview/english_metatexts.txt', plugin + 'english_metatexts.txt')
    for name in ['monstercon_korean_fonts.bundle', 'Jua-OFL.txt', 'GamjaFlower-OFL.txt', 'PROVENANCE.json']:
        add(ROOT / 'build/fonts' / name, plugin + name)
    for path in sorted((ROOT / 'build/playtest/game_assets/texts').glob('english_*.txt')):
        add(path, 'MonsterCon_Data/StreamingAssets/game_assets/texts/' + path.name)
    images = json.loads((ROOT / 'build/image_patch/manifest.json').read_text(encoding='utf-8'))
    for row in images['files']:
        add(ROOT / 'build/image_patch' / row['file'], 'MonsterCon_Data/' + row['file'], [row['before_sha256']], required=True)
    identities = []
    for relative in ['MonsterCon_Data/Managed/Assembly-CSharp.dll', 'MonsterCon_Data/StreamingAssets/aa/StandaloneWindows/texts_assets_all.bundle', 'MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll']:
        identities.append({'relative': relative, 'sha256': sha(GAME / relative)})
    manifest = {'schema': 1, 'title': '몬스터 프롬 4: 몬스터 콘', 'stage': 'local user playtest; linguistic/layout/full-branch QA pending',
                'text_fields': text_qa['fields'], 'unique_image_textures': images['unique_textures'], 'identities': identities, 'files': records}
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copy2(ROOT / 'scripts/package_installer.py', out / 'manage_patch.py')
    for action in ['check', 'install', 'restore']:
        (out / (action.capitalize() + '.cmd')).write_text(
            '@echo off\r\npython -X utf8 "%~dp0manage_patch.py" ' + action + ' %*\r\n'
            'set "patch_exit=%errorlevel%"\r\npause\r\nexit /b %patch_exit%\r\n', encoding='ascii', newline='')
    for filename in ['TEXT_QA_REPORT.json', 'IMAGE_QA_REPORT.json']:
        shutil.copy2(ROOT / 'docs' / filename, out / filename)
    (out / '사용법.txt').write_text('몬스터 프롬 4: 몬스터 콘 통합 테스트 패치\n\n'
        f'텍스트 {text_qa["fields"]:,}개 + 이미지 UI/매뉴얼 49종. 게임 실행 검사는 사용자가 진행합니다.\n'
        '게임을 종료하고 이 폴더에서 PowerShell을 연 뒤 실행하세요(Python 3 필요).\n\n'
        '확인만: python -X utf8 manage_patch.py check\n'
        '설치: python -X utf8 manage_patch.py install\n'
        '설치 직전 상태로 복구: python -X utf8 manage_patch.py restore\n\n'
        '기본 설치 경로는 C:\\Games\\Steam\\steamapps\\common\\Monster Prom 4 - Monster Con 입니다.\n'
        '다른 경로는 명령 끝에 --game "설치 경로"를 추가하세요.\n'
        '기존 미리보기는 기록된 해시가 일치할 때만 갱신하며, 이미지가 같으면 다시 쓰지 않습니다.\n'
        '복구는 이 패키지 설치 직전 상태로 돌아갑니다. 이전 미리보기/이미지 한패가 이미 있었다면 그대로 남습니다.\n'
        '백업은 게임 폴더의 .monstercon-kr-test에 보관합니다. 복구 전에는 이 폴더를 지우지 마세요.\n'
        '이 패키지를 복구한 뒤에만 예전 저장소의 제거 도구를 사용하세요.\n'
        '주아 글리프 누락 시 브리지의 기존 맑은 고딕 대체 경로가 사용됩니다. 화면의 글자/기호/잘림은 확인이 필요합니다.\n'
        '한국어 초안 전체의 문장 교열, 화면 배치 및 전체 분기 검증을 마친 정식 배포본은 아닙니다.\n', encoding='utf-8-sig')
    print('PACKAGE=' + str(out))
    print(f'FILES={len(records)} BYTES={sum(p.stat().st_size for p in (out / "payload").rglob("*") if p.is_file())}')


if __name__ == '__main__':
    main()
