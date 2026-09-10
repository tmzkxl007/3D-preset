# -*- coding: utf-8 -*-
"""참고 영상에서 실측한 스펙트럼 특성대로 효과음을 직접 합성한다.
riser  : 중심주파수 600Hz -> 5~7kHz 상승, 진폭 상승
impact : 25~120Hz가 에너지의 45~58%, 빠른 감쇠
rumble : 저역 지속 드론(1.3초)
"""
import numpy as np, subprocess, os, shutil
from pathlib import Path
SR = 44100


def stft_shape(dur, fc_fn, bw_fn, amp_fn, nfft=1024, hop=128, seed=None):
    """백색잡음을 프레임마다 가우시안 대역으로 깎아 시간가변 필터를 만든다."""
    r = np.random.default_rng(20260910 + (seed or 0))
    n = int(dur*SR)
    x = r.standard_normal(n + nfft)
    f = np.fft.rfftfreq(nfft, 1/SR)
    win = np.hanning(nfft)
    out = np.zeros(n + nfft*2)
    norm = np.zeros_like(out)
    for i in range(0, n, hop):
        p = min(1.0, i/max(1,n))
        seg = x[i:i+nfft]
        if len(seg) < nfft: break
        S = np.fft.rfft(seg*win)
        fc, bw = fc_fn(p), bw_fn(p)
        S *= np.exp(-0.5*((f-fc)/bw)**2) * amp_fn(p)
        S *= (f >= 25.0)   # DC/초저역 제거 -- 안 하면 들리지도 않는 성분이 에너지를 먹는다
        out[i:i+nfft]  += np.fft.irfft(S)*win
        norm[i:i+nfft] += win**2
    y = out[:n] / np.maximum(norm[:n], 1e-6)
    return y

def env_fade(y, fin=0.01, fout=0.03):
    n=len(y); a=int(fin*SR); b=int(fout*SR)
    if a: y[:a] *= np.linspace(0,1,a)
    if b: y[-b:] *= np.linspace(1,0,b)
    return y

def riser(dur=0.62, f0=600, f1=7600, seed=0):
    y = stft_shape(dur,
        fc_fn=lambda p: f0*(f1/f0)**(p**1.15),
        bw_fn=lambda p: max(300, (f0*(f1/f0)**(p**1.15))*0.85),
        amp_fn=lambda p: (p**2.0)*0.9 + 0.05, seed=seed)
    air = stft_shape(dur, lambda p:9000, lambda p:3500,
                     lambda p:(p**3.0)*0.55, seed=seed+41)
    y = y/np.max(np.abs(y)+1e-9) + 0.35*air/np.max(np.abs(air)+1e-9)
    t = np.arange(len(y))/SR
    # 얇은 톤 스윕을 겹쳐 방향감을 준다
    fsw = 300*(2400/300)**((t/dur)**1.15)
    tone = np.sin(2*np.pi*np.cumsum(fsw)/SR) * ((t/dur)**2.4) * 0.22
    y = y/np.max(np.abs(y)+1e-9) + tone
    y[-int(0.05*SR):] *= np.linspace(1, 0.25, int(0.05*SR))   # 정점 직후 급감
    return env_fade(y, 0.02, 0.02)

def impact(dur=0.55, f_start=95, f_end=36, seed=0):
    t = np.arange(int(dur*SR))/SR
    f = f_end + (f_start-f_end)*np.exp(-t/0.055)
    sub  = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t/0.17)
    body = stft_shape(dur, lambda p:190, lambda p:150,
                      lambda p: np.exp(-p*dur/0.045), seed=seed+7)
    body = body/np.max(np.abs(body)+1e-9)
    click = np.zeros_like(t); k=int(0.004*SR)
    click[:k] = np.random.default_rng(seed+3).standard_normal(k)*np.linspace(1,0,k)
    # 참고 실측은 저역이 45~58%다 -- 순수 서브가 아니라 중고역 몸통이 함께 있다
    air = stft_shape(dur, lambda p:1500+2500*p, lambda p:1400,
                     lambda p: np.exp(-p*dur/0.10), seed=seed+23)
    air = air/np.max(np.abs(air)+1e-9)
    y = 0.85*sub + 0.85*body + 0.35*click + 0.75*air
    return env_fade(np.tanh(y*1.35), 0.001, 0.05)

