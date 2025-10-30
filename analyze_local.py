#!/usr/bin/env python3
"""
ローカル分析スクリプト

posted_history.csv から投稿IDを取得し、
Threads API で詳細な分析データを取得します。

結果はローカルに保存され、リポジトリにはpushされません。
"""

import csv
import requests
import json
import os
from datetime import datetime
from collections import defaultdict

# 設定
ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
USER_ID = os.getenv('THREADS_USER_ID')
API_BASE_URL = 'https://graph.threads.net/v1.0'

# 出力ファイル（.gitignore に含まれている）
ANALYSIS_FILE = 'analysis_results.json'
REPORT_FILE = 'analysis_report.md'


def get_user_posts():
    """ユーザーの投稿一覧を取得"""
    url = f'{API_BASE_URL}/{USER_ID}/threads'
    params = {
        'fields': 'id,text,timestamp,media_type,permalink',
        'access_token': ACCESS_TOKEN,
        'limit': 100
    }

    print("📡 投稿一覧を取得中...")
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    posts = data.get('data', [])
    print(f"✅ {len(posts)} 件の投稿を取得")

    return posts


def get_post_insights(post_id):
    """投稿の詳細な分析データを取得"""
    url = f'{API_BASE_URL}/{post_id}/insights'
    params = {
        'metric': 'views,likes,replies,reposts,quotes,shares',
        'access_token': ACCESS_TOKEN
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        insights = {}
        for metric in data.get('data', []):
            insights[metric['name']] = metric['values'][0]['value']

        return insights
    except Exception as e:
        print(f"  ⚠️  分析データ取得エラー: {e}")
        return {}


def load_posted_history():
    """posted_history.csv から投稿済みIDを取得"""
    posted_ids = []
    with open('posted_history.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            posted_ids.append({
                'csv_id': row['csv_id'],
                'posted_at': row['posted_at']
            })

    print(f"📋 投稿履歴: {len(posted_ids)} 件")
    return posted_ids


