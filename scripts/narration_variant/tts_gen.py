# -*- coding: utf-8 -*-
import os, json, urllib.request, subprocess

KEY = open(os.path.expanduser("~/.volcano/keys/typecast"), encoding="utf-8").read().strip()
VOICE_ID = "tc_68257f68bc6e3c161ab5078d"  # Piljae
TTS_DIR = "tts"
os.makedirs(TTS_DIR, exist_ok=True)

LINES = [
    "한 여자가 놀이터에서 아이를 지켜보다 낯선 남자를 발견했습니다.",
    "그 남자는 아이들 곁을 계속 서성이고 있었죠.",
    "옆에 있던 다른 엄마는 그가 매일 그렇게 아이들을 지켜본다고 귀띔했어요.",
    "여자는 점점 더 불안해졌습니다.",
    "결국 신고할 준비까지 마쳤죠.",
    "그 순간 한 남자아이가 놀이기구에서 미끄러졌습니다.",
    "낯선 남자는 재빨리 달려가 아이를 받아냈죠.",
    "아이 아버지가 다가오자 그는 조용히 사정을 털어놨습니다.",
    "삼 년 전 이 놀이기구에서 아들을 잃었다고 했어요.",
    "그날 이후 매일 이곳에 나와 아이들을 지켜봐 왔던 겁니다.",
    "그 사실을 알게 된 여자는 눈물을 참지 못했습니다.",
    "겉모습만으로 사람을 판단해선 안 된다는 걸 보여준 순간이었죠.",
]

durations = []
for i, text in enumerate(LINES, start=1):
    mp3_path = f"{TTS_DIR}/line{i:02d}.mp3"
    if not os.path.exists(mp3_path):
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
    # speed up 1.2x (pitch preserved)
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
