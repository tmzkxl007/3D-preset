# -*- coding: utf-8 -*-
import subprocess, json, os, glob
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "assets"
SFX = ASSETS / "sfx"
DRUM = str(ASSETS / "두둥_북소리.mp3")
TTS_DIR = "tts"
PAD = 0.15

durs = json.load(open("tts_durations.json"))
N = len(durs)
sent = [d + PAD for d in durs]
cuts = []
t = 0.0
for d in sent:
    t += d
    cuts.append(round(t, 3))
TOTAL = cuts[-1]
print("cuts:", cuts, "\ntotal:", TOTAL)

# ---------- 1. narration ----------
subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
                "-t",str(PAD),"silence.mp3"],capture_output=True)
with open("narration_concat.txt","w",encoding="utf-8") as f:
    for i in range(1, N+1):
        f.write(f"file '{TTS_DIR}/line{i:02d}_fast.mp3'\n")
        f.write("file 'silence.mp3'\n")
r = subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i","narration_concat.txt",
                    "-c:a","libmp3lame","-q:a","2","narration.mp3"],capture_output=True,text=True,
                   encoding="utf-8",errors="replace")
if r.returncode: raise SystemExit(r.stderr[-1500:])

# ---------- 2. pick sfx & find each clip's peak ----------
def pick(cls):
    fs = sorted(glob.glob(str(SFX/cls/"*.wav")))
    if not fs: raise SystemExit("no sfx in "+cls)
    return fs

def peak_time(path):
    o = subprocess.run(["ffmpeg","-v","error","-i",path,"-ac","1","-ar","44100","-f","f32le","-"],
                       capture_output=True)
    x = np.frombuffer(o.stdout, dtype=np.float32)
    if len(x)==0: return 0.0, 0.0
    env = np.convolve(np.abs(x), np.ones(2205)/2205, mode="same")
    return float(np.argmax(env))/44100.0, len(x)/44100.0

risers   = pick("riser")
rimp     = pick("riser_impact")
rrum     = pick("riser_rumble")
impacts  = pick("impact")
rumbles  = pick("rumble")
hits     = pick("hit")

# big story beats get riser+impact; the rest a plain riser
BIG = {2, 6, 8, 11}          # legs lost / lever pulling starts / tracks switched / final reveal
RUMBLE_AT = {3, 9}           # entering the crisis, and just before the payoff

events = []   # (path, target_time, gain, align_peak)
for i, c in enumerate(cuts[:-1], start=1):     # no cut after the last sentence
    if i in BIG:
        p = rimp[(i//2) % len(rimp)];  g = 0.60
    elif i in RUMBLE_AT:
        p = rrum[(i//3) % len(rrum)];    g = 0.45
    else:
        p = risers[(i*5) % len(risers)]; g = 0.45
    events.append((p, c, g, True))

# sustained low rumble under the crisis and under the reveal
events.append((rumbles[0], cuts[2] + 0.9, 0.34, False))
events.append((rumbles[2], cuts[8] + 0.9, 0.34, False))

# extra mid-sentence hits to keep the reference's ~2s density
for k, idx in enumerate([4, 6, 7, 9, 11, 12]):
    mid = (cuts[idx-2] if idx >= 2 else 0.0) + sent[idx-1] * 0.55
    events.append((hits[k % len(hits)], round(mid,3), 0.38, True))

# ---------- 3. mix ----------
inputs = ["-i","narration.mp3","-i",DRUM]
parts  = ["[0:a]volume=1.0,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0]",
          "[1:a]volume=8dB,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a1]"]
labels = ["[a0]","[a1]"]
plan = []
for n,(p,tgt,g,align) in enumerate(sorted(events,key=lambda e:e[1]), start=2):
    pk,dur = peak_time(p)
    start = max(0.0, tgt - pk) if align else max(0.0, tgt)
    if start >= TOTAL: continue
    ms = int(round(start*1000))
    inputs += ["-i",p]
    parts.append(f"[{n}:a]volume={g},aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                 f"adelay={ms}|{ms}[a{n}]")
    labels.append(f"[a{n}]")
    plan.append((os.path.relpath(p,SFX).replace("\\","/"), round(start,2), round(tgt,2), g))

parts.append("".join(labels)+f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0,"
             f"alimiter=limit=0.95,atrim=0:{TOTAL:.3f}[aout]")
cmd = ["ffmpeg","-y","-v","error"]+inputs+["-filter_complex",";".join(parts),
       "-map","[aout]","-c:a","aac","-b:a","192k","audio_mix.m4a"]
r = subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace")
if r.returncode: raise SystemExit(r.stderr[-3000:])

print(f"\nSFX events: {len(plan)}  (~{TOTAL/len(plan):.1f}s apart)")
for f,s,tg,g in plan: print(f"  {s:6.2f}s  peak@{tg:6.2f}s  gain{g}  {f}")
pr = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                     "-of","default=noprint_wrappers=1:nokey=1","audio_mix.m4a"],capture_output=True,text=True)
print("\naudio_mix.m4a:", pr.stdout.strip())
