# -*- coding: utf-8 -*-
import subprocess, os, json

os.makedirs("final_segs", exist_ok=True)
PAD = 0.15
durs = json.load(open("tts_durations.json"))
targets = [d + PAD for d in durs[:-1]] + [durs[-1]]

# (src_start, src_end) chosen by matching each sentence's subject to what is on screen (3D.md #13)
RANGES = [
    (0.00,  2.60),   # 1 he falls onto the tracks
    (2.60,  5.40),   # 2 train wheels roll over his legs
    (5.20,  7.00),   # 3 legs sliced off / aftermath
    (6.00,  9.30),   # 4 recovered, struggling at the railway job
    (9.30, 12.60),   # 5 buys a baboon, brings it to work
    (12.60,15.90),   # 6 baboon copies the man by watching
    (15.90,19.10),   # 7 train whistle -> baboon pulls the lever
    (19.10,22.00),   # 8 right levers, tracks switching
    (21.90,24.60),   # 9 officials test its skills (clipboard)
    (24.00,26.90),   # 10 hired full time (baboon in the cap)
    (26.90,29.90),   # 11 20 cents and half a beer
    (29.90,35.00),   # 12 nine years, never a mistake
]
# 컷마다 세로 위치를 따로 준다(3D.md 2번). 원본 박제 자막이 y>=1456이라 430이 상한이다.
CROP_Y = [300]*12
CROP_Y[11] = 430          # 마지막 컷: 화면 아래쪽에 있는 원숭이를 살린다
assert len(RANGES) == len(targets) == len(CROP_Y)

names = []
for i, ((a, b), tgt) in enumerate(zip(RANGES, targets), start=1):
    raw = b - a
    speed = raw / tgt
    out = f"final_segs/f{i:02d}.mp4"
    cy = CROP_Y[i-1]
    vf = (f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
          f"crop=1080:1010:0:{cy},setpts=(1/{speed:.6f})*PTS,fps=30")
    cmd = ["ffmpeg","-y","-v","error","-ss",f"{a:.3f}","-to",f"{b:.3f}","-i","source.mp4","-an",
           "-vf",vf,"-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",out]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode: raise SystemExit(f"FAIL {i}: {r.stderr[-800:]}")
    pr = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                         "-of","default=noprint_wrappers=1:nokey=1",out],capture_output=True,text=True)
    got = float(pr.stdout.strip())
    print(f"f{i:02d}: src {a:5.2f}-{b:5.2f} raw={raw:.2f} speed={speed:.2f} cropY={cy} -> {got:.2f}s (target {tgt:.2f})")
    names.append(os.path.basename(out))

with open("final_segs/concat_list.txt","w",encoding="utf-8") as f:
    for n in names: f.write(f"file '{n}'\n")
r = subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i","concat_list.txt",
                    "-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p","concat.mp4"],
                   capture_output=True,text=True,encoding="utf-8",errors="replace",cwd="final_segs")
if r.returncode: raise SystemExit(r.stderr[-1500:])
pr = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                     "-of","default=noprint_wrappers=1:nokey=1","final_segs/concat.mp4"],capture_output=True,text=True)
print("\nconcat total:", pr.stdout.strip(), " | narration total:", round(sum(targets),3))
