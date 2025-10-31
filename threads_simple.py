#!/usr/bin/env python3
"""
Threads シンプル投稿スケジューラ + Daily Report

仕組み（新アーキテクチャ）:
1. 現在時刻から該当するスケジュールターム（8, 12, 15, 18, 21, 23時）を判定
2. Threads APIから最近の投稿を取得
3. そのタームの投稿で未投稿のものだけを取得
4. 投稿実行（リポジトリへの影響なし）

コマンド:
- python3 threads_simple.py          投稿実行
- python3 threads_simple.py --dry-run  ドライラン
- python3 threads_simple.py daily-report  毎朝の成果報告を投稿

メリット:
- リポジトリへの影響ゼロ（ファイル書き込みなし）
- ブランチ分け不要（mainのみ）
- 冪等性がある（何度実行しても同じ結果）
- 重複投稿防止（API照合）
"""

import csv
import time
import requests
import json
import os
import sys
import random
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
SCHEDULE_HOURS = [8, 10, 12, 15, 17, 19, 20, 21, 22, 23, 24]  # スケジュール時刻（JST）
POST_INTERVAL_SECONDS = 360  # 投稿間隔（秒、6分）
MAX_POSTS_PER_RUN = 5  # 1回の実行での最大投稿数（12枠 × 5投稿 = 60投稿/日）
DRY_RUN = '--dry-run' in sys.argv  # ドライランモード

# ドライランモード時は間隔を短縮
if DRY_RUN:
    POST_INTERVAL_SECONDS = 0.1


def get_current_schedule_hour(now_hour):
    """現在時刻から該当するスケジュール時刻（ターム）を取得

    GitHub Actionsのcronは最大15分程度ずれるため、ターム管理で対応
    新スケジュール: 8, 10, 12, 15, 17, 19, 20, 21, 22, 23, 24(0)時
    """
    # 24時(0時)のターム: 0:00-7:59 (深夜～早朝)
    if now_hour >= 0 and now_hour < 8:
        return 24  # 24時として扱う（CSVでは24:00と記録）
    # 23時のターム: 23:00-23:59
    elif now_hour >= 23:
        return 23
    # 22時のターム: 22:00-22:59
    elif now_hour >= 22:
        return 22
    # 21時のターム: 21:00-21:59
    elif now_hour >= 21:
        return 21
    # 20時のターム: 20:00-20:59
    elif now_hour >= 20:
        return 20
    # 19時のターム: 19:00-19:59
    elif now_hour >= 19:
        return 19
    # 17時のターム: 17:00-18:59
    elif now_hour >= 17:
        return 17
    # 15時のターム: 15:00-16:59
    elif now_hour >= 15:
        return 15
    # 12時のターム: 12:00-14:59
    elif now_hour >= 12:
        return 12
    # 10時のターム: 10:00-11:59
    elif now_hour >= 10:
        return 10
    # 8時のターム: 8:00-9:59
    else:
        return 8


