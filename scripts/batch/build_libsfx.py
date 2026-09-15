# -*- coding: utf-8 -*-
"""CC0 효과음 라이브러리에서 골라 컷마다 얹는다.

원본(Zack D. Films)에는 효과음이 없다 -- 나레이션과 배경음악 두 겹뿐이다.
목소리를 떼어내도 남는 건 음악이라, 원본에서 뽑아 쓰는 길은 막혔다(2026-09-15 확인).
그래서 archive.org 의 Red Library(USC Cinema, CC0 1.0)에서 장면에 맞는 소리를 받아 쓴다.

배치는 sfx_plan.json 에 컷 번호별로 적는다.

    {"9vPLv3UAKnY": {"1": ["skid_tires", 0.5, 0.0], ...}}
              컷 번호   파일 이름   소스 시작초  게인dB

효과음은 사건이 있는 컷에만 넣는다. 전 컷에 깔면 배경음악과 다를 바 없어진다.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works"))
LIB = ROOT / "sfxlib"
OPEN_LEAD = 0.55
SR = 48000
FADE = 0.08


def run(c, **k):
    return subprocess.run(c, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **k)


def load(path, start, dur):
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}",
                        "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(o.stdout, dtype=np.float32).copy()


def main(vid, plan, base_db=0.0):
    durs = json.loads((ROOT / vid / "tts_durations.json").read_text())
    total = OPEN_LEAD + sum(durs)
    out = np.zeros(int(total * SR) + SR, dtype=np.float32)

    t = OPEN_LEAD
    used = []
    for i, d in enumerate(durs, 1):
        spec = plan.get(str(i))
        if spec:
            name, src_start, gain = spec
            x = load(LIB / f"{name}.mp3", src_start, d)
            if len(x):
                x = x / (np.abs(x).max() + 1e-9)            # 파일마다 레벨이 다르다
                f = int(FADE * SR)
                if len(x) > 2 * f:                          # 앞뒤를 눕혀 뚝 끊기지 않게
                    x[:f] *= np.linspace(0, 1, f)
                    x[-f:] *= np.linspace(1, 0, f)
                x *= 10 ** ((gain + base_db) / 20)
                s = int(t * SR)
                out[s:s + len(x)] += x[:len(out) - s]
                used.append(f"컷{i}:{name}")
        t += d

    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1",
                        "-i", "-", "-ar", "48000", "-ac", "1", str(ROOT / vid / "srcsfx.wav")],
                       input=out.tobytes(), capture_output=True)
    if p.returncode:
        raise SystemExit(p.stderr[-300:].decode("utf-8", "replace"))
    print(f"  {vid}: 효과음 {len(used)}개  " + " ".join(used))


if __name__ == "__main__":
    vid = sys.argv[1]
    plans = json.loads((ROOT / "sfx_plan.json").read_text(encoding="utf-8"))
    main(vid, plans[vid], float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
