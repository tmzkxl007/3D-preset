# -*- coding: utf-8 -*-
import json
from PIL import ImageFont

FONT_PATH = r"C:\Users\Administrator\AppData\Local\Microsoft\Windows\Fonts\NanumSquareRoundB.ttf"
TITLE_FONT_PATH = r"C:\Users\Administrator\OneDrive\바탕 화면\volcano-work\fonts_3d\Recipekorea 레코체 FONT.ttf"

FRAGMENTS = [
    ["한 남자가 혼자", "앉아 있는 여자에게", "다가가 합석을 부탁했습니다"],
    ["여자는 다짜고짜 큰 소리로", "그가 함께 밤을 보내자고", "했다며 몰아붙였어요"],
    ["식당 안 사람들은", "그를 손가락질하며", "수군거렸습니다"],
    ["남자는 아무 말 없이", "조용히 다른", "자리로 걸어갔죠"],
    ["잠시 후 여자가", "웃으며 다가와", "그에게 말을 걸었어요"],
    ["사실 자신은", "심리학 전공생이라고", "밝혔습니다"],
    ["사람들이 망신당할 때", "어떻게 반응하는지", "실험한 거라고 했죠"],
    ["그 순간 남자가", "갑자기 큰 소리로", "되받아쳤습니다"],
    ["하룻밤에 이십 달러는", "너무 비싸다며", "여자를 몰아붙였어요"],
    ["식당은 순식간에", "웃음바다가 됐습니다"],
    ["여자는 얼굴이 굳은 채", "아무 말도", "하지 못했죠"],
    ["남자는 자신이 법학도라며", "조용히 되갚아", "준 것이었습니다"],
]

with open("tts_durations.json", encoding="utf-8") as f:
    raw_durations = json.load(f)
with open("tts_word_align.json", encoding="utf-8") as f:
    word_align = json.load(f)

PAD = 0.15
sentence_durations = [d + PAD for d in raw_durations]
assert len(sentence_durations) == len(FRAGMENTS) == 12

TITLE_LINES = ["큰소리로 망신 준 여자가", "5분 뒤 당한 굴욕"]

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

TITLE_TARGET_WIDTH = 1060
TITLE_MAX = 130
TITLE_MIN = 50

def fit_title_size(text):
    return fit_size(text, font_path=TITLE_FONT_PATH, target_width=TITLE_TARGET_WIDTH,
                     max_size=TITLE_MAX, min_size=TITLE_MIN)

base_size = min(fit_title_size(TITLE_LINES[0]), fit_title_size(TITLE_LINES[1]))
title_size1 = int(base_size / 1.13)
title_size2 = base_size

TITLE_MIN_ACCEPTABLE = 75  # if the auto-fit shrinks below this, the title text is too long -- shorten it, don't ship it
if base_size < TITLE_MIN_ACCEPTABLE:
    print(f"!! WARNING: title font size {base_size}px is below the {TITLE_MIN_ACCEPTABLE}px minimum -- "
          f"TITLE_LINES is too long, shorten it and rerun before rendering.")

CAP_CENTER_Y = 1065

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
