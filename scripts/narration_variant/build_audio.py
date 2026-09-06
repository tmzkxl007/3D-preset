import subprocess

TTS_DIR = "tts"
DRUM = r"C:\Users\Administrator\OneDrive\바탕 화면\volcano-work\3D\assets\두둥_북소리.mp3"
PAD = 0.15
N = 12

subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", str(PAD), "silence.mp3"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")

with open("narration_concat.txt", "w", encoding="utf-8") as f:
    for i in range(1, N + 1):
        f.write(f"file '{TTS_DIR}/line{i:02d}_fast.mp3'\n")
        if i != N:
            f.write("file 'silence.mp3'\n")

r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "narration_concat.txt",
                     "-c:a", "libmp3lame", "-q:a", "2", "narration.mp3"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
if r.returncode != 0:
    raise SystemExit(r.stderr[-1500:])

pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", "narration.mp3"],
                     capture_output=True, text=True)
print("narration duration:", pr.stdout.strip())

filter_complex = (
    "[0:a]volume=1.0[narr];"
    "[1:a]volume=8dB[drum];"
    "[narr][drum]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
    "alimiter=limit=0.95[aout]"
)
cmd = [
    "ffmpeg", "-y",
    "-i", "narration.mp3",
    "-i", DRUM,
    "-filter_complex", filter_complex,
    "-map", "[aout]",
    "-c:a", "aac", "-b:a", "192k",
    "audio_mix.m4a",
]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.returncode)
if r.returncode != 0:
    print(r.stderr[-3000:])
else:
    print("OK -> audio_mix.m4a")
