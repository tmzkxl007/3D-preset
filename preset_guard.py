# -*- coding: utf-8 -*-
"""납품 전 규격 검증 — 완성본이 이 저장소의 규격에 맞는지 확인한다.

    python preset_guard.py "<완성본.mp4>"

같은 폴더의 preset json 을 읽어 해상도 · fps · 길이 · 라우드니스 · 납품 경로를 대조한다.
하나라도 어긋나면 종료코드 1 로 끝난다 — 그 상태로 납품하지 않는다.

이 저장소의 규격에 맞지 않는 영상이 걸리는 가장 흔한 이유는 **다른 채널 프리셋으로 만든 영상을
여기 가져온 것**이다. 그럴 땐 그 프리셋 저장소의 preset_guard.py 로 검증해야 한다.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_spec():
    cands = sorted(HERE.glob("*.preset.json"))
    if not cands:
        sys.exit(f"규격 파일(*.preset.json)이 {HERE} 에 없습니다.")
    return json.loads(cands[0].read_text(encoding="utf-8")), cands[0].name


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,avg_frame_rate,codec_name",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffprobe 실패: {r.stderr.strip()[:300]}")
    d = json.loads(r.stdout)
    st = (d.get("streams") or [{}])[0]
    num, _, den = (st.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den) if float(den or 0) else 0.0
    return dict(width=st.get("width"), height=st.get("height"), fps=fps,
                vcodec=st.get("codec_name"),
                duration=float(d.get("format", {}).get("duration", 0)))


def loudness(path):
    r = subprocess.run(["ffmpeg", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for i, line in enumerate(r.stderr.splitlines()):
        if "Integrated loudness" in line:
            for nxt in r.stderr.splitlines()[i + 1:i + 3]:
                if "I:" in nxt:
                    try:
                        return float(nxt.split("I:")[1].split("LUFS")[0].strip())
                    except (IndexError, ValueError):
                        return None
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit(f"사용법: python {Path(__file__).name} \"<완성본.mp4>\"")
    video = Path(sys.argv[1])
    if not video.exists():
        sys.exit(f"파일이 없습니다: {video}")

    spec, spec_name = load_spec()
    out = spec["output"]
    name = spec.get("name", spec.get("id", "?"))
    print(f"[{name}] 규격: {spec_name}\n검사 대상: {video}\n")

    fails, warns = [], []

    p = probe(video)
    if (p["width"], p["height"]) != (out["width"], out["height"]):
        fails.append(f"해상도 {p['width']}x{p['height']} — 규격은 {out['width']}x{out['height']} "
                     f"({'가로' if out['width'] > out['height'] else '세로'})")
    else:
        print(f"  OK  해상도 {p['width']}x{p['height']}")

    if abs(p["fps"] - out["fps"]) > 0.5:
        fails.append(f"fps {p['fps']:.2f} — 규격은 {out['fps']}")
    else:
        print(f"  OK  fps {p['fps']:.2f}")

    lo, hi = out["target_seconds"]["min"], out["target_seconds"]["max"]
    if not (lo <= p["duration"] <= hi):
        fails.append(f"길이 {p['duration']:.1f}초 — 규격은 {lo}~{hi}초")
    else:
        sweet = out["target_seconds"].get("sweet_spot")
        print(f"  OK  길이 {p['duration']:.1f}초 (범위 {lo}~{hi}, 목표 {sweet})")
        if sweet and p["duration"] < sweet * 0.85:
            warns.append(f"길이 {p['duration']:.1f}초는 목표 {sweet}초보다 많이 짧습니다")

    target = out["loudness_lufs"]
    tol = out.get("loudness_tolerance_lufs", 1.5)
    lufs = loudness(video)
    if lufs is None:
        warns.append("라우드니스를 측정하지 못했습니다")
    elif abs(lufs - target) > tol:
        fails.append(f"라우드니스 {lufs:.1f} LUFS — 규격은 {target} ±{tol}")
    else:
        print(f"  OK  라우드니스 {lufs:.1f} LUFS")

    root = spec.get("delivery", {}).get("root", "")
    leaf = root.replace("\\", "/").rstrip("/").split("/")[-1] if root else ""
    if leaf and leaf not in str(video).replace("\\", "/"):
        warns.append(f"납품 폴더 밖입니다 — 완성본은 '{root}' 아래로 보냅니다 (지금: {video.parent})")
    elif leaf:
        print(f"  OK  납품 경로 ({leaf})")

    print()
    for w in warns:
        print(f"  경고  {w}")
    if fails:
        print()
        for f in fails:
            print(f"  실패  {f}")
        print(f"\n=> {len(fails)}건 불합격. 이 상태로 납품하지 마세요.")
        print("   다른 채널 프리셋으로 만든 영상이라면 그 저장소의 preset_guard.py 로 검증하세요.")
        return 1
    print("=> 합격.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
