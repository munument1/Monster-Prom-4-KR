# 몬스터콘 이미지 UI 한국어 패치

PC판의 이미지에 들어 있던 UI 글자를 번역한 로컬 패치입니다. 최종 이미지 목록은 `artwork/ui/texture_patch.json`에 있습니다.

- 장르 카드, 난이도, 음악 테이프 라벨
- 친구 호출기, 신규 표시, 갤러리의 돈 부족 안내
- DLC 및 시리즈 안내 이미지
- 게임 설명서 31쪽과 표지

총 49개 텍스처 이름을 대상으로 하며, 같은 텍스처가 여러 에셋 파일에 들어 있으면 함께 교체합니다. PC에서 사용하지 않는 Switch 전용 설명서와 글자가 없는 마지막 그림은 교체하지 않습니다.

## 이미지와 번역문

최종 적용본: `artwork/ui/final/`

이미지 생성본: 로컬 `artwork/ui/generated/`. 기존 생성본을 삭제하지 않았습니다. 매뉴얼은 생성본의 디자인을 사용하며, 발견한 오역과 게임명 표기는 실제 한글 폰트로 교정했습니다. 별도 전체 조판 비교 시안은 로컬 `artwork/ui/manual_ko/`에 보존했습니다. 생성본과 비교 시안은 Git에서 제외하며, 저장소에는 최종 적용본을 보관합니다.

번역문: `artwork/ui/manual_ko.json`. 게임명 한국어 표기는 **몬스터콘**입니다.

생성 기록: `artwork/ui/generation_prompts.json`, `artwork/ui/manual_remaining_prompts.json`. 내장 이미지 생성 도구를 사용했습니다. 원본 생성 결과는 사용자 `.codex/generated_images`에도 남아 있습니다.

## 파일 검증과 복구

의존성 설치: `python -m pip install -r requirements-ui-images.txt`

빌드 명령: `python scripts/manage_image_patch.py build --game "게임 설치 경로"`

적용 명령: `python scripts/manage_image_patch.py install --game "게임 설치 경로"`

복구 명령: `python scripts/manage_image_patch.py restore --game "게임 설치 경로"`

게임 설치 경로의 기본값은 `C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con`입니다. 빌드는 설치된 게임의 텍스처를 직접 찾아 작업하므로 추출 작업 폴더 없이 실행할 수 있습니다. 최종 PNG를 이용한 빌드에는 생성 시안이나 글꼴 파일이 필요하지 않습니다. 그림을 다시 조판하는 `build_manual_images.py`와 `assemble_ui_images.py`는 원본 추출물·시안·글꼴이 필요한 로컬 저작 도구입니다.

## 향후 한패에 포함하기

로컬 통합 테스트 패키지(`package_playtest.py`)에는 텍스트와 함께 포함합니다. [통합 테스트 사용법](PLAYTEST_QA.md)을 참고하세요. 기존 텍스트 전용 설치 스크립트에는 자동 연결하지 않았습니다. 배포 시 위 이미지 빌드를 별도로 실행한 뒤 `build/image_patch/manifest.json`의 파일 목록에 따라 `MonsterCon_Data` 아래에 적용해야 합니다. 게임 원본을 바꾸므로 배포 설치기에도 원본 백업·버전 확인·복구 처리를 포함해야 합니다. 기존 텍스트 전용 설치/제거 스크립트는 이 이미지 패치를 제거하지 않습니다.

게임 업데이트 후에는 새 원본에서 다시 빌드하고 화면을 확인해야 합니다. 저장소에는 완성된 게임 에셋 파일이나 로컬 백업을 올리지 않습니다.

게임을 종료한 상태에서 실행합니다. 적용 전에 원래 파일을 `work/backups/ui_images_날짜_시간/`에 복사합니다. 실제 백업 경로와 설치 파일 해시는 `work/install/ui_images.json`에 기록합니다. 복구 명령은 이후 변경된 파일을 덮어쓰지 않도록 해시를 검사합니다.

빌드 검증은 모든 오브젝트 ID의 보존, 대상 외 오브젝트의 바이트 일치, 교체한 텍스처를 다시 읽었을 때 최종 PNG와의 RGBA 픽셀 일치를 확인합니다. 설치 후 파일 해시를 확인합니다. 기존 번역 플러그인과 대사 번역은 이 이미지 패치에서 수정하지 않습니다.

게임 실행 및 화면 검증은 사용자가 진행합니다. 확인할 곳은 새 게임의 장르·난이도·음악 선택, 친구 호출기, 갤러리, 설정에서 여는 게임 설명서입니다. 설명서에 들어 있는 작은 예시 화면도 포함되므로, 표시가 어색한 곳이 있으면 해당 페이지 번호를 기준으로 수정할 수 있습니다.
