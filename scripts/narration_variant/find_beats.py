# -*- coding: utf-8 -*-
import json
words = json.load(open("source_words.json", encoding="utf-8"))
targets = ["fishing","lamp","rubbed","genie","wish","condition","husband","froze","divorce",
           "gained","wife","struggled","fisher","gold","palace","pacing","frustrated","minutes",
           "waited","smile","blind","eye","stared","shook","granted","morning","village",
           "mourning","tripped","stairs","died","alone","crying","jealousy","lose","costs"]
for i, w in enumerate(words):
    key = w["word"].lower().strip(".,!?'")
    if key in targets:
        ctx = " ".join(x["word"] for x in words[max(0,i-3):i+4])
        print(f"{w['start']:.1f}-{w['end']:.1f}  [{w['word']}]  ...{ctx}...")
