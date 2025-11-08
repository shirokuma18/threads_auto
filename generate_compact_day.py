#!/usr/bin/env python3
"""
Generate a compact schedule (12 posts/day) for specified dates, replacing existing rows.

Default targets (if no args):
  - 2025-11-12 放課後の光線
  - 2025-11-14 休符の居場所

Design:
  - 12 time slots, night emphasis up to 23:30.
  - Longer texts (M/L leaning), same world/voice.
  - Tags include exp:ppd=12 and other factors.
"""

from __future__ import annotations
import csv
import sys
from datetime import datetime, date
from pathlib import Path

CSV_PATH = Path('posts_schedule.csv')

SLOTS_12 = [
    (8,0),(9,30),(11,0),(12,30),(14,0),(15,30),
    (17,0),(18,30),(20,0),(21,0),(22,0),(23,30)
]

DEFAULTS = [
    (date(2025,11,12), '放課後の光線'),
    (date(2025,11,14), '休符の居場所'),
]


def rows_except_dates(ex_dates: set[str]):
    out = []
    with CSV_PATH.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            d = r['datetime'].split(' ')[0]
            if d not in ex_dates:
                out.append(r)
    return reader.fieldnames, out


def mktext(theme: str, longer: bool = True) -> str:
    a = f"放課後の教室は、光の向きがゆっくり変わる。{theme}は窓の端で細く折れて、黒板の粉の上に落ちる。"
    b = "私は急がない。子どもたちが帰ったあとにだけ見える線を、一本ずつ確かめる。"
    c = "声を使わない合図の練習は、たいてい静かな場所でうまくいく。"
    d = "明日の私が見つけられるように、黒板の端に小さな点を一つ置いておく。"
    text = a + "\n\n" + b + "\n\n" + c
    if longer:
        text += "\n\n" + d
    return text


def tags(ppd: int, thread: bool) -> str:
    # Mark ppd as an explicit factor; keep defaults for others
    return f"exp:ppd={ppd};len=L;op=sensory;end=yoin;br=3;concept=observation;tense=present;emoji=0;thread={'yes' if thread else 'no'}"


def main():
    # Parse args: pairs of YYYY-MM-DD:THEME
    targets = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if ':' in arg:
                dstr, theme = arg.split(':', 1)
            else:
                dstr, theme = arg, '短編'
            d = datetime.strptime(dstr, '%Y-%m-%d').date()
            targets.append((d, theme))
    else:
        targets = DEFAULTS

    ex_dates = {d.strftime('%Y-%m-%d') for d, _ in targets}
    header, kept = rows_except_dates(ex_dates)

    # rewrite file with kept first
    with CSV_PATH.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in kept:
            writer.writerow(r)

        # append 12-post days
        for day, theme in targets:
            for i, (h, m) in enumerate(SLOTS_12, start=1):
                row_id = f"{day.strftime('%Y%m%d')}{i:02d}"
                dt_str = f"{day.strftime('%Y-%m-%d')} {h:02d}:{m:02d}"
                text = mktext(theme, longer=True)
                thr = (h, m) in {(21,0),(23,30)}
                writer.writerow({
                    'id': row_id,
                    'datetime': dt_str,
                    'text': text,
                    'thread_text': "黒板の端に指を置いて、深呼吸を一つ。合図は音じゃなくて、ここにある。" if thr else '',
                    'status': 'pending',
                    'category': '教室短編',
                    'subcategory': theme,
                    'hashtags': tags(12, thr)
                })

    print('✅ Rebuilt compact days:', ', '.join(sorted(ex_dates)))


if __name__ == '__main__':
    main()

