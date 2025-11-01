#!/usr/bin/env python3
"""
投稿スケジュールの日付を調整するスクリプト

目的: 1日の投稿数上限（32件）を超えた投稿を翌日以降に自動的に再スケジュール
"""

import csv
from datetime import datetime, timedelta

# 設定
MAX_POSTS_PER_DAY = 32
INPUT_FILE = 'posts_schedule.csv'
OUTPUT_FILE = 'posts_schedule.csv'

# 30分間隔のスケジュール時刻（JST）
SCHEDULE_TIMES = [
    (8, 0), (8, 30), (9, 0), (9, 30), (10, 0), (10, 30), (11, 0), (11, 30),
    (12, 0), (12, 30), (13, 0), (13, 30), (14, 0), (14, 30), (15, 0), (15, 30),
    (16, 0), (16, 30), (17, 0), (17, 30), (18, 0), (18, 30), (19, 0), (19, 30),
    (20, 0), (20, 30), (21, 0), (21, 30), (22, 0), (22, 30), (23, 0), (23, 30)
]


def main():
    print("=" * 70)
    print("📅 投稿スケジュール調整ツール")
    print("=" * 70)
    print(f"\n最大投稿数/日: {MAX_POSTS_PER_DAY}件")
    print(f"スケジュール時刻: 8:00-23:30（30分間隔）")

    # CSVを読み込み
    rows = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"\n総投稿数: {len(rows)}件")

    # 日付ごとにグループ化
    posts_by_date = {}
    for row in rows:
        datetime_str = row['datetime'].strip()
        if not datetime_str:
            continue

        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        date_key = dt.date()

        if date_key not in posts_by_date:
            posts_by_date[date_key] = []
        posts_by_date[date_key].append((dt, row))

    # 日付順にソート
    sorted_dates = sorted(posts_by_date.keys())

    print("\n📊 日付別投稿数（調整前）:")
    for date in sorted_dates:
        count = len(posts_by_date[date])
        overflow = max(0, count - MAX_POSTS_PER_DAY)
        status = f" ⚠️ {overflow}件オーバー" if overflow > 0 else " ✓"
        print(f"  {date}: {count}件{status}")

    # 再スケジュール
    rescheduled_rows = []
    current_date = None
    current_date_count = 0
    current_time_index = 0

    # すべての投稿を日付順・時刻順にソート
    all_posts = []
    for date in sorted_dates:
        for dt, row in posts_by_date[date]:
            all_posts.append((dt, row))
    all_posts.sort(key=lambda x: x[0])

    for original_dt, row in all_posts:
        # 日付が変わったらリセット
        if current_date != original_dt.date():
            current_date = original_dt.date()
            current_date_count = 0
            current_time_index = 0

        # その日の上限に達したら翌日に移動
        if current_date_count >= MAX_POSTS_PER_DAY:
            # 翌日に移動
            current_date = current_date + timedelta(days=1)
            current_date_count = 0
            current_time_index = 0

        # スケジュール時刻を取得
        schedule_hour, schedule_minute = SCHEDULE_TIMES[current_time_index]

        # 新しい日時を設定
        new_dt = datetime(
            current_date.year,
            current_date.month,
            current_date.day,
            schedule_hour,
            schedule_minute
        )

        # 行を更新
        row['datetime'] = new_dt.strftime('%Y-%m-%d %H:%M')
        rescheduled_rows.append(row)

        # カウンタを更新
        current_date_count += 1
        current_time_index = (current_time_index + 1) % len(SCHEDULE_TIMES)

    print("\n📊 日付別投稿数（調整後）:")
    posts_by_date_after = {}
    for row in rescheduled_rows:
        datetime_str = row['datetime'].strip()
        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        date_key = dt.date()

        if date_key not in posts_by_date_after:
            posts_by_date_after[date_key] = []
        posts_by_date_after[date_key].append(row)

    for date in sorted(posts_by_date_after.keys()):
        count = len(posts_by_date_after[date])
        print(f"  {date}: {count}件 ✓")

    # CSVに書き込み
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        fieldnames = rows[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rescheduled_rows)

    print(f"\n✅ スケジュール調整完了: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
