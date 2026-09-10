# 배치 파이프라인 — 여러 편을 한 번에 만들 때

한 편만 만들 때는 `../narration_variant/` 의 템플릿을 작업 폴더로 복사해 쓴다.
**여러 편을 동시에** 만들 때 이쪽을 쓴다. 작업 폴더는 `VOLCANO_WORKDIR`(기본 `~/3d_works`).

```
python stage1_fetch.py <영상id> [영상id ...]     # 다운로드 + 원본 ASR (동시)
#   -> 대본을 쓴다: 작업폴더/scripts_batch.json  (아래 형식)
python stage3_tts.py  [영상id ...]                # TTS + 단어 정렬 (동시)
#   -> 문장별 원본 구간을 정한다: 작업폴더/segments_batch.json
python check_crop.py  <영상id ...>                # 원본 박제 자막이 크롭 밖인지 검증
python stage5_build.py [영상id ...]               # 자막·세그먼트·오디오·렌더 (3편 동시)
python verify_final_audio.py [영상id ...]         # 완성본 오디오를 ASR 로 대본과 대조
```

마지막에 `../../preset_guard.py <완성본.mp4>` 로 규격을 확인하고 납품한다.

## scripts_batch.json

```json
{ "<영상id>": {
    "slug": "파일명에 쓸 짧은 이름",
    "title": ["제목 윗줄", "제목 아랫줄"],
    "title_pattern": "이유형 | 의도형 | 방법형 | 정체형 | 최후형 | 반전대비형",
    "target_sec": 43,
    "lines": ["문장 1.", "문장 2."]
} }
```

## segments_batch.json

문장 수와 같은 개수의 `[시작초, 끝초]` 배열. 원본에서 그 문장에 맞는 장면 구간이다.
길이는 배속으로 환산되므로(3D.md 13번) 눈대중으로 잡은 뒤 **중심점은 두고 길이만 재계산**한다:
기본 배속 = (쓰는 구간 전체 길이) / (나레이션 총 길이). 배속은 0.70~1.90 을 벗어나면 안 된다.

## 실측해서 알게 된 것

- **Typecast 는 동시 요청 6개에서 429 를 던진다.** `stage3_tts.py` 는 동시성 2 + 백오프 재시도로 돌린다. 다운로드·ASR·렌더는 5~6개 동시가 문제없다 — **TTS 가 병목**이다.
- **대본을 고치면 그 영상의 TTS 를 통째로 다시 만든다.** `stage3_tts.py` 는 매번 `tts/` 를 비운다(3D.md 12번의 캐시 사고 방지).
- 한 번에 **3~5편**이 적당하다. 그 이상은 장면 매칭과 검수가 얕아진다.
