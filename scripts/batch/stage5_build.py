# -*- coding: utf-8 -*-
"""5단계 — 자막 · 세그먼트 · 오디오 · 렌더를 영상별로 만든다.

    python build_all.py [영상id ...]

자막 조각은 ASR 단어 타임스탬프에서 간격이 가장 크게 벌어지는 지점으로 자른다 —
어절 수로 기계적으로 나누는 것보다 3D.md 5번의 "숨 쉬는 지점"에 가깝다.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import ImageFont

ROOT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works"))
REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "assets"
FONTS = ASSETS / "fonts"
FONT = str(FONTS / "NanumSquareRoundB.ttf")
TITLE_FONT = str(FONTS / "Recipekorea 레코체 FONT.ttf")
LOGO = str(ASSETS / "두둥픽_로고_템플릿.png")
DRUM = str(ASSETS / "두둥_북소리.mp3")

PAD = 0.0        # 문장 사이 공백 없음(사용자 요청 2026-09-10)
OPEN_LEAD = 0.55 # 두둥이 때린 뒤 첫 문장이 시작한다 -- 겹치면 말이 묻힌다
TAIL = 0.3       # 마지막 말이 끝난 뒤 남기는 여운. 0 이면 뚝 끊긴다(사용자 요청 2026-09-15)
SRC_SFX_DB = 0.0 # 원본에서 나레이션을 뺀 효과음 트랙의 게인. srcsfx.wav 가 있을 때만 쓴다
WIN_Y, WIN_H = 488, 1010
CAP_CENTER_Y = 1065
REF = 100

CFG = json.loads((ROOT / "scripts_batch.json").read_text(encoding="utf-8"))
SEG = json.loads((ROOT / "segments_batch.json").read_text(encoding="utf-8"))
TARGETS = sys.argv[1:] or list(CFG)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def fit(text, font_path=FONT, width=1000, lo=44, hi=84):
    f = ImageFont.truetype(font_path, REF)
    bb = f.getbbox(text)
    w = bb[2] - bb[0]
    return max(lo, min(hi, int(width / max(w, 1) * REF)))


def ts(t):
    return f"{int(t//3600):d}:{int((t%3600)//60):02d}:{t%60:05.2f}"


def split_fragments(sentence, words):
    """숨 쉬는 지점(단어 사이 간격이 큰 곳)에서 자른다. 정렬이 안 맞으면 어절 균등 분할."""
    eojeol = sentence.rstrip(".").split()
    n = len(eojeol)
    k = 2 if n <= 5 else 3
    if k >= n:
        return [" ".join(eojeol)]
    if len(words) == n:
        gaps = [(words[i + 1]["start"] - words[i]["end"], i + 1) for i in range(n - 1)]
        cuts = []
        for _, idx in sorted(gaps, reverse=True):
            if all(abs(idx - c) >= 2 for c in cuts) and idx >= 2 and n - idx >= 2:
                cuts.append(idx)
            if len(cuts) == k - 1:
                break
        cuts.sort()
    else:
        cuts = [round(n * j / k) for j in range(1, k)]
    bounds = [0] + cuts + [n]
    return [" ".join(eojeol[a:b]) for a, b in zip(bounds, bounds[1:]) if b > a]


def build_ass(vid, c, durs, align):
    sent = [d + PAD for d in durs]
    frags = [split_fragments(line, align.get(str(i + 1), []))
             for i, line in enumerate(c["lines"])]

    t_lines = c["title"]
    base = min(fit(t_lines[0], TITLE_FONT, 1060, 50, 130),
               fit(t_lines[1], TITLE_FONT, 1060, 50, 130))
    s1, s2 = int(base / 1.13), base
    warn = f"  !! 제목 {base}px < 75px — 제목이 깁니다" if base < 75 else ""

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,NanumSquareRound,58,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,4,5,70,70,0,1
Style: Title,Recipekorea Medium,80,&H00000000,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,50,50,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    out, t, ncap = [header], OPEN_LEAD, 0
    for i, (dur, fg) in enumerate(zip(sent, frags)):
        w = align.get(str(i + 1), [])
        counts = [len(f.split()) for f in fg]
        times = []
        if len(w) == sum(counts):
            cum = 0
            for cnt in counts:
                times.append([t + w[cum]["start"], t + w[cum + cnt - 1]["end"]])
                cum += cnt
        else:
            chars = [len(f.replace(" ", "")) for f in fg]
            tt = t
            for f, ch in zip(fg, chars):
                d = dur * ch / sum(chars)
                times.append([tt, tt + d])
                tt += d
        times[-1][1] = t + dur
        for f, (a, b) in zip(fg, times):
            out.append(f"Dialogue: 1,{ts(a)},{ts(b)},Caption,,0,0,0,,"
                       f"{{\\an5\\pos(540,{CAP_CENTER_Y})\\fs{fit(f)}}}{f}\n")
            ncap += 1
        t += dur
    title = f"{{\\fs{s1}}}{t_lines[0]}\\N{{\\fs{s2}}}{t_lines[1]}"
    # 제목은 여운 구간까지 띄워 둔다 -- 끝에서 제목만 먼저 사라지면 어색하다
    out.append(f"Dialogue: 2,{ts(0)},{ts(t + TAIL)},Title,,0,0,0,,{title}\n")
    (ROOT / vid / "captions.ass").write_text("".join(out), encoding="utf-8-sig")
    return t + TAIL, ncap, (s1, s2), warn


def build_segments(vid, c, durs, crop_y):
    crops = c.get("crop_y") or [crop_y] * len(durs)   # 컷마다 다르게 줄 수 있다
    d = ROOT / vid
    (d / "final_segs").mkdir(exist_ok=True)
    tgt = [x + PAD for x in durs]
    names = []
    for i, ((a, b), t) in enumerate(zip(SEG[vid], tgt), 1):
        sp = (b - a) / t
        out = d / "final_segs" / f"f{i:02d}.mp4"
        vf = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
              "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
              f"crop=1080:{WIN_H}:0:{crops[i-1]},setpts=(1/{sp:.6f})*PTS,fps=30")
        r = run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                 "-i", str(d / "source.mp4"), "-an", "-vf", vf, "-c:v", "libx264",
                 "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
        if r.returncode:
            raise SystemExit(f"{vid} seg{i}: {r.stderr[-400:]}")
        names.append(out.name)
    (d / "final_segs" / "concat_list.txt").write_text(
        "".join(f"file '{n}'\n" for n in names), encoding="utf-8")
    r = run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", "concat_list.txt", "-c:v", "libx264", "-preset", "fast",
             "-crf", "18", "-pix_fmt", "yuv420p", "concat.mp4"], cwd=str(d / "final_segs"))
    if r.returncode:
        raise SystemExit(r.stderr[-600:])


NL = chr(10)


def build_audio(vid, durs):
    """나레이션 + 오프닝 두둥 드럼. 그 밖의 효과음은 넣지 않는다."""
    d = ROOT / vid
    n = len(durs)
    total = OPEN_LEAD + sum(durs) + TAIL

    (d / "narration_concat.txt").write_text(
        NL.join(f"file 'tts/line{i:02d}_fast.mp3'" for i in range(1, n + 1)) + NL,
        encoding="utf-8")
    r = run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", "narration_concat.txt", "-c:a", "libmp3lame", "-q:a", "2",
             "narration.mp3"], cwd=str(d))
    if r.returncode:
        raise SystemExit(r.stderr[-600:])

    # 오프닝 두둥 드럼만 남긴다. 그 밖의 효과음은 넣지 않는다(사용자 요청 2026-09-10).
    ms = int(round(OPEN_LEAD * 1000))
    fc = ("[0:a]volume=1.0,aformat=sample_fmts=fltp:sample_rates=44100:"
          f"channel_layouts=stereo,adelay={ms}|{ms}[a0];"
          "[1:a]volume=8dB,aformat=sample_fmts=fltp:sample_rates=44100:"
          f"channel_layouts=stereo,afade=t=out:st={OPEN_LEAD + 0.05:.2f}:d=0.6[a1];"
          "[a0][a1]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
          f"alimiter=limit=0.95,apad,atrim=0:{total:.3f}[aout]")
    # 원본에서 나레이션을 뺀 효과음 트랙이 있으면 아래에 깐다(build_srcsfx.py 가 만든다)
    srcsfx = d / "srcsfx.wav"
    ins = ["-i", str(d / "narration.mp3"), "-i", DRUM]
    if srcsfx.exists():
        ins += ["-i", str(srcsfx)]
        fc = fc.replace("[a0][a1]amix=inputs=2",
                        f"[2:a]volume={SRC_SFX_DB}dB,aformat=sample_fmts=fltp:"
                        "sample_rates=44100:channel_layouts=stereo[a2];"
                        "[a0][a1][a2]amix=inputs=3")
    r = run(["ffmpeg", "-y", "-v", "error"] + ins +
            ["-filter_complex", fc, "-map", "[aout]",
             "-c:a", "aac", "-b:a", "192k", str(d / "audio_mix.m4a")])
    if r.returncode:
        raise SystemExit(r.stderr[-800:])
    return total, 1


def render(vid, c, total):
    d = ROOT / vid
    ass = str((d / "captions.ass").resolve()).replace("\\", "/").replace(":", "\\:")
    fdir = str(FONTS).replace("\\", "/").replace(":", "\\:")
    fc = (f"[0:v]tpad=start_mode=clone:start_duration={OPEN_LEAD}:"
          f"stop_mode=clone:stop_duration=2,"
          f"eq=gamma_r=1.05:gamma_b=0.95:saturation=1.08:contrast=1.03,"
          f"pad=1080:1920:0:{WIN_Y}:color=black[p];"
          f"[p][1:v]overlay=0:0:format=auto,ass='{ass}':fontsdir='{fdir}'[outv]")
    r = run(["ffmpeg", "-y", "-v", "error", "-i", str(d / "final_segs" / "concat.mp4"),
             "-loop", "1", "-i", LOGO, "-filter_complex", fc, "-map", "[outv]",
             "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", str(d / "video_only.mp4")])
    if r.returncode:
        raise SystemExit(f"{vid} render: {r.stderr[-800:]}")

    # 2패스 loudnorm — 1패스는 목표에 못 미친다(preset_guard 가 잡아낸 사고)
    m = run(["ffmpeg", "-i", str(d / "audio_mix.m4a"), "-af",
             "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"])
    import re
    j = json.loads(re.search(r"\{[^{}]*input_i[^{}]*\}", m.stderr, re.S).group(0))
    meas = (f"measured_I={j['input_i']}:measured_LRA={j['input_lra']}:"
            f"measured_TP={j['input_tp']}:measured_thresh={j['input_thresh']}:"
            f"offset={j['target_offset']}")
    out = d / f"두둥픽_{c['slug']}.mp4"
    r = run(["ffmpeg", "-y", "-v", "error", "-i", str(d / "video_only.mp4"),
             "-i", str(d / "audio_mix.m4a"), "-af",
             f"loudnorm=I=-14:TP=-1.0:LRA=11:{meas}:linear=true",
             # loudnorm 은 내부적으로 업샘플링한다 -- 48kHz 로 명시하지 않으면 96kHz 로 나간다
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-shortest", str(out)])
    if r.returncode:
        raise SystemExit(f"{vid} mux: {r.stderr[-800:]}")
    return out


def one(vid):
    c = CFG[vid]
    d = ROOT / vid
    durs = json.loads((d / "tts_durations.json").read_text(encoding="utf-8"))
    align = json.loads((d / "tts_word_align.json").read_text(encoding="utf-8"))
    total, ncap, tsize, warn = build_ass(vid, c, durs, align)
    build_segments(vid, c, durs, crop_y=300)
    atotal, nsfx = build_audio(vid, durs)
    out = render(vid, c, total)
    return (f"  {c['slug']:6s} {out.name}  {total:.1f}초  자막 {ncap}장  "
            f"제목 {tsize[0]}/{tsize[1]}px  효과음 {nsfx}개{warn}")


print(f"빌드 {len(TARGETS)}편...")
with ThreadPoolExecutor(max_workers=3) as ex:
    for line in ex.map(one, TARGETS):
        print(line)
print("DONE")
