#!/usr/bin/env python3
"""
曜日別最適化スケジュールでpending投稿をリスケジュール

戦略:
- 月曜: 7:00, 8:00, 9:00, 10:30, 11:00, 16:00, 17:00, 18:30, 19:00, 20:00 (10投稿)
- 火水木: 8:00, 9:00, 10:00, 11:00, 16:00, 17:00, 18:00, 19:00, 20:00, 21:00 (10投稿)
- 金曜: 8:00, 9:00, 10:00, 16:00, 17:00, 18:00, 19:00, 20:00, 21:00, 22:00 (10投稿)
- 土曜: 10:00, 11:00, 12:00, 14:00, 15:00, 16:00, 18:00, 19:00, 20:00, 21:00 (10投稿)
- 日曜: 10:00, 11:00, 12:00, 14:00, 15:00, 16:00, 17:00, 18:00, 19:00, 19:30 (10投稿)
"""

import csv
from datetime import datetime, timedelta

# 曜日別最適化スケジュール（時、分）
# weekday(): 0=月曜, 1=火曜, 2=水曜, 3=木曜, 4=金曜, 5=土曜, 6=日曜
SCHEDULES = {
    0: [(7, 0), (8, 0), (9, 0), (10, 30), (11, 0), (16, 0), (17, 0), (18, 30), (19, 0), (20, 0)],   # 月曜
    1: [(8, 0), (9, 0), (10, 0), (11, 0), (16, 0), (17, 0), (18, 0), (19, 0), (20, 0), (21, 0)],    # 火曜
    2: [(8, 0), (9, 0), (10, 0), (11, 0), (16, 0), (17, 0), (18, 0), (19, 0), (20, 0), (21, 0)],    # 水曜
    3: [(8, 0), (9, 0), (10, 0), (11, 0), (16, 0), (17, 0), (18, 0), (19, 0), (20, 0), (21, 0)],    # 木曜
    4: [(8, 0), (9, 0), (10, 0), (16, 0), (17, 0), (18, 0), (19, 0), (20, 0), (21, 0), (22, 0)],    # 金曜
    5: [(10, 0), (11, 0), (12, 0), (14, 0), (15, 0), (16, 0), (18, 0), (19, 0), (20, 0), (21, 0)],  # 土曜
    6: [(10, 0), (11, 0), (12, 0), (14, 0), (15, 0), (16, 0), (17, 0), (18, 0), (19, 0), (19, 30)],  # 日曜
}

def get_schedule_for_date(date):
    """指定日付の曜日に応じた投稿スケジュールを取得"""
    weekday = date.weekday()  # 0=月曜, 6=日曜
    return SCHEDULES[weekday]

def reschedule_pending_posts(csv_path, start_date=None):
    """pending投稿を曜日別最適化スケジュールでリスケジュール"""
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

    # 曜日別最適化スケジュールで再割り当て
    current_date = start_date
    rescheduled_count = 0

    while pending_rows:
        # 今日の曜日に応じたスケジュールを取得
        schedule = get_schedule_for_date(current_date)

        # 今日の投稿枠に割り当て
        for hour, minute in schedule:
            if not pending_rows:
                break

            row = pending_rows.pop(0)
            new_datetime = f"{current_date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}"
            row['datetime'] = new_datetime
            rows.append(row)
            rescheduled_count += 1

        # 次の日へ
        current_date += timedelta(days=1)

    print(f"リスケジュール完了: {rescheduled_count}件")
    print(f"最終日: {(current_date - timedelta(days=1)).strftime('%Y-%m-%d')}")

    # CSVに書き戻し（元の順序でソート）
    rows.sort(key=lambda x: (x.get('datetime', ''), x.get('id', '')))

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['id', 'datetime', 'text', 'thread_text', 'status', 'category', 'subcategory', 'hashtags']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ CSVを更新しました: {csv_path}")

    # サマリー表示
    print("\n📊 曜日別投稿数:")
    date_counts = {}
    for row in rows:
        if row.get('status') == 'pending':
            dt_str = row.get('datetime', '')
            if dt_str:
                date_part = dt_str.split(' ')[0]
                date_counts[date_part] = date_counts.get(date_part, 0) + 1

    for date_str in sorted(date_counts.keys())[:14]:  # 最初の2週間を表示
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

    reschedule_pending_posts(csv_path, start_date)
