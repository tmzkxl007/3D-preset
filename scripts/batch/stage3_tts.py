# -*- coding: utf-8 -*-
"""3단계 — 전 영상의 TTS 생성 + 단어 정렬을 동시에 돌린다.

대본이 바뀌면 mp3 캐시를 절대 재사용하지 않는다(3D.md 12번 항목의 사고).
매번 tts/ 를 비우고 새로 만든다.
"""
import json
import os
import shutil
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works"))
# 작업 폴더는 저장소 밖에 둔다. VOLCANO_WORKDIR 로 바꿀 수 있다.
CFG = json.loads((ROOT / "scripts_batch.json").read_text(encoding="utf-8"))
import sys
if len(sys.argv) > 1:
    CFG = {k: v for k, v in CFG.items() if k in sys.argv[1:]}


def key(env, fn):
    v = os.environ.get(env)
    return v.strip() if v else open(os.path.expanduser(f"~/.volcano/keys/{fn}"),
                                    encoding="utf-8").read().strip()


TC = key("TYPECAST_API_KEY", "typecast")
SM = key("SPEECHMATICS_API_KEY", "speechmatics")
VOICE = "tc_68257f68bc6e3c161ab5078d"      # Piljae
SMBASE = "https://asr.api.speechmatics.com/v2"


def tts_one(args):
    vid, i, text = args
    d = ROOT / vid / "tts"
    mp3, fast = d / f"line{i:02d}.mp3", d / f"line{i:02d}_fast.mp3"
    body = json.dumps({"voice_id": VOICE, "text": text, "model": "ssfm-v30",
                       "language": "kor", "prosody": {"emotion_preset": "normal"},
                       "output": {"audio_format": "mp3"}}).encode("utf-8")
    # Typecast 는 동시 요청을 제한한다(429). 백오프하며 재시도한다.
    for attempt in range(8):
        req = urllib.request.Request("https://api.typecast.ai/v1/text-to-speech",
                                     data=body, method="POST")
        req.add_header("X-API-KEY", TC)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                mp3.write_bytes(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 7:
                raise
            time.sleep(2 * (attempt + 1) + (i % 3))
    else:
        raise RuntimeError(f"{vid} line{i}: 429 재시도 초과")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-filter:a", "atempo=1.2",
                    "-c:a", "libmp3lame", "-q:a", "2", str(fast)], capture_output=True)
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", str(fast)],
                        capture_output=True, text=True)
    return vid, i, float(pr.stdout.strip())


def align_one(args):
    vid, i = args
    path = ROOT / vid / "tts" / f"line{i:02d}_fast.mp3"
    b = f"----a{vid}{i}"
    cfg = {"type": "transcription",
           "transcription_config": {"language": "ko", "operating_point": "enhanced"}}
    parts = [f"--{b}\r\n".encode(),
             b'Content-Disposition: form-data; name="config"\r\n\r\n',
             json.dumps(cfg).encode(), b"\r\n", f"--{b}\r\n".encode(),
             b'Content-Disposition: form-data; name="data_file"; filename="a.mp3"\r\n',
             b"Content-Type: audio/mpeg\r\n\r\n", path.read_bytes(), b"\r\n",
             f"--{b}--\r\n".encode()]
    req = urllib.request.Request(SMBASE + "/jobs", data=b"".join(parts), method="POST")
    req.add_header("Authorization", f"Bearer {SM}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={b}")
    job = json.loads(urllib.request.urlopen(req).read())["id"]
    for _ in range(200):
        q = urllib.request.Request(f"{SMBASE}/jobs/{job}")
        q.add_header("Authorization", f"Bearer {SM}")
        st = json.loads(urllib.request.urlopen(q).read())["job"]["status"]
        if st == "done":
            break
        if st == "rejected":
            return vid, i, []
        time.sleep(3)
    q = urllib.request.Request(f"{SMBASE}/jobs/{job}/transcript?format=json-v2")
    q.add_header("Authorization", f"Bearer {SM}")
    data = json.loads(urllib.request.urlopen(q).read())
    return vid, i, [{"word": x["alternatives"][0]["content"],
                     "start": x["start_time"], "end": x["end_time"]}
                    for x in data.get("results", []) if x.get("type") == "word"]


jobs = []
for vid, c in CFG.items():
    d = ROOT / vid / "tts"
    shutil.rmtree(d, ignore_errors=True)     # 캐시 재사용 금지
    d.mkdir(parents=True, exist_ok=True)
    jobs += [(vid, i, t) for i, t in enumerate(c["lines"], start=1)]

print(f"TTS {len(jobs)}문장 생성 중...")
durs = {v: {} for v in CFG}
with ThreadPoolExecutor(max_workers=2) as ex:
    for vid, i, dur in ex.map(tts_one, jobs):
        durs[vid][i] = dur

for vid, c in CFG.items():
    seq = [durs[vid][i] for i in range(1, len(c["lines"]) + 1)]
    (ROOT / vid / "tts_durations.json").write_text(json.dumps(seq), encoding="utf-8")
    total = sum(seq) + 0.15 * len(seq)
    print(f"  {vid} {c['slug']}: {len(seq)}문장 {total:.1f}초 (목표 {c['target_sec']})")

print("\n단어 정렬 중...")
al = {v: {} for v in CFG}
with ThreadPoolExecutor(max_workers=6) as ex:
    for vid, i, words in ex.map(align_one, [(v, i) for v, i, _ in jobs]):
        al[vid][str(i)] = words
for vid in CFG:
    (ROOT / vid / "tts_word_align.json").write_text(
        json.dumps(al[vid], ensure_ascii=False, indent=2), encoding="utf-8")
    bad = [i for i, w in al[vid].items() if not w]
    print(f"  {vid}: 정렬 완료" + (f" (실패 문장 {bad})" if bad else ""))
print("\nDONE")
