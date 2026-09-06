import os, sys, time, json, urllib.request, urllib.error

key = open(os.path.expanduser("~/.volcano/keys/speechmatics"), encoding="utf-8").read().strip()
base = "https://asr.api.speechmatics.com/v2"
audio_path = "audio.wav"
boundary = "----volcanoBoundary555"

config = {"type": "transcription", "transcription_config": {"language": "en", "operating_point": "enhanced"}}

def build_multipart(config, audio_path, boundary):
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="config"\r\n\r\n')
    parts.append(json.dumps(config).encode())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="data_file"; filename="audio.wav"\r\n'.encode())
    parts.append(b"Content-Type: audio/wav\r\n\r\n")
    with open(audio_path, "rb") as f:
        parts.append(f.read())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)

body = build_multipart(config, audio_path, boundary)
req = urllib.request.Request(base + "/jobs", data=body, method="POST")
req.add_header("Authorization", f"Bearer {key}")
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
with urllib.request.urlopen(req) as resp:
    job_id = json.loads(resp.read())["id"]
print("job_id", job_id)

for _ in range(120):
    r = urllib.request.Request(f"{base}/jobs/{job_id}")
    r.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(r) as resp:
        j = json.loads(resp.read())
    status = j["job"]["status"]
    if status == "done":
        break
    if status == "rejected":
        print(json.dumps(j)); sys.exit(1)
    time.sleep(3)

tr_req = urllib.request.Request(f"{base}/jobs/{job_id}/transcript?format=json-v2")
tr_req.add_header("Authorization", f"Bearer {key}")
with urllib.request.urlopen(tr_req) as resp:
    data = json.loads(resp.read())

words = []
for item in data.get("results", []):
    if item.get("type") == "word":
        words.append({"word": item["alternatives"][0]["content"], "start": item["start_time"], "end": item["end_time"]})

with open("source_words.json", "w", encoding="utf-8") as f:
    json.dump(words, f, ensure_ascii=False, indent=2)
print("word count:", len(words))

tr_req2 = urllib.request.Request(f"{base}/jobs/{job_id}/transcript?format=txt")
tr_req2.add_header("Authorization", f"Bearer {key}")
with urllib.request.urlopen(tr_req2) as resp:
    txt = resp.read().decode("utf-8")
with open("transcript.txt", "w", encoding="utf-8") as f:
    f.write(txt)
