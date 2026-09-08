# 새 컴퓨터에서 3D 프리셋 쓰기

이 저장소를 clone하면 스타일 문서(`3D.md`, `examples.md`)와 재사용 자산(`assets/`), 나레이션 버전 파이프라인 스크립트(`scripts/narration_variant/`)가 그대로 옵니다. 그 외에 아래 실행 환경을 갖춰야 스크립트가 돌아갑니다.

## 1. 저장소 받기

```
git clone https://github.com/nm2240/3D-preset.git
cd 3D-preset
```

`assets/` 폴더에 워터마크 로고 PNG, 두둥 드럼 효과음, 폰트 2종(`assets/fonts/`)이 전부 포함되어 있습니다 — 폰트를 따로 설치하거나 구할 필요 없습니다.

## 2. 소프트웨어 설치

- **ffmpeg** — 설치 후 PATH에 등록되어 있어야 함 (`ffmpeg -version`으로 확인)
- **Python 3.10+**
- **Pillow**: `pip install Pillow` (스크립트가 쓰는 외부 패키지는 이것 하나뿐 — 나머지는 표준 라이브러리)
- **yt-dlp** — 유튜브 등에서 소스 영상을 받을 때 사용 (`yt-dlp -f "bv*+ba/b" --merge-output-format mp4 -o "source.%(ext)s" <URL>`). winget/pip 등으로 설치, PATH 등록 확인 (`yt-dlp --version`).

## 3. API 키 설정

스크립트는 아래 환경변수를 먼저 찾고, 없으면 `~/.volcano/keys/<파일명>` 경로의 텍스트 파일을 대신 읽습니다(둘 중 하나만 있으면 됨).

| 용도 | 환경변수 | 대체 파일 경로 | 발급처 |
|---|---|---|---|
| TTS 나레이션 | `TYPECAST_API_KEY` | `~/.volcano/keys/typecast` | https://typecast.ai |
| 자막 타이밍(ASR) | `SPEECHMATICS_API_KEY` | `~/.volcano/keys/speechmatics` | https://www.speechmatics.com |
| 잔여 자막 제거(선택) | `MT_AK` / `MT_SK` | — (SDK가 직접 환경변수만 읽음) | https://vmake.ai |

PowerShell 예시:
```powershell
$env:TYPECAST_API_KEY = "..."
$env:SPEECHMATICS_API_KEY = "..."
```
또는 파일로:
```powershell
"..." | Out-File -Encoding utf8 "$HOME\.volcano\keys\typecast"
"..." | Out-File -Encoding utf8 "$HOME\.volcano\keys\speechmatics"
```

**Vmake는 대부분 필요 없습니다.** `3D.md` 14번 항목대로, 원본 영상의 잔여 자막이 화면 하단/상단에 있으면 `render_video.py`의 `CROP_Y` 값을 조정해 크롭으로 무료로 제거하는 게 기본값입니다. 정중앙에 있어서 크롭으로 못 피할 때만 Vmake가 필요하고, 그때는 Vmake 파이썬 SDK를 https://vmake.ai 에서 별도로 받아야 합니다(이 저장소에는 포함돼 있지 않음).

## 4. 새 영상 만들 때

`scripts/narration_variant/`의 스크립트들은 **참고용 템플릿**입니다 — 그대로 재실행하지 말고, 매 영상마다 아래 값들을 그 영상에 맞게 새로 채워서 씁니다:

1. `tts_gen.py`의 `LINES` — 그 영상의 대본 (원문 번역이 아니라 사실 재구성, `3D.md` 5·15번 항목 참고)
2. `build_ass.py`의 `FRAGMENTS`, `TITLE_LINES` — 대본에 맞는 자막 조각과 제목 (`3D.md` 16번 항목의 제목 하위 패턴 참고)
3. `build_segments.py`의 `segments` — 원본 영상에서 어느 구간을, 어떤 배속으로 쓸지 (`3D.md` 13번 항목: 인물 매칭 절차)
4. `render_video.py`의 `CROP_Y`, `-t` 길이값 — 그 영상의 잔여 자막 위치와 최종 길이에 맞게

실행 순서: `tts_gen.py` → `asr_align.py` → `build_segments.py` → `build_audio.py` → `build_ass.py` → `render_video.py` → 마지막에 ffmpeg로 영상+오디오 mux.

작업 폴더(각 영상 프로젝트 디렉터리)는 저장소 밖에 따로 두고, 이 저장소의 `assets/`와 `scripts/narration_variant/`만 참조하면 됩니다.
