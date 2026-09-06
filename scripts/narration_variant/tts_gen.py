# -*- coding: utf-8 -*-
import os, json, urllib.request, subprocess

KEY = open(os.path.expanduser("~/.volcano/keys/typecast"), encoding="utf-8").read().strip()
VOICE_ID = "tc_68257f68bc6e3c161ab5078d"  # Piljae
TTS_DIR = "tts"
os.makedirs(TTS_DIR, exist_ok=True)

LINES = [
    "한 싱글맘이 낚시를 하다가 오래된 램프를 주웠습니다.",
    "램프를 문지르자 지니가 나타나 소원 하나를 들어주겠다고 했어요.",
    "하지만 그녀가 받는 것의 두 배를 전남편이 받는다는 조건이었습니다.",
    "전남편은 젊은 아내와 부자가 됐지만 그녀는 생선을 팔며 살아왔죠.",
    "그녀는 한참을 서성이며 괴로워했습니다.",
    "마침내 걸음을 멈춘 그녀의 얼굴에 서서히 미소가 번졌죠.",
    "그녀는 자신의 한쪽 눈을 멀게 해달라고 소원을 빌었습니다.",
    "지니는 고개를 젓고는 결국 소원을 들어줬어요.",
    "다음 날 전남편은 눈이 멀어 계단에서 떨어져 숨졌습니다.",
    "그녀는 한쪽 눈만 남은 채 눈물을 흘렸습니다.",
    "질투는 내 눈을 잃더라도 상대가 지길 바란다는 이야기였죠.",
]

durations = []
for i, text in enumerate(LINES, start=1):
    mp3_path = f"{TTS_DIR}/line{i:02d}.mp3"
    body = json.dumps({
        "voice_id": VOICE_ID,
        "text": text,
        "model": "ssfm-v30",
        "language": "kor",
        "prosody": {"emotion_preset": "normal"},
        "output": {"audio_format": "mp3"},
    }).encode("utf-8")
    req = urllib.request.Request("https://api.typecast.ai/v1/text-to-speech", data=body, method="POST")
    req.add_header("X-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    with open(mp3_path, "wb") as f:
        f.write(raw)
    fast_path = f"{TTS_DIR}/line{i:02d}_fast.mp3"
    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-filter:a", "atempo=1.2",
                     "-c:a", "libmp3lame", "-q:a", "2", fast_path],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", fast_path],
                         capture_output=True, text=True)
    dur = float(pr.stdout.strip())
    durations.append(dur)
    print(f"line{i:02d}: {dur:.2f}s | {text}")

with open("tts_durations.json", "w", encoding="utf-8") as f:
    json.dump(durations, f)
print("\ntotal:", sum(durations))