def get_recent_posts_from_api():
    """Threads APIから最近の投稿を取得（重複チェック用）"""
    try:
        url = f'{API_BASE_URL}/{USER_ID}/threads'
        params = {
            'fields': 'id,text,timestamp',
            'limit': 30,  # 当日分をカバー
            'access_token': ACCESS_TOKEN
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        print(f"⚠️  API投稿取得エラー: {e}")
        return []


def is_post_already_published(post_text, recent_posts):
    """指定の投稿が既に投稿済みか確認（テキストの先頭100文字で照合）"""
    post_preview = post_text[:100].strip()

    for api_post in recent_posts:
        api_text = api_post.get('text', '').strip()
        # 先頭100文字が一致すれば同じ投稿と判定
        if api_text[:100] == post_preview:
            return True

    return False


def get_posts_to_publish(csv_file, target_date, schedule_hour, max_posts=None):
    """指定日時のスケジュール時刻の未投稿分を取得"""
    # APIから最近の投稿を取得（ここで1回だけ）
    recent_posts = get_recent_posts_from_api()

    posts = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_id = row.get('id', '').strip()
            datetime_str = row.get('datetime', '').strip()
            text = row.get('text', '').strip()
            thread_text = row.get('thread_text', '').strip() or None
            category = row.get('category', '').strip()
            subcategory = row.get('subcategory', '').strip()

            if not csv_id or not datetime_str or not text:
                continue

            # scheduled_at をパース（タイムゾーン情報なし = JST として扱う）
            scheduled_at = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            scheduled_at = scheduled_at.replace(tzinfo=JST)

            # トピックリストを構築
            topics = []
            if category:
                topics.append(category)
            if subcategory:
                topics.append(subcategory)

            # 今日の日付 & そのスケジュール時刻の投稿のみ
            if scheduled_at.date() == target_date and scheduled_at.hour == schedule_hour:
                # 既に投稿済みかチェック
                if not is_post_already_published(text, recent_posts):
                    posts.append({
                        'csv_id': csv_id,
                        'scheduled_at': scheduled_at,
                        'text': text,
                        'thread_text': thread_text,
                        'topics': topics
                    })

    # 予定時刻順にソート
    posts.sort(key=lambda x: x['scheduled_at'])

    # 投稿数制限（スパム対策）
    if max_posts and len(posts) > max_posts:
        print(f"\n⚠️  投稿数制限: {len(posts)}件 → {max_posts}件に制限（スパム対策）")
        posts = posts[:max_posts]

    return posts


def create_threads_post(text, reply_to_id=None, topics=None):
    """Threads APIで投稿を作成"""
    # ドライランモード
    if DRY_RUN:
        if reply_to_id:
            print(f"  → [ドライラン] スレッド投稿をシミュレート中... (返信先: {reply_to_id})")
        else:
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

        # トピックを追加（空でない場合）
        # Threads APIは1つのトピックのみサポート（topic_tag）
        if topics and len(topics) > 0:
            create_data['topic_tag'] = topics[0]  # 最初のトピックのみ使用

        if reply_to_id:
            create_data['reply_to_id'] = reply_to_id
            print(f"  → スレッドコンテナ作成中... (返信先: {reply_to_id})")
        else:
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

    # 該当するスケジュール時刻を取得
    schedule_hour = get_current_schedule_hour(now.hour)
    print(f"該当スケジュール: {schedule_hour}:00 のターム")

    # 投稿すべき投稿を取得（スパム対策: 最大4件）
    posts_to_publish = get_posts_to_publish('posts_schedule.csv', now.date(), schedule_hour, max_posts=MAX_POSTS_PER_RUN)

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

        # メイン投稿
        threads_post_id = create_threads_post(post['text'], topics=post.get('topics'))

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
    print("\n✅ 処理完了")


def get_user_posts():
    """ユーザーの投稿一覧を取得"""
    try:
        url = f'{API_BASE_URL}/{USER_ID}/threads'
        params = {
            'fields': 'id,text,timestamp,permalink',
            'limit': 100,
            'access_token': ACCESS_TOKEN
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        print(f"✗ 投稿一覧取得エラー: {e}")
        return []


def get_post_insights(post_id):
    """投稿のインサイトを取得"""
    try:
        url = f'{API_BASE_URL}/{post_id}/insights'
        params = {
            'metric': 'views,likes,replies,reposts,quotes',
            'access_token': ACCESS_TOKEN
        }
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json().get('data', [])
        insights = {}
        for item in data:
            metric_name = item.get('name')
            value = item.get('values', [{}])[0].get('value', 0)
            insights[metric_name] = value

        return insights
    except Exception as e:
        return {'views': 0, 'likes': 0, 'replies': 0, 'reposts': 0, 'quotes': 0}


def get_followers_count():
    """フォロワー数を取得"""
    try:
        url = f'{API_BASE_URL}/{USER_ID}/threads_insights'
        params = {
            'metric': 'followers_count',
            'access_token': ACCESS_TOKEN
        }
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json().get('data', [])
        for item in data:
            if item.get('name') == 'followers_count':
                return item.get('values', [{}])[0].get('value', 0)
        return 0
    except Exception as e:
        print(f"✗ フォロワー数取得エラー: {e}")
        return 0


def generate_daily_report():
    """毎朝の成果報告を生成・投稿"""
    print("=" * 70)
    print("📊 Daily Report Generator")
    print("=" * 70)

    # 運用開始日
    start_date = datetime(2025, 10, 29, tzinfo=JST)
    today = datetime.now(JST)
    days_running = (today - start_date).days

    print(f"\n運用開始日: {start_date.strftime('%Y-%m-%d')}")
    print(f"経過日数: {days_running}日")

    # 昨日のデータを取得
    yesterday = today - timedelta(days=1)
    yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

    print(f"\n昨日の範囲: {yesterday_start.strftime('%Y-%m-%d %H:%M')} - {yesterday_end.strftime('%Y-%m-%d %H:%M')}")

    # 投稿一覧を取得
    posts = get_user_posts()

    # 昨日の投稿を抽出
    yesterday_posts = []
    for post in posts:
        timestamp_str = post.get('timestamp', '')
        if timestamp_str:
            # ISO 8601形式をパース
            post_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            post_time_jst = post_time.astimezone(JST)

            if yesterday_start <= post_time_jst <= yesterday_end:
                yesterday_posts.append(post)

    print(f"昨日の投稿数: {len(yesterday_posts)}件")

    # インサイト集計
    total_views = 0
    total_likes = 0

    for post in yesterday_posts:
        post_id = post.get('id')
        insights = get_post_insights(post_id)
        total_views += insights.get('views', 0)
        total_likes += insights.get('likes', 0)

    avg_likes = total_likes / len(yesterday_posts) if yesterday_posts else 0

    # フォロワー数
    followers_count = get_followers_count()

    print(f"\n📊 集計結果:")
    print(f"  投稿数: {len(yesterday_posts)}投稿")
    print(f"  いいね: {total_likes}件（平均{avg_likes:.1f}）")
    print(f"  インプレッション: {total_views:,}回")
    print(f"  フォロワー: {followers_count}人")

    # モチベーションメッセージ
    motivation_messages = [
        "継続は力なり。今日も頑張ろう！",
        "小さな積み重ねが大きな成果に。",
        "毎日コツコツ、着実に成長中！",
        "焦らず、自分のペースで。",
        "今日も楽しく発信していこう！"
    ]
    motivation = random.choice(motivation_messages)

    # レポート本文を生成
    report_text = f"""おはよう☀️
運用開始して{days_running}日目の成果報告！

【投稿数】{len(yesterday_posts)}投稿
【いいね】{total_likes}件（平均{avg_likes:.1f}）
【インプレッション】{total_views:,}回
【フォロワー】{followers_count}人

{motivation}"""

    print(f"\n📝 レポート本文:")
    print(report_text)
    print()

    # 投稿
    if DRY_RUN:
        print("[ドライラン] 実際には投稿されません")
    else:
        print("📤 レポートを投稿中...")
        post_id = create_threads_post(report_text)
        if post_id:
            print(f"✅ レポート投稿成功！ (ID: {post_id})")
        else:
            print("✗ レポート投稿失敗")


if __name__ == '__main__':
    # コマンドライン引数チェック
    if len(sys.argv) > 1 and sys.argv[1] == 'daily-report':
        generate_daily_report()
    else:
        main()
