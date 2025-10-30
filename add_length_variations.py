#!/usr/bin/env python3
"""
投稿に文字数バリエーションを追加するスクリプト
150-250文字（短文）、250-350文字（中文）、350-500文字（長文）
"""

import csv
import re

# 短文化する投稿ID（150-250文字）
SHORT_IDS = [27, 30, 33, 36, 41, 44, 48, 49, 51, 54, 59, 64, 68, 71, 74, 75]

# 中文化する投稿ID（250-350文字）
MEDIUM_IDS = [28, 31, 34, 37, 42, 45, 50, 52, 55, 58, 61, 65, 69, 72, 73]

def shorten_text(text, target_length=200):
    """テキストを短縮する"""
    lines = text.split('\n')

    # チェックリスト形式の場合
    if '✅' in text:
        # チェック項目を3つに減らす
        check_items = [l for l in lines if '✅' in l][:3]
        rest = [l for l in lines if '✅' not in l]

        # 簡潔なバージョンを作成
        result = []
        in_checklist = False
        item_count = 0

        for line in lines:
            if '✅' in line and item_count < 3:
                result.append(line)
                item_count += 1
            elif '全部当てはまった' in line or 'やったこと' in line:
                result.append(line)
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.') or line.startswith('5.'):
                # 詳細説明を省略、1行にまとめる
                if item_count <= 5:
                    simple_line = line.split('→')[0].strip()
                    result.append(simple_line)
                    item_count += 1
            elif '【' in line or '変化' in line or 'じゃなくて' in line or '✨' in line:
                result.append(line)

        return '\n'.join(result)

    # Before/After形式の場合
    elif '【Before' in text or '【After' in text:
        # 重要な部分だけ残す
        result = []
        for line in lines:
            if '【Before' in line or '【After' in line or '：' in line or '貯金' in line or '節約' in line or 'じゃなくて' in line or '✨' in line:
                result.append(line)
        return '\n'.join(result)

    # その他の形式：重要な行だけ残す
    else:
        result = []
        for line in lines:
            if line.startswith('私「') or line.startswith('友人「') or '【' in line or 'じゃなくて' in line or '✨' in line or line.startswith('1.') or line.startswith('結果'):
                result.append(line)
        return '\n'.join(result)

def medium_text(text, target_length=300):
    """テキストを中文にする（詳細を少し減らす）"""
    lines = text.split('\n')
    result = []
    detail_count = 0

    for line in lines:
        # メインの内容は全て残す
        if '✅' in line or '【' in line or line.startswith('私「') or line.startswith('友人「') or 'じゃなくて' in line or '✨' in line:
            result.append(line)
        # 詳細説明は間引く
        elif line.startswith('   ') or line.startswith('  '):
            detail_count += 1
            if detail_count % 2 == 0:  # 2つに1つだけ残す
                result.append(line)
        else:
            result.append(line)

    return '\n'.join(result)

def process_csv():
    """CSVを処理して文字数バリエーションを追加"""

    with open('posts_schedule.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 各行を処理
    for row in rows:
        post_id = int(row['id'])
        text = row['text']

        # 短文化
        if post_id in SHORT_IDS:
            row['text'] = shorten_text(text, 200)
            print(f"ID {post_id}: 短文化 ({len(row['text'])} 文字)")

        # 中文化
        elif post_id in MEDIUM_IDS:
            row['text'] = medium_text(text, 300)
            print(f"ID {post_id}: 中文化 ({len(row['text'])} 文字)")

        # 長文はそのまま
        else:
            print(f"ID {post_id}: 長文維持 ({len(text)} 文字)")

    # CSVに書き込み
    with open('posts_schedule.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n✅ 文字数バリエーション追加完了")

    # 統計
    short_count = len([r for r in rows if int(r['id']) in SHORT_IDS])
    medium_count = len([r for r in rows if int(r['id']) in MEDIUM_IDS])
    long_count = len(rows) - short_count - medium_count

    print(f"\n📊 文字数分布:")
    print(f"  短文 (150-250字): {short_count}投稿")
    print(f"  中文 (250-350字): {medium_count}投稿")
    print(f"  長文 (350-500字): {long_count}投稿")

if __name__ == '__main__':
    process_csv()
