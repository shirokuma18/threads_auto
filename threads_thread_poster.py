#!/usr/bin/env python3
"""
スレッド形式投稿スクリプト - 1つの小説を1つのスレッドにまとめて投稿

使い方:
- python3 threads_thread_poster.py              今日のストーリーを投稿
- python3 threads_thread_poster.py --dry-run    ドライランモード
- python3 threads_thread_poster.py 2025-11-19   指定日のストーリーを投稿
"""

import csv
import time
import requests
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path

# 環境変数読み込み
load_dotenv(override=True)

# Threads API設定
API_BASE_URL = 'https://graph.threads.net/v1.0'
ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
USER_ID = os.getenv('THREADS_USER_ID')

# JST タイムゾーン
JST = timezone(timedelta(hours=9))

# 設定
POST_INTERVAL_SECONDS = 3600  # スレッド内の投稿間隔（秒、1時間）
DRY_RUN = '--dry-run' in sys.argv


def resolve_csv_path():
    """CSVファイルのパスを解決"""
    csv_path = Path('data/posts_schedule.csv')
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    return str(csv_path)


def get_story_posts_for_date(csv_file, target_date):
    """指定日付の投稿を取得し、ストーリーごとにグループ化

    Returns:
        list of dict: [{'story_id': '001', 'story_title': '鈴の音', 'posts': [...]}, ...]
    """
    stories = {}

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_id = row.get('id', '').strip()
            datetime_str = row.get('datetime', '').strip()
            text = row.get('text', '').strip()
            status = row.get('status', '').strip()
            subcategory = row.get('subcategory', '').strip()

            if not csv_id or not datetime_str or not text or status != 'pending':
                continue

            # 日付チェック
            scheduled_at = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            if scheduled_at.date() != target_date:
                continue

            # ストーリーIDを抽出（例: 001_01 → 001）
            story_id = csv_id.split('_')[0]

            if story_id not in stories:
                stories[story_id] = {
                    'story_id': story_id,
                    'story_title': subcategory,
                    'posts': []
                }

            stories[story_id]['posts'].append({
                'csv_id': csv_id,
                'scheduled_at': scheduled_at,
                'text': text,
                'subcategory': subcategory
            })

    # 各ストーリーの投稿をIDでソート
    for story in stories.values():
        story['posts'].sort(key=lambda x: x['csv_id'])

    return list(stories.values())


def create_threads_post(text, reply_to_id=None):
    """Threads APIで投稿を作成（スレッド対応）"""
    if DRY_RUN:
        if reply_to_id:
            print(f"  → [ドライラン] スレッド投稿をシミュレート中... (返信先: {reply_to_id})")
        else:
            print(f"  → [ドライラン] メイン投稿をシミュレート中...")
        time.sleep(0.1)
        fake_post_id = f"dry_run_{int(time.time() * 1000)}"
        print(f"  ✓ [ドライラン] 投稿成功（シミュレート）！ (ID: {fake_post_id})")
        return fake_post_id

    try:
        # コンテナ作成
        create_url = f'{API_BASE_URL}/{USER_ID}/threads'
        create_params = {'access_token': ACCESS_TOKEN}
        create_data = {
            'media_type': 'TEXT',
            'text': text
        }

        if reply_to_id:
            create_data['reply_to_id'] = reply_to_id
            print(f"  → スレッドコンテナ作成中... (返信先: {reply_to_id})")
        else:
            print(f"  → メイン投稿コンテナ作成中...")

        create_response = requests.post(create_url, params=create_params, data=create_data)
        create_response.raise_for_status()
        container_id = create_response.json().get('id')

        if not container_id:
            print(f"  ✗ コンテナIDの取得に失敗")
            return None

        # 投稿公開
        publish_url = f'{API_BASE_URL}/{USER_ID}/threads_publish'
        publish_params = {'access_token': ACCESS_TOKEN}
        publish_data = {'creation_id': container_id}

        print(f"  → 投稿公開中...")
        publish_response = requests.post(publish_url, params=publish_params, data=publish_data)
        publish_response.raise_for_status()

        post_id = publish_response.json().get('id')
        if post_id:
            if reply_to_id:
                print(f"  ✓ スレッド投稿成功！ (ID: {post_id})")
            else:
                print(f"  ✓ メイン投稿成功！ (ID: {post_id})")
            return post_id
        else:
            print(f"  ✗ 投稿IDの取得に失敗")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  ✗ API エラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  ✗ エラー詳細: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"  ✗ レスポンス: {e.response.text[:200]}")
        return None


