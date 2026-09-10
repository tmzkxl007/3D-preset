# -*- coding: utf-8 -*-
"""완성본 오디오를 ASR로 다시 읽어 대본에 없는 말이 섞이지 않았는지 확인한다."""
import json
import os, re, subprocess, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works"))
CFG = json.loads((ROOT/"scripts_batch.json").read_text(encoding="utf-8"))
import sys
TARGETS = sys.argv[1:] or list(CFG)
KEY = open(os.path.expanduser("~/.volcano/keys/speechmatics"), encoding="utf-8").read().strip()
BASE = "https://asr.api.speechmatics.com/v2"

def norm(s):
    return re.sub(r"[^가-힣0-9]", "", s)

def one(vid):
    c = CFG[vid]
    mp4 = ROOT/vid/f"두둥픽_{c['slug']}.mp4"
    wav = ROOT/vid/"final_audio.wav"
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(mp4),"-vn","-ac","1","-ar","16000",str(wav)],
                   capture_output=True)
    b = f"----f{vid}"
    cfg = {"type":"transcription","transcription_config":{"language":"ko","operating_point":"enhanced"}}
    parts=[f"--{b}\r\n".encode(), b'Content-Disposition: form-data; name="config"\r\n\r\n',
           json.dumps(cfg).encode(), b"\r\n", f"--{b}\r\n".encode(),
           b'Content-Disposition: form-data; name="data_file"; filename="a.wav"\r\n',
           b"Content-Type: audio/wav\r\n\r\n", wav.read_bytes(), b"\r\n", f"--{b}--\r\n".encode()]
    req=urllib.request.Request(BASE+"/jobs",data=b"".join(parts),method="POST")
    req.add_header("Authorization",f"Bearer {KEY}")
    req.add_header("Content-Type",f"multipart/form-data; boundary={b}")
    job=json.loads(urllib.request.urlopen(req).read())["id"]
    for _ in range(200):
        q=urllib.request.Request(f"{BASE}/jobs/{job}"); q.add_header("Authorization",f"Bearer {KEY}")
        st=json.loads(urllib.request.urlopen(q).read())["job"]["status"]
        if st=="done": break
        if st=="rejected": return vid,"REJECTED",None
        time.sleep(3)
    q=urllib.request.Request(f"{BASE}/jobs/{job}/transcript?format=txt")
    q.add_header("Authorization",f"Bearer {KEY}")
    heard = q and urllib.request.urlopen(q).read().decode("utf-8").strip()
    (ROOT/vid/"final_transcript.txt").write_text(heard, encoding="utf-8")
    # 띄어쓰기는 ASR 마음대로다 -- 공백을 지운 글자열로 비교한다
    import difflib
    a, b2 = norm(" ".join(c["lines"])), norm(heard)
    ratio = difflib.SequenceMatcher(None, a, b2).ratio()
    sm = difflib.SequenceMatcher(None, a, b2)
    foreign = "".join(b2[j1:j2] for tag, _, _, j1, j2 in sm.get_opcodes()
                      if tag in ("insert", "replace"))
    return vid, ratio, foreign

with ThreadPoolExecutor(max_workers=5) as ex:
    for vid, ratio, foreign in ex.map(one, TARGETS):
        s = CFG[vid]["slug"]
        verdict = "외부 음성 없음" if ratio >= 0.95 else ("확인 필요" if ratio >= 0.85 else "!! 이상")
        print(f"  {s:6s} 대본 일치율 {ratio*100:.1f}%  {verdict}"
              + (f"  대본에 없던 글자: {foreign[:40]}" if foreign else ""))
