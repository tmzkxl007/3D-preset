# -*- coding: utf-8 -*-
"""원본에 박제된 자막의 y 위치를 측정하고, 크롭이 그것을 배제하는지 확인한다.

자막은 흰 글자 + 검은 외곽선이라 그 행에서 가로 방향 밝기 변화(엣지)가 폭증한다.
여러 프레임에서 행별 엣지 강도를 평균내면 자막 띠가 봉우리로 드러난다.
"""
import subprocess, numpy as np, json, sys
from pathlib import Path

H, W = 1920, 1080          # 1920 기준으로 환산해 본다
CROP_Y, CROP_H = 300, 1010

def rows(vid):
    src = Path(vid) / "source.mp4"
    dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(src)],
        capture_output=True,text=True).stdout.strip())
    acc = np.zeros(H)
    n = 0
    for t in np.linspace(1.0, dur - 1.0, 12):
        o = subprocess.run(["ffmpeg","-v","error","-ss",f"{t:.2f}","-i",str(src),
                            "-frames:v","1","-vf",f"scale={W}:{H},format=gray",
                            "-f","rawvideo","-"],capture_output=True)
        if len(o.stdout) < W*H: continue
        g = np.frombuffer(o.stdout,dtype=np.uint8)[:W*H].reshape(H,W).astype(float)
        bright = g > 215                                  # 흰 글자
        edge = np.abs(np.diff(g,axis=1)) > 55             # 외곽선 경계
        acc += bright[:,1:].sum(1) * edge.sum(1) / W
        n += 1
    return acc / max(n,1)

for vid in sys.argv[1:]:
    r = rows(vid)
    band = r[900:1750]
    peak = int(np.argmax(band)) + 900
    thr = max(band.mean()*4, 1.0)
    hits = np.where(band > thr)[0] + 900
    top, bot = (int(hits.min()), int(hits.max())) if len(hits) else (peak, peak)
    crop_lo, crop_hi = CROP_Y, CROP_Y + CROP_H
    safe = bot < crop_lo or top >= crop_hi
    print(f"{vid:14s} 자막띠 y={top}~{bot} (봉우리 {peak})  크롭 {crop_lo}~{crop_hi}  "
          + ("배제됨 OK" if safe else "!! 크롭 안에 들어옴"))
