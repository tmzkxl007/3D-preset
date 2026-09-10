# -*- coding: utf-8 -*-
import os, time, json, urllib.request
def get_key(env,f):
    v=os.environ.get(env)
    if v: return v.strip()
    return open(os.path.expanduser(f"~/.volcano/keys/{f}"),encoding="utf-8").read().strip()
key=get_key("SPEECHMATICS_API_KEY","speechmatics"); base="https://asr.api.speechmatics.com/v2"
b="----volcanoLib1"
cfg={"type":"transcription","transcription_config":{"language":"ko","operating_point":"enhanced"}}
p=[f"--{b}\r\n".encode(), b'Content-Disposition: form-data; name="config"\r\n\r\n',
   json.dumps(cfg).encode(), b"\r\n", f"--{b}\r\n".encode(),
   b'Content-Disposition: form-data; name="data_file"; filename="a.wav"\r\n',
   b"Content-Type: audio/wav\r\n\r\n", open("_lib.wav","rb").read(), b"\r\n", f"--{b}--\r\n".encode()]
req=urllib.request.Request(base+"/jobs",data=b"".join(p),method="POST")
req.add_header("Authorization",f"Bearer {key}")
req.add_header("Content-Type",f"multipart/form-data; boundary={b}")
jid=json.loads(urllib.request.urlopen(req).read())["id"]
for _ in range(200):
    r=urllib.request.Request(f"{base}/jobs/{jid}"); r.add_header("Authorization",f"Bearer {key}")
    st=json.loads(urllib.request.urlopen(r).read())["job"]["status"]
    if st=="done": break
    if st=="rejected": raise SystemExit("rejected")
    time.sleep(3)
r=urllib.request.Request(f"{base}/jobs/{jid}/transcript?format=json-v2"); r.add_header("Authorization",f"Bearer {key}")
data=json.loads(urllib.request.urlopen(r).read())
words=[{"w":i["alternatives"][0]["content"],"c":i["alternatives"][0].get("confidence",0),
        "s":i["start_time"],"e":i["end_time"]} for i in data.get("results",[]) if i.get("type")=="word"]
index=json.load(open("_lib_index.json",encoding="utf-8"))
bad={}
for w in words:
    for a,bb,name in index:
        if w["s"] < bb and w["e"] > a:
            bad.setdefault(name,[]).append((w["w"], round(w["c"],2)))
json.dump(bad, open("sfx_voice_flags.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"recognized words: {len(words)}   contaminated clips: {len(bad)}/{len(index)}")
for k,v in sorted(bad.items()): print(f"  {k}: {v}")
