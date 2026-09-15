# -*- coding: utf-8 -*-
"""컷 구간을 장면 중심에 맞춰 배치한다 — 배속은 고정, 겹침은 상한을 둔다.

원본이 나레이션×배속보다 짧으면 어딘가는 되감아 써야 한다(같은 장면을 조금 다시 보여준다).
그 되감기를 한 컷에 몰면 눈에 띄므로, 컷마다 MAXOV 이하로만 겹치게 밀어 고르게 나눈다.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works"))
DEFAULT_SPEED = 1.3   # 사용자 기본값(2026-09-15). plan 에 speed 가 없으면 이 값을 쓴다


def place(L, centers, dur, maxov):
    n = len(L)
    a = [min(max(0.0, c - l / 2), dur - l) for c, l in zip(centers, L)]
    for _ in range(200):
        for i in range(1, n):                       # 앞에서 뒤로: 너무 겹치면 민다
            a[i] = max(a[i], a[i - 1] + L[i - 1] - maxov)
        a[n - 1] = min(a[n - 1], dur - L[n - 1])
        for i in range(n - 2, -1, -1):              # 뒤에서 앞으로: 넘치면 당긴다
            a[i] = min(a[i], a[i + 1] + maxov - L[i])
        if a[0] >= -1e-6:
            a[0] = max(a[0], 0.0)
            return a
    return None


def main(vid, spd, dur, centers, force=None):
    d = json.loads((ROOT / vid / "tts_durations.json").read_text())
    L = [x * spd for x in d]
    need = sum(L) - dur
    lo = max(0.0, need / (len(L) - 1))
    if force:                      # 상한을 직접 줄 수 있다(앞쪽 컷이 뒤로 밀리는 걸 줄인다)
        a = place(L, centers, dur, force)
        if a:
            maxov = force
        else:
            sys.exit(f"{vid}: 상한 {force} 로는 배치 실패")
    else:
      for maxov in [lo + s for s in (0.05, 0.15, 0.3, 0.5, 0.8, 1.2, 2.0)]:
        a = place(L, centers, dur, maxov)
        if a:
            break
      else:
        sys.exit(f"{vid}: 배치 실패 — 원본이 너무 짧다")
    segs = [[round(x, 3), round(x + l, 3)] for x, l in zip(a, L)]
    print(f"== {vid}  원본 {dur}  필요 {sum(L):.2f}  겹침총량 {max(0,need):.2f}  상한 {maxov:.2f}")
    prev = None
    for i, (s, e) in enumerate(segs, 1):
        tag = "" if prev is None else (f"겹침 {prev-s:.2f}" if s < prev - 1e-6 else f"건너뜀 {s-prev:.2f}")
        print(f"  {i:2d}  {s:5.2f}-{e:5.2f}  x{(e-s)/d[i-1]:.3f}  {tag}")
        prev = e
    return segs


if __name__ == "__main__":
    PLAN = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    p = ROOT / "segments_batch.json"
    sg = json.loads(p.read_text(encoding="utf-8"))
    for vid, v in PLAN.items():
        sg[vid] = main(vid, v.get("speed", DEFAULT_SPEED), v["dur"], v["centers"], v.get("maxov"))
    p.write_text(json.dumps(sg, ensure_ascii=False, indent=2), encoding="utf-8")