def post_story_as_thread(story):
    """1つのストーリーをスレッド形式で投稿"""
    print(f"\n" + "=" * 80)
    print(f"📚 ストーリー投稿: {story['story_title']} (ID: {story['story_id']})")
    print(f"投稿数: {len(story['posts'])}件")
    print("=" * 80)

    # メイン投稿（1投稿目）
    first_post = story['posts'][0]
    print(f"\n[1/{len(story['posts'])}] メイン投稿")
    print(f"ID: {first_post['csv_id']}")
    print(f"本文: {first_post['text'][:100]}...")

    main_post_id = create_threads_post(first_post['text'])

    if not main_post_id:
        print(f"✗ メイン投稿に失敗しました")
        return False

    # スレッド投稿（2投稿目以降）
    current_post_id = main_post_id

    for i, post in enumerate(story['posts'][1:], 2):
        print(f"\n[{i}/{len(story['posts'])}] スレッド投稿")
        print(f"ID: {post['csv_id']}")
        print(f"本文: {post['text'][:100]}...")

        # 前の投稿との間隔
        print(f"  ⏳ {POST_INTERVAL_SECONDS}秒待機...")
        time.sleep(POST_INTERVAL_SECONDS)

        # スレッド投稿
        thread_post_id = create_threads_post(post['text'], reply_to_id=current_post_id)

        if not thread_post_id:
            print(f"  ✗ スレッド投稿に失敗しました")
            return False

        current_post_id = thread_post_id

    print(f"\n✅ ストーリー「{story['story_title']}」の投稿完了！")
    print(f"   メイン投稿ID: {main_post_id}")
    print(f"   総投稿数: {len(story['posts'])}件")

    return True


def main():
    """メイン処理"""
    print("=" * 80)
    print("📅 スレッド形式投稿スクリプト")
    if DRY_RUN:
        print("   [ドライランモード - 実際には投稿されません]")
    print("=" * 80)

    # 対象日付を決定
    if len(sys.argv) > 1 and sys.argv[1] != '--dry-run':
        target_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    else:
        target_date = datetime.now(JST).date()

    print(f"\n対象日付: {target_date}")

    # CSVからストーリーを取得
    csv_path = resolve_csv_path()
    print(f"CSV: {csv_path}")

    stories = get_story_posts_for_date(csv_path, target_date)

    print(f"\n📊 投稿対象ストーリー: {len(stories)}件")

    if not stories:
        print("\n✓ 投稿するストーリーがありません")
        return

    # ストーリー一覧を表示
    print("\nストーリー一覧:")
    for i, story in enumerate(stories, 1):
        print(f"  {i}. [{story['story_id']}] {story['story_title']} - {len(story['posts'])}投稿")

    # 各ストーリーを投稿
    success_count = 0
    fail_count = 0

    for i, story in enumerate(stories, 1):
        if post_story_as_thread(story):
            success_count += 1
        else:
            fail_count += 1

        # 次のストーリーまで待機（最後のストーリー以外）
        if i < len(stories):
            wait_time = 60  # ストーリー間は1分待機
            if DRY_RUN:
                wait_time = 1
            print(f"\n⏳ 次のストーリーまで {wait_time}秒待機...")
            time.sleep(wait_time)

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 投稿完了")
    print("=" * 80)
    print(f"成功: {success_count} ストーリー")
    print(f"失敗: {fail_count} ストーリー")
    print("\n✅ 処理完了")


if __name__ == '__main__':
    main()
