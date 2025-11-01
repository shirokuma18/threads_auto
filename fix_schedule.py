#!/usr/bin/env python3
"""
投稿スケジュールの時間帯を内容に合わせて調整するスクリプト

手順:
1. 時間帯と内容の不一致を検出
2. 適切な時間帯に投稿を再配置
3. 1日32投稿の上限を守りながら再スケジュール
"""

import csv
from datetime import datetime, timedelta
from collections import defaultdict

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

# 時間帯の定義
TIME_SLOTS = {
    'morning': range(8, 12),      # 8:00-11:59 (朝)
    'afternoon': range(12, 18),   # 12:00-17:59 (午後)
    'evening': range(18, 24)      # 18:00-23:59 (夕方〜夜)
}

def get_preferred_time_slot(text):
    """投稿内容から適切な時間帯を判定"""
    # 夕方〜夜向けのキーワード
    if any(kw in text for kw in ['仕事終わった', '帰宅', '今日も疲れた', '今日の仕事', '退勤']):
        return 'evening'

    # 朝向けのキーワード
    if any(kw in text for kw in ['おはよう', '朝活', '朝の散歩', '出勤前', 'よく眠れた', '早起き']):
        return 'morning'

    # 午後向けのキーワード
    if any(kw in text for kw in ['お昼', 'ランチ', '午後から']):
        return 'afternoon'

    # デフォルトはどこでもOK
    return None


def get_time_slot(hour):
    """時刻から時間帯を取得"""
    for slot_name, hours in TIME_SLOTS.items():
        if hour in hours:
            return slot_name
    return None


def main():
    print("=" * 70)
    print("📅 投稿スケジュール最適化ツール")
    print("=" * 70)
    print(f"\n最大投稿数/日: {MAX_POSTS_PER_DAY}件")
    print(f"スケジュール時刻: 8:00-23:30（30分間隔）\n")

    # CSVを読み込み
    rows = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"総投稿数: {len(rows)}件\n")

    # 各投稿の情報を準備
    posts = []
    mismatches = []

    for row in rows:
        datetime_str = row['datetime'].strip()
        if not datetime_str:
            continue

        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        text = row['text']

        preferred_slot = get_preferred_time_slot(text)
        current_slot = get_time_slot(dt.hour)

        # 時間帯の不一致をチェック
        is_mismatch = False
        if preferred_slot and current_slot and preferred_slot != current_slot:
            is_mismatch = True
            preview = text.replace('\n', ' ')[:50]
            mismatches.append({
                'id': row['id'],
                'datetime': dt,
                'preferred': preferred_slot,
                'current': current_slot,
                'preview': preview
            })

        posts.append({
            'row': row,
            'datetime': dt,
            'preferred_slot': preferred_slot,
            'is_mismatch': is_mismatch
        })

    # 不一致の報告
    if mismatches:
        print(f"⚠️  時間帯の不一致: {len(mismatches)}件\n")
        for m in mismatches:
            print(f"  ID {m['id']} ({m['datetime'].strftime('%H:%M')}): {m['current']} → {m['preferred']} へ移動")
            print(f"    → {m['preview']}...\n")
    else:
        print("✓ 時間帯の不一致なし\n")

    # 再スケジュール
    # 優先順: 不一致なし > 不一致あり
    posts.sort(key=lambda x: (x['is_mismatch'], x['datetime']))

    # 日付・時間帯別のスロット管理
    schedule = defaultdict(lambda: defaultdict(list))  # {date: {time_slot: [posts]}}

    for post in posts:
        original_dt = post['datetime']
        preferred_slot = post['preferred_slot']
        row = post['row']

        # 配置先を決定
        target_date = original_dt.date()
        target_slot = preferred_slot if preferred_slot else get_time_slot(original_dt.hour)

        # その日のその時間帯のスロットを取得
        day_schedule = schedule[target_date]

        # 日の上限チェック
        total_posts_on_day = sum(len(posts) for posts in day_schedule.values())

        # 上限に達している場合は翌日へ
        while total_posts_on_day >= MAX_POSTS_PER_DAY:
            target_date = target_date + timedelta(days=1)
            day_schedule = schedule[target_date]
            total_posts_on_day = sum(len(posts) for posts in day_schedule.values())

        # スロットに追加
        day_schedule[target_slot].append((post, row))

    # スケジュールを最終調整してCSV用のデータを作成
    final_rows = []

    for date in sorted(schedule.keys()):
        day_schedule = schedule[date]

        # 時間帯ごとに処理
        for slot_name in ['morning', 'afternoon', 'evening']:
            if slot_name not in day_schedule:
                continue

            slot_posts = day_schedule[slot_name]
            slot_hours = TIME_SLOTS[slot_name]

            # その時間帯の利用可能な時刻を取得
            available_times = [(h, m) for h, m in SCHEDULE_TIMES if h in slot_hours]

            # 投稿を時刻に割り当て
            for i, (post, row) in enumerate(slot_posts):
                if i >= len(available_times):
                    # 時刻が足りない場合は次の時間帯へ（本来起きないはず）
                    available_times = [(h, m) for h, m in SCHEDULE_TIMES]

                time_idx = i % len(available_times)
                hour, minute = available_times[time_idx]

                new_dt = datetime(date.year, date.month, date.day, hour, minute)
                row['datetime'] = new_dt.strftime('%Y-%m-%d %H:%M')
                final_rows.append(row)

    # 結果の表示
    print("\n📊 最終スケジュール:")
    posts_by_date = defaultdict(int)
    for row in final_rows:
        dt = datetime.strptime(row['datetime'], '%Y-%m-%d %H:%M')
        posts_by_date[dt.date()] += 1

    for date in sorted(posts_by_date.keys()):
        count = posts_by_date[date]
        print(f"  {date}: {count}件 ✓")

    # CSVに書き込み
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        fieldnames = rows[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)

    print(f"\n✅ スケジュール最適化完了: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
