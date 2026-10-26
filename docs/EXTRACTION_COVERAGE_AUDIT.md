# v0.1.0 번역 추출 누락 추가 감사 (2026-10-26)

## 판정

**현재 설치된 Monster Con 빌드의 등록된 지역화 텍스트 자산에서는 추가 누락을 발견하지 못함.**
이는 번역된 전체 문장의 문학적 품질이나 모든 인게임 UI/이미지·하드코딩 문구의 한글
출력을 보증하는 결론은 아니다.

### 검증한 범위

- `StandaloneWindows`의 번들 **40개**를 열어 `TextAsset` 총 **30개**를 조사.
- 게임의 `TextFileProfile` 등록 정보를 직접 확인: 지역화 텍스트 16개,
  비지역화 구조 파일 2개. 별도의 `english_metatexts`를 합쳐 지역화 원문 **17개**.
- 원문·SHA-256·기존 카탈로그에 대해 **별도의 표시 필드 인식기**로 추출 수 검증.
  기존 추출기의 `ordinary_display_field`를 참조하지 않음.
- 독립 판정된 표시 필드 **24,274개**와 현재 카탈로그 **24,274개**가 정확히 일치.
  원문과 카탈로그의 필드 값 및 메타텍스트 키도 일치.
- `>comic_answer`의 선택지/변형 표시 필드 288개(기존 QA6에서 추가),
  `>choice`, `>action`, 기본 대사, 퀴즈 `>question`/`>image`,
  시작 취향, 메타텍스트를 검사.
- `conditions_secret_endings`, `comic_panels_cutscenes`은
  원본 게임에서도 비지역화 TextFileProfile이며 조건/컷신 배치 형식이다.
  추가 대사 파일로 잘못 취급하지 않음.
- 도전 과제의 `>>> challenge` 헤더 5번째 필드(예: `ANIMAL`)는
  `CoreParser.LoadChallenges` IL 기준 사용되지 않음.
  실제 대화 본문은 뒤따르는 표시 행에서 처리한다.

## 한계 및 후속 확인

이번 감사는 **TextAsset의 파서/메타텍스트 공급 경로**를 다루며 다음은 별도의
확인이 필요하다.

- Unity 씬/프리팹에 직접 들어간 문자열, 런타임에서 만들어지는 문자열,
  게임 실행 조건에 의존하는 출력.
- 그림·스프라이트 안에 그려진 글자와 실제 화면 줄바꿈·말풍선 폭.
- 별도 UI 이미지 번역 보고서의 전체 인게임 표시 및 모든 분기 플레이.

원본 게임 업데이트 시 다음을 다시 실행한다.

```powershell
python -X utf8 scripts/extract_assets.py
python -X utf8 scripts/audit_extraction_coverage.py
python -X utf8 scripts/build_playtest.py
python -X utf8 scripts/audit_translation.py
python -X utf8 -m unittest discover -s tests
```

증거: [EXTRACTION_COVERAGE_AUDIT.json](EXTRACTION_COVERAGE_AUDIT.json).
번역 자산/패치 파일 자체는 변경하지 않았으므로 **v0.1.0 재배포는 필요하지 않다**.
