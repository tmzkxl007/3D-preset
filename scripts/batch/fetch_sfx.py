# -*- coding: utf-8 -*-
"""CC0 효과음을 archive.org 에서 받아 sfxlib/ 에 채운다.

Red Library(USC Cinema / Sunset Editorial 아카이브, archive.org)는 CC0 1.0 이다 --
퍼블릭 도메인이라 출처 표기 의무가 없고 상업적 사용도 자유롭다. 73개 컬렉션이 있고
파일명이 구체적이라("R23-25-Water Splash") 장면에 맞는 소리를 골라내기 쉽다.

음원 파일은 저장소에 넣지 않는다(11MB). 필요할 때 이 스크립트로 다시 받는다.

    python fetch_sfx.py            # 목록 전체
    python fetch_sfx.py splash     # 이름에 splash 가 든 것만

새 소리가 필요하면 아래 표에 (컬렉션 id, 파일 이름, 쓸 이름) 을 추가한다.
컬렉션 목록은 archive.org 에서 title:"Red Library" 로 검색하면 나온다.
"""
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import os
OUT = Path(os.environ.get("VOLCANO_WORKDIR") or (Path.home() / "3d_works")) / "sfxlib"

CATALOG = [
    # 물 · 얼음
    ("Red_Library_Water_2", "R23-45-Jumping Into Water",          "splash_jump"),
    ("Red_Library_Water_2", "R27-12-Heavy Splashing in Water",    "splash_heavy"),
    ("Red_Library_Water_2", "R23-30-Water Bubbling",              "bubbling"),
    ("Red_Library_Water_1", "R13-57-Heavy Water Gurgles",         "gurgle"),
    ("Red_Library_Water_1", "R23-05-Water Running Underwater",    "underwater"),
    # 차량 · 충돌
    ("Red_Library_Cars_1",  "R03-36-Old Auto Tire Skids",         "skid_tires"),
    ("Red_Library_Cars_1",  "R03-19-Old Auto Tire Skid",          "skid_single"),
    ("Red_Library_Crashes", "R29-28-Large Metal Vehicle Crashes", "crash_metal"),
    # 몸싸움
    ("Red_Library_Fights",  "R15-03-Boxing Punches",              "punches"),
    ("Red_Library_Fights",  "R09-76-Two Falls on Wooden Floor",   "fall_wood"),
    ("Red_Library_Fights",  "R19-01-Fight Scuffle",               "scuffle"),
    ("Red_Library_Fights",  "R19-03-Movement for Fist Fight",     "fight_move"),
    # 사물 · 기계
    ("Red_Library_Doors",       "R09-01-Metal Door Slam",          "door_metal"),
    ("Red_Library_Foley_Props_1", "R12-47-Hit or Hammer Wood",     "gavel"),
    ("Red_Library_Foley_Props_1", "R15-80-Wooden Sticks",          "wood_sticks"),
    ("Red_Library_Metal",       "R16-36-Screwdriver on Metal",     "screwdriver"),
    ("Red_Library_Metal",       "R16-29-Squeaky Wheel",            "squeaky_wheel"),
    ("Red_Library_Machines_1",  "R12-51-Steady Motor Running",     "motor_steady"),
    # 군중 · 자연 · 탈것
    ("Red_Library_Crowds_Applause", "R02-08-Applause and Cheering", "cheer"),
    ("Red_Library_Crowds_Applause", "R02-05-Large Crowd Applauding","applause"),
    ("Red_Library_Nature_Wind",     "R22-11-Blustery Wind Loop",    "wind_blustery"),
    ("Red_Library_Nature_Wind",     "R22-15-Noisy Dull Wind",       "wind_dull"),
    ("Red_Library_Aircraft_Jets",   "R02-38-Astrojet Taxi",         "jet_taxi"),
    ("Red_Library_Boats",           "R05-45-Medium Boat Motor",     "boat_motor"),
]


def get(item):
    ident, name, slug = item
    dst = OUT / f"{slug}.mp3"
    if dst.exists():
        return f"  있음 {slug}"
    url = f"https://archive.org/download/{ident}/" + urllib.parse.quote(name + ".mp3")
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "3d-preset/1.0"})
        d = urllib.request.urlopen(r, timeout=180).read()
        dst.write_bytes(d)
        return f"  받음 {slug:15s} {len(d)//1024:>5}KB  <- {name}"
    except Exception as e:
        return f"  실패 {slug:15s} {e}"


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    want = CATALOG
    if len(sys.argv) > 1:
        key = sys.argv[1].lower()
        want = [c for c in CATALOG if key in c[2].lower() or key in c[1].lower()]
    print(f"CC0 효과음 {len(want)}개 (Red Library, archive.org)")
    with ThreadPoolExecutor(max_workers=4) as ex:
        for line in ex.map(get, want):
            print(line)
