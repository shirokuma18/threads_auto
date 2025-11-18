#!/usr/bin/env python3
"""
1日3投稿スクリプト - シンプルな個別投稿

スケジュール: 8:00, 12:00, 19:00
各時刻に1投稿のみ
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
DRY_RUN = '--dry-run' in sys.argv


def resolve_csv_path():
    """CSVファイルのパスを解決"""
    csv_path = Path('data/posts_schedule.csv')
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    return str(csv_path)


def get_recent_posts_from_api():
    """Threads APIから最近の投稿を取得（重複チェック用）"""
    try:
        url = f'{API_BASE_URL}/{USER_ID}/threads'
        params = {
            'fields': 'id,text,timestamp',
            'limit': 30,
            'access_token': ACCESS_TOKEN
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        print(f"⚠️  API投稿取得エラー: {e}")
        return []


def is_post_already_published(post_text, recent_posts):
    """指定の投稿が既に投稿済みか確認"""
    post_preview = post_text[:100].strip()

    for api_post in recent_posts:
        api_text = api_post.get('text', '').strip()
        if api_text[:100] == post_preview:
            return True

    return False


def get_current_schedule_time(now_hour, now_minute):
    """現在時刻から該当するスケジュール時刻を取得

    スケジュール: 8:00, 12:00, 19:00
    ±15分の範囲で該当するタームを判定
    """
    schedule_times = [(8, 0), (12, 0), (19, 0)]

    current_minutes = now_hour * 60 + now_minute

    for schedule_hour, schedule_minute in schedule_times:
        schedule_minutes = schedule_hour * 60 + schedule_minute
        diff = abs(current_minutes - schedule_minutes)

        if diff <= 15:
            return (schedule_hour, schedule_minute)

    return None


def get_posts_to_publish(csv_file, target_date, schedule_time):
    """指定日時の未投稿分を取得"""
    if schedule_time is None:
        return []

    schedule_hour, schedule_minute = schedule_time

    # APIから最近の投稿を取得
    recent_posts = get_recent_posts_from_api()

    posts = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_id = row.get('id', '').strip()
            datetime_str = row.get('datetime', '').strip()
            text = row.get('text', '').strip()
            status = row.get('status', '').strip()
            category = row.get('category', '').strip()
            subcategory = row.get('subcategory', '').strip()

            if not csv_id or not datetime_str or not text or status != 'pending':
                continue

            # scheduled_at をパース
            scheduled_at = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            scheduled_at = scheduled_at.replace(tzinfo=JST)

            # トピックリストを構築
            topics = []
            if category:
                topics.append(category)
            if subcategory:
                topics.append(subcategory)

            # 今日の日付 & そのスケジュール時刻の投稿のみ
            if (scheduled_at.date() == target_date and
                scheduled_at.hour == schedule_hour and
                scheduled_at.minute == schedule_minute):
                # 既に投稿済みかチェック
                if not is_post_already_published(text, recent_posts):
                    posts.append({
                        'csv_id': csv_id,
                        'scheduled_at': scheduled_at,
                        'text': text,
                        'topics': topics
                    })

    # 予定時刻順にソート
    posts.sort(key=lambda x: x['scheduled_at'])

    # 最大1件のみ
    if len(posts) > 1:
        posts = posts[:1]

    return posts


def create_threads_post(text, topics=None):
    """Threads APIで投稿を作成"""
    if DRY_RUN:
        topic_info = f" トピック: {', '.join(topics)}" if topics else ""
        print(f"  → [ドライラン] 投稿をシミュレート中...{topic_info}")
        time.sleep(0.1)
        fake_post_id = f"dry_run_{int(time.time())}"
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

        # トピックを追加
        if topics and len(topics) > 0:
            create_data['topic_tag'] = topics[0]

        topic_info = f" [トピック: {', '.join(topics)}]" if topics else ""
        print(f"  → コンテナ作成中...{topic_info}")

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
            print(f"  ✓ 投稿成功！ (ID: {post_id})")
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


def main():
    """メイン処理"""
    print("=" * 70)
    print("📅 1日3投稿スクリプト")
    if DRY_RUN:
        print("   [ドライランモード - 実際には投稿されません]")
    print("=" * 70)

    # 現在時刻（JST）
    now = datetime.now(JST)
    print(f"\n現在時刻: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # 該当するスケジュール時刻を取得
    schedule_time = get_current_schedule_time(now.hour, now.minute)

    if schedule_time is None:
        print("該当スケジュール: なし（スケジュール時間外）")
        print("\n✓ スケジュール時間外です（8:00, 12:00, 19:00 のみ）")
        return

    schedule_hour, schedule_minute = schedule_time
    print(f"該当スケジュール: {schedule_hour}:{schedule_minute:02d}")

    # 投稿すべき投稿を取得
    csv_path = resolve_csv_path()
    print(f"CSV: {csv_path}")

    posts_to_publish = get_posts_to_publish(csv_path, now.date(), schedule_time)

    print(f"\n📊 投稿対象: {len(posts_to_publish)} 件")

    if not posts_to_publish:
        print("\n✓ 投稿する投稿がありません（全て投稿済み or 該当なし）")
        return

    # 投稿リストを表示
    print("\n投稿予定:")
    for i, post in enumerate(posts_to_publish, 1):
        preview = post['text'][:50].replace('\n', ' ')
        topic_info = f" [トピック: {', '.join(post['topics'])}]" if post.get('topics') else ""
        print(f"  {i}. [{post['csv_id']}] {post['scheduled_at'].strftime('%Y-%m-%d %H:%M')}{topic_info} - {preview}...")

    print("\n" + "=" * 70)
    print("📤 投稿を開始します")
    print("=" * 70)

    # 投稿を実行
    success_count = 0
    fail_count = 0

    for i, post in enumerate(posts_to_publish, 1):
        print(f"\n[{i}/{len(posts_to_publish)}] ID: {post['csv_id']}")
        print(f"予定時刻: {post['scheduled_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"本文: {post['text'][:100]}...")
        if post.get('topics'):
            print(f"トピック: {', '.join(post['topics'])}")

        # 投稿実行
        post_id = create_threads_post(post['text'], topics=post.get('topics'))

        if post_id:
            success_count += 1
        else:
            fail_count += 1

    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 投稿完了")
    print("=" * 70)
    print(f"成功: {success_count} 件")
    print(f"失敗: {fail_count} 件")
    print("\n✅ 処理完了")


if __name__ == '__main__':
    main()
