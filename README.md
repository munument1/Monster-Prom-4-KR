# Monster Prom 4: Monster Con 한국어 번역

2026-10-26 착수. **전체 번역 완성본이 아닌 초기 개발본**입니다.

- Steam Windows build 26157563, Unity 2022.3.62f1 / Mono x86.
- 초기 추출: 영어 TextAsset 17개, 번역 후보 23,986개.
- UI 520 / 2,502개, 대사·선택지·시작 취향·퀴즈 132 / 21,484개 작성.
- 합계 652개(2.72%). 미번역 부분은 영어로 유지합니다.
- 주아·감자꽃 번들 로딩과 프롤로그·취향·퀴즈 외부 파일 읽기를 실제 로그에서 확인했습니다.
- UI 브리지 0.1.0은 초기 실행에서 UI를 바꾸지 못했습니다. 0.1.1에서
  `CoreTextManager.LoadMetatextsFile(ref string)`에 직접 연결하도록 수정했습니다.
  **수정본의 실행·화면 검증은 사용자가 진행합니다.**
- 0.1.1 사용자 테스트에서 기호만 보이고 한글이 누락됐습니다. 폰트 로딩은 성공했지만
  후속 UI 적용 로그는 없었습니다. 0.1.2는 브리지/폰트 생존 유지, NGUI 비트맵 해제,
  한글 텍스트 대입 시 폰트 재적용, 활성 언어 프로필 폰트 연결, 1초 간격 복구와
  생명주기 진단 로그를 추가한 수정 후보입니다. 실행 검증은 아직 하지 않았습니다.

## 3편에서 가져온 부분

[Monster-Prom-3-KR](https://github.com/munument1/Monster-Prom-3-KR)의 추출·검증·설치 도구와
NGUI/Unity UI 폰트 브리지를 4편에 맞게 이식했습니다. UI 번역 459개는 영문 일치 기준으로
재사용했고, 61개 UI 및 프롤로그·취향·퀴즈 132개는 새로 작성했습니다.

4편은 줄바꿈이 혼재하고, 시작 취향·퀴즈의 번역 필드 위치도 다릅니다.
이를 별도로 추출합니다. 이벤트 명령·인물 ID·분기·능력치 코드는 보존합니다.
초기 카탈로그는 발견한 표시 필드 기준이며, 이후 파서 조사로 대상이 늘어날 수 있습니다.

3편의 도로 이동·세이브·스탯 UI 수정은 이식하지 않았습니다.
4편 Mono의 `mono_domain_assembly_foreach`에서 +0x53 플래그를 독립적으로 확인했고,
정확한 DLL 해시에 한정한 MonoMod 보정을 적용했습니다. 독립 x86 호스트에서
플래그 기록, Harmony 적용, 적용 후 해제의 세 경우 모두 정상 종료했습니다.

## 개발 환경

Python 3, .NET SDK, .NET Framework 4.7.2 참조 어셈블리 및 정품 게임 설치가 필요합니다.
현재 개발 PC에서는 옆의 3편 작업 폴더에서 로컬 의존성을 준비합니다.

```powershell
python -m pip install -r requirements.txt
python -X utf8 scripts/prepare_from_roadtrip.py
python -X utf8 scripts/extract_assets.py
python -X utf8 scripts/build_playtest.py
python -X utf8 scripts/build_ui_preview.py
dotnet build src/MonsterConKoreanBridge/MonsterConKoreanBridge.csproj -c Release
python -X utf8 -m unittest discover -s tests -v
```

원문·작업 카탈로그·게임/로더/폰트 바이너리·로컬 빌드는 `work/`, `build/`에 두고
Git에서 제외합니다. 원문 파일 해시와 개별 필드 해시를 확인한 뒤 번역을 빌드합니다.
잘못된 제어 토큰·수치·능력치 효과는 빌드에서 거부합니다.

## 로컬 설치와 제거

게임을 종료한 상태에서 실행하세요. 이미 설치했다면 제거 후 재설치합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/uninstall_local_playtest.ps1
powershell -ExecutionPolicy Bypass -File scripts/install_local_playtest.ps1
```

첫 설치는 install만 실행합니다. 기존 파일과 충돌하면 설치를 거부하며, 추가 파일의
SHA256을 기록합니다. 제거는 기록과 일치하는 파일만 삭제합니다.
게임 원본 DLL/번들 및 세이브를 덮어쓰지 않습니다. Steam에서 영어 슬롯으로 실행합니다.

## UI 글꼴 후보

현재 기본 빌드는 주아·감자꽃입니다. 사용자가 제공한 **빗썸 고딕 오리지널**은 UI 후보로
별도 비교했습니다. 현재 UI의 한글 420종은 모두 지원하지만, 폰트의 한글 완성형 범위는
2,350자이므로 번역 추가 시 누락 글리프 검사와 대체 글꼴이 필요합니다.
제공된 파일은 Bold Italic 스타일입니다. 아직 게임용 번들에는 반영하지 않았습니다.
로컬 비교 이미지는 `work/ui_fonts/ui-font-comparison.png`입니다.

주아·감자꽃 공개 OFL 원본의 출처는 `docs/PUBLIC_FONT_SOURCES.json`에 있습니다.
해당 폰트 번들과 OFL·저작권 고지는 로컬 설치 시 함께 복사합니다.

남은 작업: 본편 대사·UI 번역, 0.1.1 UI 표시 확인, 긴 문자열/글리프 누락 검증,
저장·로드 및 전체 분기 회귀 검증, 배포 패키징.
