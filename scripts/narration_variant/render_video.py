# -*- coding: utf-8 -*-
import subprocess, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = REPO_ROOT / "assets"
LOGO = str(ASSETS / "두둥픽_로고_템플릿.png")
FONTS_DIR = str(ASSETS / "fonts").replace("\\", "/").replace(":", "\:")

concat_in, ass_path, out_video = "final_segs/concat.mp4", "captions.ass", "video_only.mp4"
ass_escaped = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\:")

WIN_Y, WIN_H = 488, 1010
# 크롭은 build_segments.py 에서 컷마다 따로 적용한다(3D.md 2번)
DURATION = 42.956

filter_complex = (
    f"[0:v]tpad=stop_mode=clone:stop_duration=1,"
    f"eq=gamma_r=1.05:gamma_b=0.95:saturation=1.08:contrast=1.03,"
    f"pad=1080:1920:0:{WIN_Y}:color=black[padded];"
    f"[padded][1:v]overlay=0:0:format=auto,"
    f"ass='{ass_escaped}':fontsdir='{FONTS_DIR}'[outv]"
)
cmd = ["ffmpeg","-y","-v","error","-i",concat_in,"-loop","1","-i",LOGO,
       "-filter_complex",filter_complex,"-map","[outv]","-t",str(DURATION),
       "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",out_video]
r = subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace")
if r.returncode: raise SystemExit(r.stderr[-3000:])
print("OK ->", out_video)
