import subprocess, os

os.makedirs("final_segs", exist_ok=True)

# (input_file, speed, out_name)
segments = [
    ("seg1_clean.mp4", 1.32, "f1.mp4"),
    ("seg2_clean.mp4", 1.53, "f2.mp4"),
    ("seg3_clean.mp4", 0.70, "f3.mp4"),
    ("seg4_clean.mp4", 0.73, "f4.mp4"),
    ("seg5_clean.mp4", 0.70, "f5.mp4"),
    ("seg4_clean.mp4", 0.83, "f6.mp4"),
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