def rumble(dur=1.35, seed=0):
    y = stft_shape(dur, lambda p:58, lambda p:44,
                   lambda p: 0.75+0.25*np.sin(2*np.pi*1.4*p*dur), seed=seed)
    y = y/np.max(np.abs(y)+1e-9)
    tex = stft_shape(dur, lambda p:700+300*np.sin(2*np.pi*0.7*p*dur), lambda p:600,
                     lambda p: 0.6+0.4*np.sin(2*np.pi*1.1*p*dur+1.0), seed=seed+31)
    y = y + 0.16*tex/np.max(np.abs(tex)+1e-9)
    return env_fade(y, 0.22, 0.45)

def hit(dur=0.30, f=175, seed=0):
    t = np.arange(int(dur*SR))/SR
    tone = np.sin(2*np.pi*f*t)*np.exp(-t/0.075)
    nz = stft_shape(dur, lambda p:420, lambda p:320,
                    lambda p: np.exp(-p*dur/0.05), seed=seed+11)
    nz = nz/np.max(np.abs(nz)+1e-9)
    bright = stft_shape(dur, lambda p:3800, lambda p:2600,
                        lambda p: np.exp(-p*dur/0.035), seed=seed+17)
    bright = bright/np.max(np.abs(bright)+1e-9)
    return env_fade(np.tanh((tone*0.9 + nz*0.5 + bright*0.95)*1.3), 0.001, 0.06)

def riser_impact(seed=0):
    r = riser(0.58, f1=7600, seed=seed); im = impact(0.55, seed=seed)
    y = np.zeros(len(r)+len(im)-int(0.05*SR))
    y[:len(r)] += r*0.85
    off = len(r)-int(0.05*SR)
    y[off:off+len(im)] += im
    return env_fade(y/np.max(np.abs(y)+1e-9), 0.02, 0.05)

def riser_rumble(seed=0):
    r = riser(0.55, f1=6400, seed=seed); ru = rumble(1.15, seed=seed)
    y = np.zeros(len(r)+len(ru)-int(0.18*SR))
    y[:len(r)] += r*0.8
    off = len(r)-int(0.18*SR)
    y[off:off+len(ru)] += ru*0.9
    return env_fade(y/np.max(np.abs(y)+1e-9), 0.02, 0.4)

OUT = Path("synth_out"); shutil.rmtree(OUT, ignore_errors=True)
SPECS = {
 "riser":        [("riser_%02d", lambda i: riser(0.50+0.05*(i%4), 560+70*(i%3), 6900+520*(i%4), seed=i))     for _ in [0]],
 "impact":       [("impact_%02d", lambda i: impact(0.50+0.05*(i%3), 88+9*(i%3), 34+3*(i%2), seed=i))         for _ in [0]],
 "rumble":       [("rumble_%02d", lambda i: rumble(1.20+0.12*(i%3), seed=i))                                  for _ in [0]],
 "hit":          [("hit_%02d",    lambda i: hit(0.26+0.04*(i%3), 155+22*(i%4), seed=i))                       for _ in [0]],
 "riser_impact": [("riser_impact_%02d", lambda i: riser_impact(seed=i))                                       for _ in [0]],
 "riser_rumble": [("riser_rumble_%02d", lambda i: riser_rumble(seed=i))                                       for _ in [0]],
}
COUNT = {"riser":8,"impact":5,"rumble":3,"hit":6,"riser_impact":5,"riser_rumble":3}
made=[]
for cls,(fmt,fn) in ((k,v[0]) for k,v in SPECS.items()):
    (OUT/cls).mkdir(parents=True, exist_ok=True)
    for i in range(1, COUNT[cls]+1):
        y = fn(i).astype(np.float32)
        y = y/np.max(np.abs(y)+1e-9)*0.95
        raw = OUT/cls/((fmt % i)+"_raw.f32")
        y.astype("<f4").tofile(raw)
        dst = OUT/cls/((fmt % i)+".wav")
        subprocess.run(["ffmpeg","-y","-v","error","-f","f32le","-ar",str(SR),"-ac","1","-i",str(raw),
                        "-af","aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar","44100","-ac","2","-c:a","pcm_s16le",str(dst)],check=True)
        raw.unlink()
        made.append(str(dst))
print("synthesized:", len(made))
