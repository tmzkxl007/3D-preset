# -*- coding: utf-8 -*-
"""TTS 문장별 앞뒤 공백을 잘라낸다.

타입캐스트 mp3 는 문장마다 앞 0.25초 · 뒤 0.28초쯤 무음이 붙어 나온다.
그대로 이어붙이면 전체의 20% 가 공백이 된다.

원본은 tts/raw/ 에 보관하고 항상 거기서 다시 자른다(두 번 돌려도 결과가 같다).
단어 정렬 타임스탬프도 잘라낸 앞부분만큼 당겨준다 — ASR 을 다시 부르지 않는다.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works"))
GUARD_HEAD = 0.02      # 파열음 첫머리가 잘리지 않게 남기는 여유
GUARD_TAIL = 0.03
THR = 0.012            # 이보다 작으면 무음으로 본다


def pcm(path):
    o = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "44100",
                        "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(o.stdout, dtype=np.float32)


def bounds(path):
    x = pcm(path)
    if not len(x):
        return None
    env = np.convolve(np.abs(x), np.ones(441) / 441, mode="same")
    loud = np.where(env > THR)[0]
    if not len(loud):
        return None
    dur = len(x) / 44100
    a = max(0.0, loud[0] / 44100 - GUARD_HEAD)
    b = min(dur, loud[-1] / 44100 + GUARD_TAIL)
    return dur, a, b


targets = sys.argv[1:]
if not targets:
    sys.exit("사용법: python trim_silence.py <영상id ...>")

for vid in targets:
    d = ROOT / vid
    tts = d / "tts"
    raw = tts / "raw"
    raw.mkdir(exist_ok=True)

    files = sorted(tts.glob("line*_fast.mp3"))
    if not files:
        print(f"{vid}: tts 파일 없음"); continue

    # 처음 한 번만 원본을 보관한다
    for f in files:
        keep = raw / f.name
        if not keep.exists():
            keep.write_bytes(f.read_bytes())
    align_raw = d / "tts_word_align_raw.json"
    if not align_raw.exists():
        align_raw.write_bytes((d / "tts_word_align.json").read_bytes())

    align = json.loads(align_raw.read_text(encoding="utf-8"))
    new_align, durs, saved = {}, [], 0.0

    for i, f in enumerate(sorted(raw.glob("line*_fast.mp3")), start=1):
        bb = bounds(f)
        if bb is None:
            print(f"  {vid} line{i:02d}: 소리 없음 — 건너뜀"); continue
        dur, a, b = bb
        out = tts / f.name
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                            "-i", str(f), "-c:a", "libmp3lame", "-q:a", "2", str(out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise SystemExit(f"{vid} line{i}: {r.stderr[-300:]}")
        new_dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
            capture_output=True, text=True).stdout.strip())
        durs.append(new_dur)
        saved += dur - new_dur
        # 정렬 타임스탬프를 잘라낸 앞부분만큼 당긴다
        new_align[str(i)] = [{"word": w["word"],
                              "start": max(0.0, w["start"] - a),
                              "end": max(0.0, w["end"] - a)}
                             for w in align.get(str(i), [])]

    (d / "tts_durations.json").write_text(json.dumps(durs), encoding="utf-8")
    (d / "tts_word_align.json").write_text(
        json.dumps(new_align, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {vid}: {len(durs)}문장  공백 {saved:.1f}초 제거  →  나레이션 {sum(durs):.1f}초")
