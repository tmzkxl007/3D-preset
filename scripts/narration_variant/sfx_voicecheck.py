# -*- coding: utf-8 -*-
import os, sys, time, json, glob, subprocess, urllib.request
from pathlib import Path
SFX = Path.home()/"3D-preset"/"assets"/"sfx"
files = sorted(glob.glob(str(SFX/"*"/"*.wav")))
GAP = 1.0
subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i","anullsrc=r=44100:cl=stereo","-t",str(GAP),
                "_gap.wav"],capture_output=True)
lines=[]; index=[]; t=0.0
for f in files:
    d=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of",
        "default=noprint_wrappers=1:nokey=1",f],capture_output=True,text=True).stdout.strip())
    index.append((t, t+d, os.path.relpath(f,SFX).replace("\\","/")))
    lines.append(f"file '{f}'"); lines.append("file '_gap.wav'")
    t += d + GAP
open("_lib.txt","w",encoding="utf-8").write("\n".join(l.replace("'","'\''") if False else l for l in lines))
subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i","_lib.txt",
                "-ac","1","-ar","16000","_lib.wav"],capture_output=True)
json.dump(index, open("_lib_index.json","w",encoding="utf-8"), ensure_ascii=False)
print("library concat:", round(t,1),"s /", len(files),"clips")