def load_posts_schedule():
    """posts_schedule.csv からカテゴリ情報を取得"""
    categories = {}
    if os.path.exists('posts_schedule.csv'):
        with open('posts_schedule.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                categories[row['id']] = row.get('category', '未分類')

    return categories


def analyze_posts():
    """投稿を分析"""
    print("=" * 70)
    print("Threads 投稿分析（ローカル実行）")
    print("=" * 70)

    # 1. 投稿履歴を読み込み
    posted_history = load_posted_history()

    # 2. カテゴリ情報を読み込み
    categories = load_posts_schedule()

    # 3. Threads API から投稿一覧を取得
    posts = get_user_posts()

    # 4. 各投稿の詳細データを取得
    print("\n📊 各投稿の分析データを取得中...\n")

    analysis_results = []

    for i, post in enumerate(posts[:20]):  # 最新20件を分析
        post_id = post['id']
        text_preview = post.get('text', '')[:50]
        timestamp = post.get('timestamp', '')

        print(f"[{i+1}/20] {text_preview}...")

        # 分析データを取得
        insights = get_post_insights(post_id)

        result = {
            'post_id': post_id,
            'text': post.get('text', ''),
            'timestamp': timestamp,
            'permalink': post.get('permalink', ''),
            'views': insights.get('views', 0),
            'likes': insights.get('likes', 0),
            'replies': insights.get('replies', 0),
            'reposts': insights.get('reposts', 0),
            'quotes': insights.get('quotes', 0),
            'shares': insights.get('shares', 0),
            'engagement_rate': 0
        }

        # エンゲージメント率を計算
        if result['views'] > 0:
            total_engagement = result['likes'] + result['replies'] + result['reposts']
            result['engagement_rate'] = (total_engagement / result['views']) * 100

        analysis_results.append(result)

    # 5. 結果をローカルに保存
    print(f"\n💾 分析結果を保存中: {ANALYSIS_FILE}")

    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'total_posts': len(analysis_results),
            'results': analysis_results
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 保存完了: {ANALYSIS_FILE}")

    # 6. レポートを生成
    generate_report(analysis_results)

    return analysis_results


def generate_report(results):
    """分析レポートを生成"""
    print(f"\n📝 レポートを生成中: {REPORT_FILE}")

    # ソート: エンゲージメント率順
    sorted_by_engagement = sorted(results, key=lambda x: x['engagement_rate'], reverse=True)

    # ソート: いいね数順
    sorted_by_likes = sorted(results, key=lambda x: x['likes'], reverse=True)

    # レポート作成
    report = []
    report.append("# 📊 Threads 投稿分析レポート\n")
    report.append(f"**分析日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**分析件数:** {len(results)} 件\n")
    report.append("\n---\n")

    # サマリー
    total_views = sum(r['views'] for r in results)
    total_likes = sum(r['likes'] for r in results)
    total_replies = sum(r['replies'] for r in results)
    avg_engagement = sum(r['engagement_rate'] for r in results) / len(results) if results else 0

    report.append("## 📈 サマリー\n")
    report.append(f"- **合計ビュー数:** {total_views:,}\n")
    report.append(f"- **合計いいね数:** {total_likes:,}\n")
    report.append(f"- **合計リプライ数:** {total_replies:,}\n")
    report.append(f"- **平均エンゲージメント率:** {avg_engagement:.2f}%\n")
    report.append("\n---\n")

    # エンゲージメント率 TOP 5
    report.append("## 🔥 エンゲージメント率 TOP 5\n")
    for i, post in enumerate(sorted_by_engagement[:5], 1):
        report.append(f"### {i}. エンゲージメント率: {post['engagement_rate']:.2f}%\n")
        report.append(f"- **投稿内容:** {post['text'][:100]}...\n")
        report.append(f"- **ビュー数:** {post['views']:,}\n")
        report.append(f"- **いいね数:** {post['likes']:,}\n")
        report.append(f"- **リプライ数:** {post['replies']:,}\n")
        report.append(f"- **リンク:** {post['permalink']}\n")
        report.append("\n")

    report.append("---\n")

    # いいね数 TOP 5
    report.append("## ❤️ いいね数 TOP 5\n")
    for i, post in enumerate(sorted_by_likes[:5], 1):
        report.append(f"### {i}. いいね数: {post['likes']:,}\n")
        report.append(f"- **投稿内容:** {post['text'][:100]}...\n")
        report.append(f"- **ビュー数:** {post['views']:,}\n")
        report.append(f"- **エンゲージメント率:** {post['engagement_rate']:.2f}%\n")
        report.append(f"- **リンク:** {post['permalink']}\n")
        report.append("\n")

    report.append("---\n")

    # 改善ポイント
    report.append("## 💡 改善ポイント\n")
    report.append("分析結果から以下のポイントを参考に、新しい投稿を作成してください：\n\n")

    best_post = sorted_by_engagement[0] if sorted_by_engagement else None
    if best_post:
        report.append(f"1. **最も反応が良かった投稿の特徴を分析**\n")
        report.append(f"   - テーマ、トーン、文章構成を確認\n")
        report.append(f"   - エンゲージメント率: {best_post['engagement_rate']:.2f}%\n\n")

    avg_views = total_views / len(results) if results else 0
    report.append(f"2. **平均ビュー数を上回る投稿を増やす**\n")
    report.append(f"   - 現在の平均: {avg_views:,.0f} ビュー\n")
    report.append(f"   - 目標: {avg_views * 1.5:,.0f} ビュー以上\n\n")

    report.append(f"3. **エンゲージメント率を向上させる**\n")
    report.append(f"   - 現在の平均: {avg_engagement:.2f}%\n")
    report.append(f"   - 目標: {avg_engagement * 1.2:.2f}% 以上\n\n")

    # ファイルに保存
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"✅ レポート生成完了: {REPORT_FILE}")
    print("\n📖 レポートを開く:")
    print(f"  open {REPORT_FILE}")


def main():
    if not ACCESS_TOKEN or not USER_ID:
        print("❌ エラー: 環境変数が設定されていません")
        print("\n.envファイルを読み込んでください:")
        print("  export $(cat .env | xargs)")
        print("  python3 analyze_local.py")
        return

    try:
        results = analyze_posts()

        print("\n" + "=" * 70)
        print("✅ 分析完了！")
        print("=" * 70)
        print(f"\n結果:")
        print(f"  - {ANALYSIS_FILE} (JSON形式)")
        print(f"  - {REPORT_FILE} (レポート)")
        print("\nこれらのファイルはローカルのみに保存され、")
        print("リポジトリにはpushされません（.gitignore設定済み）")
        print("\n次のステップ:")
        print("  1. レポートを確認")
        print("  2. 反応の良かった投稿を参考に新しい投稿を作成")
        print("  3. posts_schedule.csv に追加")
        print("  4. git push")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
