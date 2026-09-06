# -*- coding: utf-8 -*-
import json
from PIL import ImageFont

FONT_PATH = r"C:\Users\Administrator\AppData\Local\Microsoft\Windows\Fonts\NanumSquareRoundB.ttf"
TITLE_FONT_PATH = r"C:\Users\Administrator\OneDrive\바탕 화면\volcano-work\fonts_3d\Recipekorea 레코체 FONT.ttf"

FRAGMENTS = [
    ["한 여자가 놀이터에서", "아이를 지켜보다", "낯선 남자를 발견했습니다"],
    ["그 남자는 아이들 곁을", "계속 서성이고 있었죠"],
    ["옆에 있던 다른 엄마는", "그가 매일 그렇게", "아이들을 지켜본다고 귀띔했어요"],
    ["여자는 점점 더", "불안해졌습니다"],
    ["결국 신고할 준비까지", "마쳤죠"],
    ["그 순간 한 남자아이가", "놀이기구에서 미끄러졌습니다"],
    ["낯선 남자는 재빨리", "달려가 아이를 받아냈죠"],
    ["아이 아버지가 다가오자", "그는 조용히", "사정을 털어놨습니다"],
    ["삼 년 전 이 놀이기구에서", "아들을 잃었다고 했어요"],
    ["그날 이후 매일", "이곳에 나와", "아이들을 지켜봐 왔던 겁니다"],
    ["그 사실을 알게 된", "여자는 눈물을", "참지 못했습니다"],
    ["겉모습만으로 사람을", "판단해선 안 된다는 걸", "보여준 순간이었죠"],
]

with open("tts_durations.json", encoding="utf-8") as f:
    raw_durations = json.load(f)
with open("tts_word_align.json", encoding="utf-8") as f:
    word_align = json.load(f)

PAD = 0.15
sentence_durations = [d + PAD for d in raw_durations]
assert len(sentence_durations) == len(FRAGMENTS) == 12

TITLE_LINES = ["놀이터에 매일 나타난 남자", "그 이유가 밝혀졌다"]

TARGET_WIDTH = 1000
MAX_SIZE = 84
MIN_SIZE = 44
REF_SIZE = 100

def fit_size(text, font_path=FONT_PATH, target_width=TARGET_WIDTH, max_size=MAX_SIZE, min_size=MIN_SIZE):
    font = ImageFont.truetype(font_path, REF_SIZE)
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    size = int(target_width / w * REF_SIZE)
    return max(min_size, min(max_size, size))

def ts(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"

TITLE_TARGET_WIDTH = 1040
TITLE_MAX = 110
TITLE_MIN = 50

def fit_title_size(text):
    return fit_size(text, font_path=TITLE_FONT_PATH, target_width=TITLE_TARGET_WIDTH,
                     max_size=TITLE_MAX, min_size=TITLE_MIN)

base_size = min(fit_title_size(TITLE_LINES[0]), fit_title_size(TITLE_LINES[1]))
title_size1 = int(base_size / 1.13)
title_size2 = base_size

# caption vertical center = where the source's own leftover caption used to sit
CAP_CENTER_Y = 985

def fragment_times(sent_idx, frags, sent_start, sent_dur):
    align = word_align.get(str(sent_idx + 1), [])
    word_counts = [len(f.split()) for f in frags]
    total_words = sum(word_counts)
    times = []
    if len(align) == total_words:
        cum = 0
        for wc in word_counts:
            w_start = align[cum]["start"]
            w_end = align[cum + wc - 1]["end"]
            times.append([sent_start + w_start, sent_start + w_end])
            cum += wc
    else:
        char_counts = [len(f.replace(" ", "")) for f in frags]
        total_chars = sum(char_counts)
        t = sent_start
        for f, cc in zip(frags, char_counts):
            dur = sent_dur * cc / total_chars
            times.append([t, t + dur])
            t += dur
    # extend last fragment to cover the trailing pad/silence, no gap before next sentence
    times[-1][1] = sent_start + sent_dur
    return times

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

lines = [header]
t = 0.0
for i, (sent_dur, frags) in enumerate(zip(sentence_durations, FRAGMENTS)):
    times = fragment_times(i, frags, t, sent_dur)
    for frag, (start, end) in zip(frags, times):
        size = fit_size(frag)
        tag = f"{{\\an5\\pos(540,{CAP_CENTER_Y})\\fs{size}}}"
        lines.append(f"Dialogue: 1,{ts(start)},{ts(end)},Caption,,0,0,0,,{tag}{frag}\n")
    t += sent_dur

total = t

title_text = f"{{\\fs{title_size1}}}" + TITLE_LINES[0] + f"\\N{{\\fs{title_size2}}}" + TITLE_LINES[1]
lines.append(f"Dialogue: 2,{ts(0)},{ts(total)},Title,,0,0,0,,{title_text}\n")

with open("captions.ass", "w", encoding="utf-8-sig") as f:
    f.writelines(lines)

print("total duration:", total, "title sizes:", title_size1, title_size2)
