import subprocess, os

LOGO = r"C:\Users\Administrator\OneDrive\바탕 화면\volcano-work\3D\assets\두둥픽_로고_템플릿.png"
FONTS_DIR = r"C:\Users\Administrator\OneDrive\바탕 화면\volcano-work\fonts_3d".replace("\\", "/").replace(":", "\\:")

concat_in = "final_segs/concat.mp4"
ass_path = "captions.ass"
out_video = "video_only.mp4"

ass_escaped = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")

WIN_Y, WIN_H = 488, 1010
CROP_Y = 300  # upper-biased crop (not centered) so bottom-of-frame leftover captions fall outside the window

filter_complex = (
    f"[0:v]crop=1080:{WIN_H}:0:{CROP_Y},"
    f"eq=gamma_r=1.05:gamma_b=0.95:saturation=1.08:contrast=1.03,"
    f"pad=1080:1920:0:{WIN_Y}:color=black[padded];"
    f"[padded][1:v]overlay=0:0:format=auto,"
    f"ass='{ass_escaped}':fontsdir='{FONTS_DIR}'[outv]"
)

cmd = [
    "ffmpeg", "-y",
    "-i", concat_in,
    "-loop", "1", "-i", LOGO,
    "-filter_complex", filter_complex,
    "-map", "[outv]",
    "-t", "43.586553",
    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
    out_video,
]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.returncode)
if r.returncode != 0:
    print(r.stderr[-3000:])
else:
    print("OK ->", out_video)
