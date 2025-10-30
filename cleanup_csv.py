#!/usr/bin/env python3
"""
投稿済みIDをposts_schedule.csvから削除するスクリプト

使い方:
    python3 cleanup_csv.py "1,2,3"  # カンマ区切りのIDを渡す
"""

import csv
import sys

def cleanup_posted_ids(posted_ids_str):
    """投稿済みのIDをCSVから削除"""

    if not posted_ids_str:
        print("削除対象のIDがありません")
        return

    # IDのセットを作成
    posted_ids = set(posted_ids_str.split(','))
    rows = []

    # CSVを読み込み、投稿済みIDを除外
    with open('posts_schedule.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row['id'] not in posted_ids:
                rows.append(row)

    # CSVを書き込み
    with open('posts_schedule.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f'✅ {len(posted_ids)} 件を削除、{len(rows)} 件が残っています')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cleanup_posted_ids(sys.argv[1])
    else:
        print("エラー: 投稿済みIDを引数として渡してください")
        sys.exit(1)
