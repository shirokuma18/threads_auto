#!/usr/bin/env python3
"""
CSVデータを1日3投稿のスケジュールに再割り当て

スケジュール: 8:00, 12:00, 19:00
"""

import csv
from datetime import datetime, timedelta

# 1日のスケジュール（時、分）
DAILY_SCHEDULE = [
    (8, 0),   # 朝
    (12, 0),  # 昼
    (19, 0),  # 夜
]


def reschedule_3posts_daily(csv_path, start_date=None):
    """pending投稿を1日3投稿のスケジュールで再割り当て"""
    if start_date is None:
        start_date = datetime.now().date()

    print(f"開始日: {start_date}")
    print(f"CSVファイル: {csv_path}")

    # CSVを読み込み
    rows = []
    pending_rows = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'pending':
                pending_rows.append(row)
            else:
                rows.append(row)

    print(f"\nPending投稿数: {len(pending_rows)}件")

    # Pending投稿をIDでソート（元の順序を維持）
    pending_rows.sort(key=lambda x: x.get('id', ''))

    # 1日3投稿のスケジュールで再割り当て
    current_date = start_date
    schedule_index = 0
    rescheduled_count = 0

    for row in pending_rows:
        # 現在のスケジュール時刻を取得
        hour, minute = DAILY_SCHEDULE[schedule_index]
        new_datetime = f"{current_date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}"
        row['datetime'] = new_datetime
        rows.append(row)
        rescheduled_count += 1

        # 次のスケジュールへ
        schedule_index += 1
        if schedule_index >= len(DAILY_SCHEDULE):
            schedule_index = 0
            current_date += timedelta(days=1)

    print(f"リスケジュール完了: {rescheduled_count}件")
    print(f"最終日: {(current_date if schedule_index == 0 else current_date).strftime('%Y-%m-%d')}")
    total_days = (current_date - start_date).days + (1 if schedule_index > 0 else 0)
    print(f"期間: {total_days}日間")

    # CSVに書き戻し（元の順序でソート）
    rows.sort(key=lambda x: (x.get('datetime', ''), x.get('id', '')))

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['id', 'datetime', 'text', 'thread_text', 'status', 'category', 'subcategory', 'hashtags']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ CSVを更新しました: {csv_path}")

    # サマリー表示
    print("\n📊 日別投稿数（最初の14日）:")
    from collections import Counter
    date_counts = Counter()

    for row in rows:
        if row.get('status') == 'pending':
            dt_str = row.get('datetime', '')
            if dt_str:
                date_part = dt_str.split(' ')[0]
                date_counts[date_part] += 1

    for date_str in sorted(date_counts.keys())[:14]:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday_name = ['月', '火', '水', '木', '金', '土', '日'][date_obj.weekday()]
        print(f"  {date_str} ({weekday_name}): {date_counts[date_str]}投稿")


if __name__ == '__main__':
    import sys

    csv_path = 'data/posts_schedule.csv'
    start_date = None

    # コマンドライン引数で開始日を指定可能
    if len(sys.argv) > 1:
        start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()

    reschedule_3posts_daily(csv_path, start_date)
