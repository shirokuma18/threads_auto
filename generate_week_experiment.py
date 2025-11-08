#!/usr/bin/env python3
"""
Generate a 5-day experiment schedule (11/11–11/15 JST) with 25 posts/day.

- Writes to posts_schedule.csv (appends).
- Night-emphasis schedule up to 23:30.
- Adds experiment tags in `hashtags` as a semicolon-separated key=value list.
  Example: exp:len=M;op=sensory;end=yoin;br=3;concept=observation;tense=present;emoji=0;thread=no

Content: short literary vignettes in Japanese, first-person teacher POV.
"""

from __future__ import annotations
import csv
import random
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
import os

def default_csv_path() -> Path:
    env = os.getenv('CSV_FILE')
    if env:
        return Path(env)
    p = Path('data/posts_schedule.csv')
    return p if p.exists() else Path('posts_schedule.csv')

CSV_PATH = default_csv_path()

JST = timedelta(hours=9)  # used only for labels

NIGHT_THREAD_TIMES = {(20,0), (20,30), (21,0), (22,0), (23,0)}

# 25 time slots per day (night-heavy, 30-min granularity)
SLOTS = [
    (8,0),(8,30),(9,0),(9,30),(11,0),
    (12,0),(13,0),(14,0),(14,30),(15,0),
    (15,30),(16,0),(16,30),(18,0),(18,30),
    (19,0),(19,30),(20,0),(20,30),(21,0),
    (21,30),(22,0),(22,30),(23,0),(23,30)
]

THEMES = [
    (date(2025,11,11), '窓ぎわの天気予報'),
    (date(2025,11,12), '放課後の光線'),
    (date(2025,11,13), 'しおりの住所'),
    (date(2025,11,14), '休符の居場所'),
    (date(2025,11,15), 'チャイムの前後'),
]

LEN_BUCKETS = ['S','M','L']
OPENINGS = ['sensory','introspect','dialogue']
ENDINGS = ['yoin','softhook']  # 余韻 or さりげないフック
BREAKS = [2,3,4]
CONCEPTS = ['observation','teacher','parent','object']
TENSES = ['present','past']


def choose_factors(idx: int):
    """Balanced factor assignment over the 25 slots."""
    # Fixed seeded shuffle per index to be reproducible
    random.seed(idx * 9973)
    len_pool = (['S']*8 + ['M']*12 + ['L']*5)
    op_pool = (['sensory']*10 + ['dialogue']*7 + ['introspect']*8)
    end_pool = (['yoin']*18 + ['softhook']*7)
    br_pool = ([3]*14 + [2]*6 + [4]*5)
    concept_pool = (['observation']*12 + ['teacher']*5 + ['parent']*4 + ['object']*4)
    tense_pool = (['present']*18 + ['past']*7)

    random.shuffle(len_pool)
    random.shuffle(op_pool)
    random.shuffle(end_pool)
    random.shuffle(br_pool)
    random.shuffle(concept_pool)
    random.shuffle(tense_pool)

    return list(zip(len_pool, op_pool, end_pool, br_pool, concept_pool, tense_pool))


def emoji_for(concept: str) -> int:
    # Mostly 0; allow a single subtle emoji in some observation/parent posts
    return 1 if concept in ('observation','parent') and random.random() < 0.2 else 0


def make_opening(theme: str, op: str, tense: str) -> str:
    if op == 'sensory':
        if tense == 'present':
            return f"窓ぎわに立つと、{theme}の匂いが薄く流れ込む。"
        else:
            return f"窓ぎわに立ったとき、{theme}の匂いが薄く流れ込んだ。"
    if op == 'dialogue':
        if tense == 'present':
            return f"「先生、きょうの{theme}は晴れ？」と誰かが聞く。"
        else:
            return f"『先生、きょうの{theme}は晴れ？』と誰かが聞いた。"
    # introspect
    if tense == 'present':
        return f"黒板の粉を払うたび、{theme}に似た形の雲が浮かぶのを思う。"
    return f"黒板の粉を払うたび、{theme}に似た形の雲が浮かんでいたのを思い出す。"


