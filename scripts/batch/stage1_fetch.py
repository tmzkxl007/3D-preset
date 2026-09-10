# -*- coding: utf-8 -*-
"""1단계 — 링크 전부 동시에 받고, 원본 나레이션을 동시에 전사한다."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works"))
# 작업 폴더는 저장소 밖에 둔다. VOLCANO_WORKDIR 로 바꿀 수 있다.
IDS = sys.argv[1:]

KEY = os.environ.get("SPEECHMATICS_API_KEY") or \
    open(os.path.expanduser("~/.volcano/keys/speechmatics"), encoding="utf-8").read().strip()
BASE = "https://asr.api.speechmatics.com/v2"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def fetch(vid):
    d = ROOT / vid
    d.mkdir(parents=True, exist_ok=True)
    src = d / "source.mp4"
    if not src.exists():
        r = run(["yt-dlp", "-f", "bv*+ba/b", "--merge-output-format", "mp4",
                 "-o", str(d / "source.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"])
        if r.returncode:
            return vid, {"error": r.stderr[-300:]}
    meta = run(["yt-dlp", "--skip-download", "--print", "%(title)s\t%(channel)s\t%(duration)s",
                f"https://www.youtube.com/watch?v={vid}"])
    title, channel, dur = (meta.stdout.strip().split("\t") + ["", "", ""])[:3]
    pr = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=width,height", "-show_entries", "format=duration",
              "-of", "json", str(src)])
    p = json.loads(pr.stdout or "{}")
    st = (p.get("streams") or [{}])[0]
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
         str(d / "audio.wav")])
    return vid, {"title": title, "channel": channel,
                 "w": st.get("width"), "h": st.get("height"),
                 "dur": float(p.get("format", {}).get("duration", 0) or 0)}


def asr_submit(vid):
    path = ROOT / vid / "audio.wav"
    b = f"----v{vid}"
    cfg = {"type": "transcription",
           "transcription_config": {"language": "en", "operating_point": "enhanced"}}
    parts = [f"--{b}\r\n".encode(),
             b'Content-Disposition: form-data; name="config"\r\n\r\n',
             json.dumps(cfg).encode(), b"\r\n", f"--{b}\r\n".encode(),
             b'Content-Disposition: form-data; name="data_file"; filename="a.wav"\r\n',
             b"Content-Type: audio/wav\r\n\r\n", path.read_bytes(), b"\r\n",
             f"--{b}--\r\n".encode()]
    req = urllib.request.Request(BASE + "/jobs", data=b"".join(parts), method="POST")
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={b}")
    return json.loads(urllib.request.urlopen(req).read())["id"]


def asr_collect(vid, job):
    for _ in range(200):
        r = urllib.request.Request(f"{BASE}/jobs/{job}")
        r.add_header("Authorization", f"Bearer {KEY}")
        st = json.loads(urllib.request.urlopen(r).read())["job"]["status"]
        if st == "done":
            break
        if st == "rejected":
            return vid, "REJECTED"
        time.sleep(3)
    d = ROOT / vid
    for fmt, name in (("json-v2", "source_words.json"), ("txt", "transcript.txt")):
        q = urllib.request.Request(f"{BASE}/jobs/{job}/transcript?format={fmt}")
        q.add_header("Authorization", f"Bearer {KEY}")
        raw = urllib.request.urlopen(q).read()
        if fmt == "txt":
            (d / name).write_text(raw.decode("utf-8"), encoding="utf-8")
        else:
            data = json.loads(raw)
            words = [{"word": i["alternatives"][0]["content"],
                      "start": i["start_time"], "end": i["end_time"]}
                     for i in data.get("results", []) if i.get("type") == "word"]
            (d / name).write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
    return vid, (d / "transcript.txt").read_text(encoding="utf-8").strip()


with ThreadPoolExecutor(max_workers=5) as ex:
    metas = dict(ex.map(fetch, IDS))
print("=== 받은 영상 ===")
for vid in IDS:
    m = metas[vid]
    if "error" in m:
        print(f"  {vid}  실패: {m['error']}")
    else:
        print(f"  {vid}  {m['w']}x{m['h']}  {m['dur']:.1f}s  [{m['channel']}] {m['title']}")

ok = [v for v in IDS if "error" not in metas[v]]
with ThreadPoolExecutor(max_workers=5) as ex:
    jobs = dict(zip(ok, ex.map(asr_submit, ok)))
with ThreadPoolExecutor(max_workers=5) as ex:
    texts = dict(ex.map(lambda v: asr_collect(v, jobs[v]), ok))

print("\n=== 원본 나레이션 ===")
for vid in ok:
    print(f"\n--- {vid} | {metas[vid]['title']}\n{texts[vid]}")
(ROOT / "batch_meta.json").write_text(
    json.dumps({v: metas[v] for v in ok}, ensure_ascii=False, indent=2), encoding="utf-8")
