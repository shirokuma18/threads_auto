#!/usr/bin/env python3
"""
Threads シンプル投稿スケジューラ

仕組み:
1. .last_posted_at から前回実行時刻を読む
2. posts_schedule.csv から scheduled_at が (last_posted_at, now] の範囲を取得
3. その範囲の投稿を順番に投稿（一定間隔を空ける）
4. 投稿完了後、現在時刻を .last_posted_at に保存

メリット:
- posted_history.csv 不要
- threads.db 不要
- CSVから削除不要（すべての投稿がマスターデータとして残る）
- 冪等性がある（何度実行しても同じ結果）
"""

import csv
import time
import requests
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv(override=True)

# Threads API設定
API_BASE_URL = 'https://graph.threads.net/v1.0'
ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
USER_ID = os.getenv('THREADS_USER_ID')

# JST タイムゾーン
JST = timezone(timedelta(hours=9))

# 設定
LAST_POSTED_FILE = '.last_posted_at'
POST_INTERVAL_SECONDS = 60  # 投稿間隔（秒）
DRY_RUN = '--dry-run' in sys.argv  # ドライランモード

# ドライランモード時は間隔を短縮
if DRY_RUN:
    POST_INTERVAL_SECONDS = 0.1


def get_last_posted_at():
    """前回投稿時刻を取得（JST）"""
    if not os.path.exists(LAST_POSTED_FILE):
        # 初回実行時は現在時刻の少し前を返す（直近の投稿を取得するため）
        return datetime.now(JST) - timedelta(hours=24)

    with open(LAST_POSTED_FILE, 'r') as f:
        timestamp_str = f.read().strip()
        # ISO形式で保存されているので読み込み
        return datetime.fromisoformat(timestamp_str)


def save_last_posted_at(dt):
    """最新投稿時刻を保存（JST）"""
    with open(LAST_POSTED_FILE, 'w') as f:
        # ISO形式で保存
        f.write(dt.isoformat())
    print(f"✓ 最終投稿時刻を保存: {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def get_posts_to_publish(csv_file, after_time, before_time):
    """投稿すべき投稿を取得"""
    posts = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_id = row.get('id', '').strip()
            datetime_str = row.get('datetime', '').strip()
            text = row.get('text', '').strip()
            thread_text = row.get('thread_text', '').strip() or None

            if not csv_id or not datetime_str or not text:
                continue

            # scheduled_at をパース（タイムゾーン情報なし = JST として扱う）
            scheduled_at = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            scheduled_at = scheduled_at.replace(tzinfo=JST)

            # (after_time, before_time] の範囲内かチェック
            if after_time < scheduled_at <= before_time:
                posts.append({
                    'csv_id': csv_id,
                    'scheduled_at': scheduled_at,
                    'text': text,
                    'thread_text': thread_text
                })

    # 予定時刻順にソート
    posts.sort(key=lambda x: x['scheduled_at'])
    return posts


def create_threads_post(text, reply_to_id=None):
    """Threads APIで投稿を作成"""
    # ドライランモード
    if DRY_RUN:
        if reply_to_id:
            print(f"  → [ドライラン] スレッド投稿をシミュレート中... (返信先: {reply_to_id})")
        else:
            print(f"  → [ドライラン] 投稿をシミュレート中...")
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

        if reply_to_id:
            create_data['reply_to_id'] = reply_to_id
            print(f"  → スレッドコンテナ作成中... (返信先: {reply_to_id})")
        else:
            print(f"  → コンテナ作成中...")

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
    print("📅 Threads シンプル投稿スケジューラ")
    if DRY_RUN:
        print("   [ドライランモード - 実際には投稿されません]")
    print("=" * 70)

    # 現在時刻（JST）
    now = datetime.now(JST)
    print(f"\n現在時刻: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # 前回投稿時刻を取得
    last_posted_at = get_last_posted_at()
    print(f"前回実行: {last_posted_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # 投稿すべき投稿を取得
    posts_to_publish = get_posts_to_publish('posts_schedule.csv', last_posted_at, now)

    print(f"\n📊 投稿対象: {len(posts_to_publish)} 件")

    if not posts_to_publish:
        print("\n✓ 投稿する投稿がありません")
        # 実行時刻だけ更新
        save_last_posted_at(now)
        return

    # 投稿リストを表示
    print("\n投稿予定:")
    for i, post in enumerate(posts_to_publish, 1):
        preview = post['text'][:50].replace('\n', ' ')
        print(f"  {i}. [{post['csv_id']}] {post['scheduled_at'].strftime('%Y-%m-%d %H:%M')} - {preview}...")

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

        # メイン投稿
        threads_post_id = create_threads_post(post['text'])

        if threads_post_id:
            # スレッド投稿がある場合
            if post['thread_text']:
                print(f"  → スレッド投稿を作成中...")
                time.sleep(2)
                thread_post_id = create_threads_post(post['thread_text'], reply_to_id=threads_post_id)
                if not thread_post_id:
                    print(f"  ⚠️  スレッド投稿に失敗しましたが、メイン投稿は成功")

            success_count += 1

            # 次の投稿まで待機（最後の投稿以外）
            if i < len(posts_to_publish):
                print(f"\n⏳ 次の投稿まで {POST_INTERVAL_SECONDS} 秒待機...")
                time.sleep(POST_INTERVAL_SECONDS)
        else:
            fail_count += 1
            print(f"  ✗ 投稿に失敗しました")

    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 投稿完了")
    print("=" * 70)
    print(f"成功: {success_count} 件")
    print(f"失敗: {fail_count} 件")

    # 最終投稿時刻を保存
    if not DRY_RUN:
        save_last_posted_at(now)
    else:
        print(f"\n[ドライラン] 最終投稿時刻の保存をスキップ: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("\n✅ 処理完了")


if __name__ == '__main__':
    main()