def make_body(theme: str, concept: str, tense: str) -> str:
    if concept == 'observation':
        return "子どもたちの目線は低く、机の角で風が曲がる。私は何も言わず、その曲がり方だけを覚える。"
    if concept == 'teacher':
        return "配るプリントを一枚だけ残し、手の中で折り目を感じる。言葉より先に、視線の高さを揃える。"
    if concept == 'parent':
        return "連絡帳の余白に短い返事を書く。説明のない安心が、ときどき一番届く。"
    # object view
    return "窓枠は季節の重さで少しきしむ。鉛筆立ては、昼休みになると光の帯の中に避難する。"


def make_ending(theme: str, ending: str, tense: str) -> str:
    if ending == 'yoin':
        if tense == 'present':
            return f"チャイムの前後だけ、{theme}は少しだけ静かになる。私はその静けさをポケットにしまう。"
        else:
            return f"チャイムの前後だけ、{theme}は少し静かになった。私はその静けさをポケットにしまった。"
    # softhook (gentle, non-coercive)
    if tense == 'present':
        return f"黒板の端に小さな点を一つ。明日の私が見つける目印にする。"
    return f"黒板の端に小さな点を一つ残した。明日の私への目印だった。"


def build_text(theme: str, lb: str, op: str, end: str, br: int, concept: str, tense: str, use_emoji: int) -> str:
    parts = [make_opening(theme, op, tense), make_body(theme, concept, tense), make_ending(theme, end, tense)]
    # paragraph breaks
    if br == 2:
        parts = [parts[0] + "\n" + parts[1], parts[2]]
    elif br == 4:
        parts.insert(1, "教室の時計が一度だけ長く鳴る。")
    text = "\n\n".join(parts)
    if use_emoji:
        text += "\n\n" + "（少しだけ、胸のあたりが軽い🙂）"
    # adjust length subtly: add a descriptive clause for L
    if lb == 'L':
        text += "\n\n" + "窓の外の雲は、ノートの罫線みたいに細く重なっていた。"
    return text


def tags(lb, op, end, br, concept, tense, thread):
    return f"exp:len={lb};op={op};end={end};br={br};concept={concept};tense={tense};emoji={0};thread={'yes' if thread else 'no'}"


def next_index_for_day(d: date, used: set[int]) -> int:
    # 01..99 per day
    for i in range(1, 100):
        if i not in used:
            return i
    raise RuntimeError('index overflow')


def read_existing_ids() -> set[str]:
    if not CSV_PATH.exists():
        return set()
    with CSV_PATH.open('r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return set()
    header, *data = rows
    idx = header.index('id') if 'id' in header else 0
    return {r[idx] for r in data if r}


def main():
    existing_ids = read_existing_ids()
    out_exists = CSV_PATH.exists()
    # Ensure header
    if not out_exists:
        with CSV_PATH.open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id','datetime','text','thread_text','status','category','subcategory','hashtags'])

    with CSV_PATH.open('a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for day, theme in THEMES:
            # balance factors over 25 slots
            factors = choose_factors(int(day.strftime('%Y%m%d')))
            used_idx = set()
            for slot_idx, (h, m) in enumerate(SLOTS):
                lb, op, end, br, concept, tense = factors[slot_idx % len(factors)]
                random.seed((day.toordinal() * 37) + slot_idx)
                emj = emoji_for(concept)
                thread = (h, m) in NIGHT_THREAD_TIMES
                text = build_text(theme, lb, op, end, br, concept, tense, emj)
                thread_text = ""
                if thread:
                    # gentle second note
                    thread_text = "黒板の端に指を置いて、深呼吸を一つ。合図は音じゃなくて、ここにある。"
                idx = next_index_for_day(day, used_idx)
                used_idx.add(idx)
                row_id = f"{day.strftime('%Y%m%d')}{idx:02d}"
                # keep IDs unique globally
                while row_id in existing_ids:
                    idx = next_index_for_day(day, used_idx)
                    used_idx.add(idx)
                    row_id = f"{day.strftime('%Y%m%d')}{idx:02d}"
                dt_str = f"{day.strftime('%Y-%m-%d')} {h:02d}:{m:02d}"
                tag_str = tags(lb, op, end, br, concept, tense, thread)
                writer.writerow([row_id, dt_str, text, thread_text or None, 'pending', '教室短編', theme, tag_str])

    print("✅ Generated experiment schedule for:")
    for d, theme in THEMES:
        print(f"  {d} — {theme} (25 posts)")


if __name__ == '__main__':
    main()
