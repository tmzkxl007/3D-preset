import subprocess, os

os.makedirs("final_segs", exist_ok=True)

# (raw_file, speed, out_name) -- speed chosen from raw_dur / target_caption_dur, slower for emotional beats
segments = [
    ("s01_raw.mp4", 1.36, "f01.mp4"),
    ("s02_raw.mp4", 1.26, "f02.mp4"),
    ("s03_raw.mp4", 0.93, "f03.mp4"),
    ("s04_raw.mp4", 1.44, "f04.mp4"),
    ("s06_raw.mp4", 3.03, "f05.mp4"),
    ("s07_raw.mp4", 0.57, "f06.mp4"),
    ("s08_raw.mp4", 0.74, "f07.mp4"),
    ("s09_raw.mp4", 1.11, "f08.mp4"),
    ("s10_raw.mp4", 1.71, "f09.mp4"),
    ("s11_raw.mp4", 1.28, "f10.mp4"),
    ("s12_raw.mp4", 2.04, "f11.mp4"),
]

for src, speed, out in segments:
    vf = f"setpts=(1/{speed})*PTS"
    out_path = f"final_segs/{out}"
    cmd = ["ffmpeg", "-y", "-i", src, "-an", "-vf", vf,
           "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
           out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"FAIL {src}: {r.stderr[-800:]}")
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", out_path],
                         capture_output=True, text=True)
    print(f"{out}: speed={speed} -> {float(pr.stdout.strip()):.2f}s")

with open("final_segs/concat_list.txt", "w", encoding="utf-8") as f:
    for _, _, out in segments:
        f.write(f"file '{out}'\n")

r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
                     "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                     "concat.mp4"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd="final_segs")
if r.returncode != 0:
    raise SystemExit(r.stderr[-1500:])

pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", "final_segs/concat.mp4"],
                     capture_output=True, text=True)
print("\nconcat total:", pr.stdout.strip())
