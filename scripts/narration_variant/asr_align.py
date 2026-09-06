# -*- coding: utf-8 -*-
import os, sys, time, json, urllib.request, urllib.error

key = open(os.path.expanduser("~/.volcano/keys/speechmatics"), encoding="utf-8").read().strip()
base = "https://asr.api.speechmatics.com/v2"
TTS_DIR = "tts"
N = 12

def build_multipart(config, audio_path, boundary):
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="config"\r\n\r\n')
    parts.append(json.dumps(config).encode())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="data_file"; filename="a.mp3"\r\n'.encode())
    parts.append(b"Content-Type: audio/mpeg\r\n\r\n")
    with open(audio_path, "rb") as f:
        parts.append(f.read())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)

def submit(audio_path, lang="ko", operating_point="enhanced"):
    config = {
        "type": "transcription",
        "transcription_config": {"language": lang, "operating_point": operating_point},
    }
    boundary = "----volcanoBoundary987654"
    body = build_multipart(config, audio_path, boundary)
    req = urllib.request.Request(base + "/jobs", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["id"]

def poll(job_id):
    url = f"{base}/jobs/{job_id}"
    for _ in range(120):
        r = urllib.request.Request(url)
        r.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(r) as resp:
            j = json.loads(resp.read())
        status = j["job"]["status"]
        if status == "done":
            return True
        if status == "rejected":
            print("REJECTED", json.dumps(j))
            return False
        time.sleep(2)
    return False

def fetch_words(job_id):
    tr_req = urllib.request.Request(f"{base}/jobs/{job_id}/transcript?format=json-v2")
    tr_req.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(tr_req) as resp:
        data = json.loads(resp.read())
    words = []
    for item in data.get("results", []):
        if item.get("type") == "word":
            alt = item["alternatives"][0]
            words.append({
                "word": alt["content"],
                "start": item["start_time"],
                "end": item["end_time"],
            })
    return words

results = {}
for i in range(1, N + 1):
    path = f"{TTS_DIR}/line{i:02d}_fast.mp3"
    try:
        job_id = submit(path)
    except urllib.error.HTTPError as e:
        print(i, "submit error", e.code, e.read().decode())
        results[i] = []
        continue
    ok = poll(job_id)
    if not ok:
        results[i] = []
        continue
    words = fetch_words(job_id)
    results[i] = words
    print(i, "words:", [w["word"] for w in words])

with open("tts_word_align.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("DONE")
