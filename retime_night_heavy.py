#!/usr/bin/env python3
"""
Retime selected dates to a night-heavy schedule while preserving post order/content.

Targets (if no args): 2025-11-11, 2025-11-13, 2025-11-15

Policy (25 posts/day): prioritize 17:00–23:30, then 16:00–16:30, 15:00–15:30, 14:00, 13:30–13:00, 12:00, 11:00, 09:30, 08:30.
This keeps 25 unique 30-min slots with maximal night presence.
"""

from __future__ import annotations
import csv
import sys
from datetime import datetime, date
from pathlib import Path

CSV_PATH = Path('posts_schedule.csv')

# night-heavy 25-slot ordering (ascending time)
SLOTS25 = [
    (8,30),(9,30),(11,0),(12,0),(13,0),(13,30),(14,0),(15,0),(15,30),(16,0),(16,30),
    (17,0),(17,30),(18,0),(18,30),(19,0),(19,30),(20,0),(20,30),(21,0),(21,30),(22,0),(22,30),(23,0),(23,30)
]

DEFAULTS = [date(2025,11,11), date(2025,11,13), date(2025,11,15)]


def load_rows():
    with CSV_PATH.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def main():
    targets = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            targets.append(datetime.strptime(arg, '%Y-%m-%d').date())
    else:
        targets = DEFAULTS

    header, rows = load_rows()
    by_date = {}
    keep = []
    for r in rows:
        d = r['datetime'].split(' ')[0]
        by_date.setdefault(d, []).append(r)

    # rewrite
    with CSV_PATH.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for d, lst in by_date.items():
            d_date = datetime.strptime(d, '%Y-%m-%d').date()
            if d_date in targets:
                # sort existing rows by original datetime to keep narrative order
                lst_sorted = sorted(lst, key=lambda r: r['datetime'])
                # only retime days that have exactly 25 posts (safety)
                if len(lst_sorted) != 25:
                    for r in lst_sorted:
                        writer.writerow(r)
                    continue
                for i, r in enumerate(lst_sorted):
                    h, m = SLOTS25[i]
                    r['datetime'] = f"{d} {h:02d}:{m:02d}"
                    writer.writerow(r)
            else:
                for r in lst:
                    writer.writerow(r)

    print('✅ Retimed night-heavy for:', ', '.join([d.strftime('%Y-%m-%d') for d in targets]))


if __name__ == '__main__':
    main()

