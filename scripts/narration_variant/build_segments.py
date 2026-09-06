import subprocess, os

os.makedirs("final_segs", exist_ok=True)

# (clean_file, speed, out_name)
segments = [
    ("s01_clean.mp4", 1.26, "f01.mp4"),
    ("s02_clean.mp4", 1.19, "f02.mp4"),
    ("s03_clean.mp4", 1.30, "f03.mp4"),
    ("s04_clean.mp4", 0.89, "f04.mp4"),
    ("s05_clean.mp4", 1.23, "f05.mp4"),
    ("s06_clean.mp4", 0.91, "f06.mp4"),
    ("s07_clean.mp4", 0.79, "f07.mp4"),
    ("s08_clean.mp4", 0.74, "f08.mp4"),
    ("s09_clean.mp4", 0.75, "f09.mp4"),
    ("s10_clean.mp4", 0.91, "f10.mp4"),
    ("s11_clean.mp4", 1.30, "f11.mp4"),
    ("s12_clean.mp4", 1.47, "f12.mp4"),
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
