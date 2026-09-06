# -*- coding: utf-8 -*-
import json
words = json.load(open("source_words.json", encoding="utf-8"))
targets = ["walked","table","woman","pardon","join","insane","restaurant","silent","heads",
           "morals","muttered","embarrassed","man","quietly","away","minutes","smile",
           "psychology","observe","embarrassed","raised","20","dollars","expensive","madam",
           "exploded","laughter","froze","face","leaned","whispered","law","tables","lesson"]
for i, w in enumerate(words):
    key = w["word"].lower().strip(".,!?'$")
    if key in targets:
        ctx = " ".join(x["word"] for x in words[max(0,i-3):i+4])
        print(f"{w['start']:.1f}-{w['end']:.1f}  [{w['word']}]  ...{ctx}...")
