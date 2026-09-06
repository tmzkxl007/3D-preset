# -*- coding: utf-8 -*-
import os, json, urllib.request, subprocess

KEY = open(os.path.expanduser("~/.volcano/keys/typecast"), encoding="utf-8").read().strip()
VOICE_ID = "tc_68257f68bc6e3c161ab5078d"  # Piljae
TTS_DIR = "tts"
os.makedirs(TTS_DIR, exist_ok=True)

LINES = [
    "한 남자가 혼자 앉아 있는 여자에게 다가가 합석을 부탁했습니다.",
    "여자는 다짜고짜 큰 소리로 그가 함께 밤을 보내자고 했다며 몰아붙였어요.",
    "식당 안 사람들은 그를 손가락질하며 수군거렸습니다.",
    "남자는 아무 말 없이 조용히 다른 자리로 걸어갔죠.",
    "잠시 후 여자가 웃으며 다가와 그에게 말을 걸었어요.",
    "사실 자신은 심리학 전공생이라고 밝혔습니다.",
    "사람들이 망신당할 때 어떻게 반응하는지 실험한 거라고 했죠.",
    "그 순간 남자가 갑자기 큰 소리로 되받아쳤습니다.",
    "하룻밤에 이십 달러는 너무 비싸다며 여자를 몰아붙였어요.",
    "식당은 순식간에 웃음바다가 됐습니다.",
    "여자는 얼굴이 굳은 채 아무 말도 하지 못했죠.",
    "남자는 자신이 법학도라며 조용히 되갚아 준 것이었습니다.",
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
