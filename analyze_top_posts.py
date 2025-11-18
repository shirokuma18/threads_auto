#!/usr/bin/env python3
"""
最近の投稿のインサイトを分析して、インプレッションが高い投稿を特定
"""

import os
import requests
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


def get_user_posts(limit=100):
    """ユーザーの投稿一覧を取得"""
    try:
        url = f'{API_BASE_URL}/{USER_ID}/threads'
        params = {
            'fields': 'id,text,timestamp,permalink',
            'limit': limit,
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


def analyze_top_posts():
    """最近の投稿を分析してインプレッションが高いものを特定"""
    print("=" * 80)
    print("📊 最近の投稿のインサイト分析")
    print("=" * 80)

    # 投稿一覧を取得
    print("\n投稿を取得中...")
    posts = get_user_posts(limit=100)
    print(f"取得した投稿数: {len(posts)}件")

    if not posts:
        print("投稿が見つかりませんでした。")
        return

    # 各投稿のインサイトを取得
    print("\nインサイトを取得中...")
    posts_with_insights = []

    for i, post in enumerate(posts, 1):
        post_id = post.get('id')
        text = post.get('text', '')
        timestamp_str = post.get('timestamp', '')
        permalink = post.get('permalink', '')

        # タイムスタンプをJSTに変換
        if timestamp_str:
            if timestamp_str.endswith('+0000'):
                timestamp_str = timestamp_str.replace('+0000', '+00:00')
            elif timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str.replace('Z', '+00:00')
            post_time = datetime.fromisoformat(timestamp_str)
            post_time_jst = post_time.astimezone(JST)
        else:
            post_time_jst = None

        # インサイトを取得
        insights = get_post_insights(post_id)

        posts_with_insights.append({
            'id': post_id,
            'text': text,
            'timestamp': post_time_jst,
            'permalink': permalink,
            'views': insights.get('views', 0),
            'likes': insights.get('likes', 0),
            'replies': insights.get('replies', 0),
            'reposts': insights.get('reposts', 0),
            'quotes': insights.get('quotes', 0),
            'engagement': insights.get('likes', 0) + insights.get('replies', 0) +
                         insights.get('reposts', 0) + insights.get('quotes', 0)
        })

        if i % 10 == 0:
            print(f"  {i}/{len(posts)}件取得完了...")

    print(f"\n✅ インサイト取得完了: {len(posts_with_insights)}件")

    # インプレッション数でソート
    posts_with_insights.sort(key=lambda x: x['views'], reverse=True)

    # トップ10を表示
    print("\n" + "=" * 80)
    print("🏆 インプレッションが高い投稿 TOP 10")
    print("=" * 80)

    for i, post in enumerate(posts_with_insights[:10], 1):
        timestamp_str = post['timestamp'].strftime('%Y-%m-%d %H:%M') if post['timestamp'] else 'N/A'
        text_preview = post['text'][:60].replace('\n', ' ')

        print(f"\n【{i}位】")
        print(f"📅 日時: {timestamp_str}")
        print(f"👁  インプレッション: {post['views']:,}")
        print(f"❤️  いいね: {post['likes']}")
        print(f"💬 リプライ: {post['replies']}")
        print(f"🔄 リポスト: {post['reposts']}")
        print(f"💭 引用: {post['quotes']}")
        print(f"🎯 総エンゲージメント: {post['engagement']}")
        print(f"📝 本文: {text_preview}...")
        print(f"🔗 URL: {post['permalink']}")

    # エンゲージメント率でもソート
    posts_with_insights.sort(key=lambda x: x['engagement'] / max(x['views'], 1), reverse=True)

    print("\n" + "=" * 80)
    print("🎯 エンゲージメント率が高い投稿 TOP 5")
    print("=" * 80)

    for i, post in enumerate(posts_with_insights[:5], 1):
        if post['views'] > 0:
            engagement_rate = (post['engagement'] / post['views']) * 100
            timestamp_str = post['timestamp'].strftime('%Y-%m-%d %H:%M') if post['timestamp'] else 'N/A'
            text_preview = post['text'][:60].replace('\n', ' ')

            print(f"\n【{i}位】")
            print(f"📅 日時: {timestamp_str}")
            print(f"📊 エンゲージメント率: {engagement_rate:.2f}%")
            print(f"👁  インプレッション: {post['views']:,}")
            print(f"🎯 総エンゲージメント: {post['engagement']}")
            print(f"📝 本文: {text_preview}...")
            print(f"🔗 URL: {post['permalink']}")

    # サマリー統計
    total_views = sum(p['views'] for p in posts_with_insights)
    total_likes = sum(p['likes'] for p in posts_with_insights)
    total_engagement = sum(p['engagement'] for p in posts_with_insights)
    avg_views = total_views / len(posts_with_insights) if posts_with_insights else 0
    avg_engagement = total_engagement / len(posts_with_insights) if posts_with_insights else 0

    print("\n" + "=" * 80)
    print("📈 全体サマリー")
    print("=" * 80)
    print(f"投稿数: {len(posts_with_insights)}件")
    print(f"総インプレッション: {total_views:,}")
    print(f"総いいね: {total_likes:,}")
    print(f"総エンゲージメント: {total_engagement:,}")
    print(f"平均インプレッション: {avg_views:.1f}")
    print(f"平均エンゲージメント: {avg_engagement:.1f}")
    print(f"平均エンゲージメント率: {(avg_engagement / avg_views * 100 if avg_views > 0 else 0):.2f}%")


if __name__ == '__main__':
    analyze_top_posts()
