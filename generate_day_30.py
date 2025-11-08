#!/usr/bin/env python3
"""
Generate exactly 30 posts for a given date:
- 8 stories x 3 posts = 24 (self-contained micro-scenes with a shared motif)
- 6 mini-essays (考察) = 6

Schedule (JST, 30-min slots, night-heavy):
Stories use consecutive 3 slots. Essays fill gaps. Leaves 2 spare slots of the 32/day grid.

Usage:
  python3 generate_day_30.py 2025-11-09 黒板の雪

Env:
  CSV_FILE (optional) — output csv path. Falls back to data/posts_schedule.csv or posts_schedule.csv
"""

from __future__ import annotations
import csv
import os
import sys
from datetime import datetime
from pathlib import Path


def csv_path() -> Path:
    env = os.getenv('CSV_FILE')
    if env:
        return Path(env)
    p = Path('data/posts_schedule.csv')
    return p if p.exists() else Path('posts_schedule.csv')


SLOTS = [
    (8,0),(8,30),(9,0),(9,30),(10,0),(10,30),(11,0),(11,30),(12,0),(12,30),
    (13,0),(13,30),(14,0),(14,30),(15,0),(15,30),(16,0),(16,30),(17,0),(17,30),
    (18,0),(18,30),(19,0),(19,30),(20,0),(20,30),(21,0),(21,30),(22,0),(22,30),(23,0),(23,30)
]

# 8 story blocks (3 consecutive slots each) + 6 essays
STORY_BLOCKS = [
    [(8,30),(9,0),(9,30)],
    [(11,0),(11,30),(12,0)],
    [(13,30),(14,0),(14,30)],
    [(15,0),(15,30),(16,0)],
    [(17,0),(17,30),(18,0)],
    [(19,0),(19,30),(20,0)],
    [(20,30),(21,0),(21,30)],
    [(22,0),(22,30),(23,0)],
]

ESSAYS = [(8,0),(10,0),(12,30),(16,30),(18,30),(23,30)]


def rm_day_rows(path: Path, day: str) -> list[dict]:
    rows: list[dict] = []
    if path.exists():
        with path.open('r', encoding='utf-8') as f:
            r = csv.DictReader(f)
            for row in r:
                d = row.get('datetime','').split(' ')[0]
                if d != day:
                    rows.append(row)
    return rows


def fmt_dt(day: str, h: int, m: int) -> str:
    return f"{day} {h:02d}:{m:02d}"


def story_text(theme: str, idx: int, part: int) -> str:
    """各パートは単独でも楽しめる情景＋小さな手がかり＋やわらかな余韻。
    明示的な『続きは』は使わず、次を読みたくなる“未完の呼吸”を残す。"""
    if part == 1:
        return (
            f"{theme}の朝。昇降口のゴムの匂い、まだ乾ききらない黒板、袖口につく白い粉。\n\n"
            "そらは椅子の前脚を床から少しだけ浮かせて座る。鈴は鳴らない。\n\n"
            "最初の一文を置いたとき、教室の空気が半歩だけ動いた気がした。その動きの行き先が、まだわからない。"
        )
    if part == 2:
        return (
            f"{theme}の昼。窓ぎわの光が机の端で曲がり、ノートの罫線が波打つ。\n\n"
            "黒板の隅に小さな丸。そこにだけ風が触れているように見える。問いは出さない。視線だけが集まる。\n\n"
            "手を伸ばせば届くのに、誰もまだ触れない。その距離感に、今日の答えの形がうっすら見えた。"
        )
    # part 3
    return (
        f"{theme}の夕方。廊下の自転車のチェーンが一度鳴り、窓の色が低くなる。\n\n"
        "連絡帳の余白に短く書く。『合図は強制ではない。選べると安心は増える』。\n\n"
        "黒板の丸はそのまま残す。消さない理由が、明日の始業前にきっと見つかる。"
    )


def essay_text(theme: str, slot: tuple[int,int]) -> str:
    """観察ノート: 具体の情景→仮説→問い。結論は置き切らず、考えを進める手がかりにする。"""
    h, m = slot
    when = f"{h:02d}:{m:02d}"
    return (
        f"{when}の観察ノート。{theme}。\n\n"
        "黒板の端に指を置くと、粉が音もなく崩れて小さな光をつくる。\n"
        "『見える合図』は、言葉より先に届くのか。\n\n"
        "もしそうなら、説明は『あとから追いかけるもの』でいいのかもしれない。今日はここまで。"
    )


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 generate_day_30.py YYYY-MM-DD THEME')
        sys.exit(1)
    day = sys.argv[1]
    theme = sys.argv[2]
    # Validate
    datetime.strptime(day, '%Y-%m-%d')

    out = csv_path()
    rows = rm_day_rows(out, day)

    # Build new day rows
    newrows: list[dict] = []
    # stories
    for sidx, block in enumerate(STORY_BLOCKS, start=1):
        series = f"S{sidx}"
        for part, (h,m) in enumerate(block, start=1):
            rid = f"{day.replace('-','')}{sidx:02d}{part}"
            newrows.append({
                'id': rid,
                'datetime': fmt_dt(day,h,m),
                'text': story_text(theme, sidx, part),
                'thread_text': '',
                'status': 'pending',
                'category': '教室短編',
                'subcategory': theme,
                'hashtags': f"exp:type=story;series={series};part={part};hook=soft"
            })

    # essays
    for (h,m) in ESSAYS:
        rid = f"{day.replace('-','')}E{h:02d}{m:02d}"
        newrows.append({
            'id': rid,
            'datetime': fmt_dt(day,h,m),
            'text': essay_text(theme, (h,m)),
            'thread_text': '',
            'status': 'pending',
            'category': '教室短編',
            'subcategory': f"{theme} 考察",
            'hashtags': "exp:type=essay;hook=soft"
        })

    # sort by datetime
    newrows.sort(key=lambda r: r['datetime'])
    rows.extend(newrows)

    # ensure header
    header = ['id','datetime','text','thread_text','status','category','subcategory','hashtags']
    # write
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"✅ Generated 30 posts for {day} ({theme}). Output: {out}")


if __name__ == '__main__':
    main()
