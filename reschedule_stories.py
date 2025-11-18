#!/usr/bin/env python3
"""
CSVデータをストーリー単位で再スケジュール

1日3ストーリー投稿（朝8:00、昼12:00、夜19:00）
各ストーリーの全投稿を同じ日時にまとめる
"""

import csv
from datetime import datetime, timedelta
from collections import defaultdict

# 1日のスケジュール（時、分）
DAILY_SCHEDULE = [
    (8, 0),   # 朝
    (12, 0),  # 昼
    (19, 0),  # 夜
]


def reschedule_stories(csv_path, start_date=None):
    """pending投稿をストーリー単位で再スケジュール"""
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

    # ストーリー単位でグループ化
    stories = defaultdict(list)
    for row in pending_rows:
        csv_id = row.get('id', '')
        story_id = csv_id.split('_')[0]  # 例: 001_01 → 001
        stories[story_id].append(row)

    # ストーリーをIDでソート
    sorted_stories = sorted(stories.items(), key=lambda x: x[0])

    print(f"ストーリー数: {len(sorted_stories)}件")

    # ストーリー情報を表示
    print("\nストーリー一覧（最初の10件）:")
    for i, (story_id, posts) in enumerate(sorted_stories[:10], 1):
        subcategory = posts[0].get('subcategory', '')
        print(f"  {i}. {story_id}: {subcategory} - {len(posts)}投稿")

    # 各ストーリーに日時を割り当て
    current_date = start_date
    schedule_index = 0
    rescheduled_count = 0

    for story_id, posts in sorted_stories:
        # 現在のスケジュール時刻を取得
        hour, minute = DAILY_SCHEDULE[schedule_index]
        story_datetime = f"{current_date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}"

        # そのストーリーの全投稿に同じ日時を設定
        for post in posts:
            post['datetime'] = story_datetime
            rows.append(post)
            rescheduled_count += 1

        # 次のスケジュールへ
        schedule_index += 1
        if schedule_index >= len(DAILY_SCHEDULE):
            schedule_index = 0
            current_date += timedelta(days=1)

    print(f"\nリスケジュール完了: {rescheduled_count}件")
    print(f"最終日: {current_date.strftime('%Y-%m-%d')}")
    print(f"期間: {(current_date - start_date).days}日間")

    # CSVに書き戻し（日時とIDでソート）
    rows.sort(key=lambda x: (x.get('datetime', ''), x.get('id', '')))

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['id', 'datetime', 'text', 'thread_text', 'status', 'category', 'subcategory', 'hashtags']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ CSVを更新しました: {csv_path}")

    # 日別サマリーを表示
    print("\n📊 日別スケジュール（最初の14日）:")
    date_counts = defaultdict(lambda: {'朝': 0, '昼': 0, '夜': 0})

    for row in rows:
        if row.get('status') == 'pending':
            dt_str = row.get('datetime', '')
            if dt_str:
                date_part, time_part = dt_str.split(' ')
                hour = int(time_part.split(':')[0])

                if hour == 8:
                    time_slot = '朝'
                elif hour == 12:
                    time_slot = '昼'
                elif hour == 19:
                    time_slot = '夜'
                else:
                    continue

                date_counts[date_part][time_slot] += 1

    for date_str in sorted(date_counts.keys())[:14]:
        counts = date_counts[date_str]
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday_name = ['月', '火', '水', '木', '金', '土', '日'][date_obj.weekday()]
        total = sum(counts.values())
        print(f"  {date_str} ({weekday_name}): 朝{counts['朝']}件 昼{counts['昼']}件 夜{counts['夜']}件 (計{total}件)")


if __name__ == '__main__':
    import sys

    csv_path = 'data/posts_schedule.csv'
    start_date = None

    # コマンドライン引数で開始日を指定可能
    if len(sys.argv) > 1:
        start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()

    reschedule_stories(csv_path, start_date)
