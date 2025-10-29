#!/usr/bin/env python3
"""
Threads API 予約投稿 + PDCA分析スクリプト
3日サイクルでPDCAを回すことに特化
"""

import csv
import time
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
import argparse

# ============================================
# 設定項目
# ============================================
ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN_HERE')
USER_ID = os.getenv('THREADS_USER_ID', 'YOUR_USER_ID_HERE')

# ファイルパス
CSV_FILE = os.getenv('CSV_FILE', 'posts_schedule.csv')
LOG_FILE = 'posted_log.json'
ANALYTICS_FILE = 'analytics_data.csv'
PDCA_REPORT_FILE = 'pdca_report.md'
COMPETITORS_FILE = 'competitors.csv'
COMPETITOR_ANALYTICS_FILE = 'competitor_analytics.csv'
COMPETITOR_REPORT_FILE = 'competitor_report.md'

# レート制限対策
MIN_INTERVAL_SECONDS = 3600  # 1時間

# ドライランモード
DRY_RUN = False

# ============================================
# Threads API
# ============================================
API_BASE_URL = 'https://graph.threads.net/v1.0'


def create_threads_post(text):
    """Threads APIで投稿を作成"""
    global DRY_RUN

    if DRY_RUN:
        print(f"  → [ドライラン] 投稿をシミュレート中...")
        print(f"  → [ドライラン] 実際には投稿されません")
        time.sleep(0.5)  # リアルな動作をシミュレート
        fake_post_id = f"dry_run_{int(time.time())}"
        print(f"  ✓ [ドライラン] 投稿成功（シミュレート）！ (ID: {fake_post_id})")
        return fake_post_id

    try:
        create_url = f'{API_BASE_URL}/{USER_ID}/threads'
        create_params = {
            'media_type': 'TEXT',
            'text': text,
            'access_token': ACCESS_TOKEN
        }

        print(f"  → コンテナ作成中...")
        create_response = requests.post(create_url, params=create_params)
        create_response.raise_for_status()
        container_id = create_response.json().get('id')

        if not container_id:
            print(f"  ✗ コンテナIDの取得に失敗")
            return None

        publish_url = f'{API_BASE_URL}/{USER_ID}/threads_publish'
        publish_params = {
            'creation_id': container_id,
            'access_token': ACCESS_TOKEN
        }

        print(f"  → 投稿公開中...")
        publish_response = requests.post(publish_url, params=publish_params)
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
        return None


def get_post_insights(post_id):
    """投稿の分析データを取得"""
    try:
        url = f'{API_BASE_URL}/{post_id}'
        params = {
            'fields': 'id,text,timestamp,permalink',
            'access_token': ACCESS_TOKEN
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        insights_url = f'{API_BASE_URL}/{post_id}/insights'
        insights_params = {
            'metric': 'views,likes,replies,reposts,quotes',
            'access_token': ACCESS_TOKEN
        }
        
        insights_response = requests.get(insights_url, params=insights_params)
        
        insights_data = {}
        if insights_response.status_code == 200:
            insights = insights_response.json().get('data', [])
            for metric in insights:
                insights_data[metric['name']] = metric.get('values', [{}])[0].get('value', 0)
        
        result = {
            'post_id': post_id,
            'text': data.get('text', ''),
            'timestamp': data.get('timestamp', ''),
            'permalink': data.get('permalink', ''),
            'views': insights_data.get('views', 0),
            'likes': insights_data.get('likes', 0),
            'replies': insights_data.get('replies', 0),
            'reposts': insights_data.get('reposts', 0),
            'quotes': insights_data.get('quotes', 0),
        }
        
        total_engagement = (
            result['likes'] + 
            result['replies'] + 
            result['reposts'] + 
            result['quotes']
        )
        result['engagement'] = total_engagement
        result['engagement_rate'] = (
            (total_engagement / result['views'] * 100) 
            if result['views'] > 0 else 0
        )
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"  ✗ 分析データ取得エラー: {e}")
        return None


# ============================================
# 競合分析機能
# ============================================

def extract_post_id_from_url(url):
    """
    Threads投稿URLから投稿IDを抽出

    Args:
        url: Threads投稿URL (例: https://www.threads.net/@username/post/ABC123...)

    Returns:
        投稿ID、またはNone
    """
    import re

    # URLのパターン: https://www.threads.net/@username/post/{POST_ID}
    pattern = r'threads\.net/@[^/]+/post/([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)

    if match:
        return match.group(1)

    return None


def load_competitor_posts():
    """競合投稿URLリストを読み込む"""
    posts = []
    try:
        with open(COMPETITORS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('post_url', '').strip()

                # コメント行をスキップ
                if url.startswith('#') or not url:
                    continue

                # URLから投稿IDを抽出
                post_id = extract_post_id_from_url(url)
                if post_id:
                    posts.append({
                        'post_id': post_id,
                        'url': url,
                        'category': row.get('category', ''),
                        'note': row.get('note', '')
                    })
                else:
                    print(f"警告: 無効なURL形式: {url}")

    except FileNotFoundError:
        print(f"警告: {COMPETITORS_FILE} が見つかりません")

    return posts


def get_thread_details(thread_id):
    """
    投稿の詳細情報を取得

    Args:
        thread_id: 投稿ID

    Returns:
        投稿の詳細情報
    """
    try:
        url = f'{API_BASE_URL}/{thread_id}'
        params = {
            'fields': 'id,text,timestamp,permalink,media_type,media_url,username',
            'access_token': ACCESS_TOKEN
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Threads APIでは公開エンゲージメント数の取得が制限されている可能性があるため、
        # 基本情報のみを取得
        result = {
            'thread_id': thread_id,
            'text': data.get('text', ''),
            'timestamp': data.get('timestamp', ''),
            'permalink': data.get('permalink', ''),
            'username': data.get('username', ''),
            'media_type': data.get('media_type', 'TEXT'),
            'char_count': len(data.get('text', ''))
        }

        # タイムスタンプから時間帯と曜日を抽出
        if result['timestamp']:
            posted_time = datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))
            result['posted_hour'] = posted_time.hour
            result['posted_day'] = posted_time.strftime('%A')
            result['posted_datetime'] = posted_time

        # 絵文字の有無
        text = result.get('text', '')
        result['has_emoji'] = any(ord(c) > 127 for c in text)

        return result

    except requests.exceptions.RequestException as e:
        print(f"  ✗ 投稿詳細取得エラー (ID: {thread_id}): {e}")
        return None


def save_competitor_analytics(analytics_data):
    """競合分析データをCSVに保存"""
    file_exists = os.path.exists(COMPETITOR_ANALYTICS_FILE)

    fieldnames = [
        'timestamp', 'competitor_username', 'thread_id', 'text',
        'posted_hour', 'posted_day', 'char_count', 'has_emoji',
        'media_type', 'permalink'
    ]

    with open(COMPETITOR_ANALYTICS_FILE, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            'timestamp': datetime.now().isoformat(),
            'competitor_username': analytics_data.get('username', ''),
            'thread_id': analytics_data.get('thread_id', ''),
            'text': analytics_data.get('text', '')[:200],
            'posted_hour': analytics_data.get('posted_hour', ''),
            'posted_day': analytics_data.get('posted_day', ''),
            'char_count': analytics_data.get('char_count', 0),
            'has_emoji': analytics_data.get('has_emoji', False),
            'media_type': analytics_data.get('media_type', 'TEXT'),
            'permalink': analytics_data.get('permalink', '')
        })


# ============================================
# CSV & ログ管理
# ============================================

def load_schedule():
    """CSVファイルから投稿スケジュールを読み込む"""
    posts = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posts.append({
                    'id': row.get('id', ''),
                    'datetime': row.get('datetime', ''),
                    'text': row.get('text', '')
                })
    except FileNotFoundError:
        print(f"警告: {CSV_FILE} が見つかりません")
    
    return posts


def load_posted_log():
    """投稿済みログを読み込む"""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_posted_log(log):
    """投稿済みログを保存"""
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def save_analytics_to_csv(analytics_data):
    """分析データをCSVに保存"""
    file_exists = os.path.exists(ANALYTICS_FILE)
    
    fieldnames = [
        'timestamp', 'post_id', 'text', 'posted_hour', 'posted_day',
        'views', 'likes', 'replies', 'reposts', 'quotes', 
        'engagement', 'engagement_rate', 'char_count', 'has_emoji'
    ]
    
    with open(ANALYTICS_FILE, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        # 投稿時間から時間帯と曜日を抽出
        posted_time = datetime.fromisoformat(analytics_data.get('timestamp', '').replace('Z', '+00:00'))
        
        # テキスト分析
        text = analytics_data.get('text', '')
        has_emoji = any(ord(c) > 127 for c in text)  # 簡易的な絵文字判定
        
        writer.writerow({
            'timestamp': datetime.now().isoformat(),
            'post_id': analytics_data.get('post_id', ''),
            'text': text[:100],
            'posted_hour': posted_time.hour,
            'posted_day': posted_time.strftime('%A'),
            'views': analytics_data.get('views', 0),
            'likes': analytics_data.get('likes', 0),
            'replies': analytics_data.get('replies', 0),
            'reposts': analytics_data.get('reposts', 0),
            'quotes': analytics_data.get('quotes', 0),
            'engagement': analytics_data.get('engagement', 0),
            'engagement_rate': f"{analytics_data.get('engagement_rate', 0):.2f}",
            'char_count': len(text),
            'has_emoji': has_emoji
        })


# ============================================
# PDCA分析機能
# ============================================

def generate_3day_report():
    """
    過去3日間のPDCAレポートを生成
    """
    print("\n" + "="*70)
    print("📊 過去3日間のPDCAレポートを生成中...")
    print("="*70)
    
    # 過去3日間の投稿を取得
    posted_log = load_posted_log()
    three_days_ago = datetime.now() - timedelta(days=3)
    
    recent_posts = []
    for post_id, post_data in posted_log.items():
        posted_at = datetime.fromisoformat(post_data.get('posted_at', ''))
        if posted_at >= three_days_ago and 'threads_post_id' in post_data:
            recent_posts.append({
                'csv_id': post_id,
                'threads_id': post_data['threads_post_id'],
                'text': post_data['text'],
                'posted_at': posted_at,
                'scheduled_at': post_data.get('scheduled_at', '')
            })
    
    if not recent_posts:
        print("⚠️  過去3日間の投稿がありません")
        return
    
    print(f"\n過去3日間の投稿数: {len(recent_posts)}件")
    print("分析データを取得中...\n")
    
    # 各投稿の分析データを取得
    analytics_results = []
    for i, post in enumerate(recent_posts, 1):
        print(f"[{i}/{len(recent_posts)}] 投稿 {post['csv_id']} を分析中...")
        analytics = get_post_insights(post['threads_id'])
        if analytics:
            analytics['posted_at'] = post['posted_at']
            analytics['csv_id'] = post['csv_id']
            analytics_results.append(analytics)
            save_analytics_to_csv(analytics)
            print(f"  ✓ 完了")
        time.sleep(2)  # レート制限対策
    
    if not analytics_results:
        print("⚠️  分析データを取得できませんでした")
        return
    
    # レポート生成
    report = generate_pdca_markdown(analytics_results)
    
    # ファイルに保存
    with open(PDCA_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ レポートを {PDCA_REPORT_FILE} に保存しました")
    print("\n" + report)
    
    return report


def generate_pdca_markdown(analytics_results):
    """
    PDCAレポートをMarkdown形式で生成
    """
    # 基本統計
    total_posts = len(analytics_results)
    total_views = sum(a['views'] for a in analytics_results)
    total_engagement = sum(a['engagement'] for a in analytics_results)
    avg_engagement_rate = sum(a['engagement_rate'] for a in analytics_results) / total_posts
    
    # 時間帯別分析
    hourly_performance = defaultdict(lambda: {'count': 0, 'engagement_rate': 0})
    for a in analytics_results:
        hour = a['posted_at'].hour
        hourly_performance[hour]['count'] += 1
        hourly_performance[hour]['engagement_rate'] += a['engagement_rate']
    
    for hour in hourly_performance:
        hourly_performance[hour]['avg_engagement_rate'] = (
            hourly_performance[hour]['engagement_rate'] / 
            hourly_performance[hour]['count']
        )
    
    # ベスト時間帯
    best_hours = sorted(
        hourly_performance.items(),
        key=lambda x: x[1]['avg_engagement_rate'],
        reverse=True
    )[:3]
    
    # トップパフォーマンス投稿
    top_posts = sorted(analytics_results, key=lambda x: x['engagement_rate'], reverse=True)[:3]
    worst_posts = sorted(analytics_results, key=lambda x: x['engagement_rate'])[:3]
    
    # 文字数分析
    char_counts = [len(a['text']) for a in analytics_results]
    avg_char_count = sum(char_counts) / len(char_counts) if char_counts else 0
    
    # 絵文字使用の効果
    with_emoji = [a for a in analytics_results if any(ord(c) > 127 for c in a['text'])]
    without_emoji = [a for a in analytics_results if not any(ord(c) > 127 for c in a['text'])]
    
    emoji_effect = ""
    if with_emoji and without_emoji:
        avg_with_emoji = sum(a['engagement_rate'] for a in with_emoji) / len(with_emoji)
        avg_without_emoji = sum(a['engagement_rate'] for a in without_emoji) / len(without_emoji)
        emoji_diff = avg_with_emoji - avg_without_emoji
        emoji_effect = f"絵文字あり: {avg_with_emoji:.2f}% vs なし: {avg_without_emoji:.2f}% (差: {emoji_diff:+.2f}%)"
    
    # Markdownレポート生成
    now = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    report = f"""# 📊 Threads PDCA レポート

**生成日時**: {now}  
**分析期間**: 過去3日間  
**投稿数**: {total_posts}件

---

## 📈 サマリー

| 指標 | 値 |
|------|-----|
| **総表示回数** | {total_views:,} |
| **総エンゲージメント** | {total_engagement:,} |
| **平均エンゲージメント率** | {avg_engagement_rate:.2f}% |
| **平均文字数** | {avg_char_count:.0f}文字 |

---

## 🏆 トップパフォーマンス投稿

"""
    
    for i, post in enumerate(top_posts, 1):
        report += f"""### {i}位: {post['engagement_rate']:.2f}%

- **テキスト**: {post['text'][:80]}...
- **表示回数**: {post['views']:,}
- **いいね**: {post['likes']:,} | **返信**: {post['replies']:,} | **リポスト**: {post['reposts']:,}
- **投稿時刻**: {post['posted_at'].strftime('%m/%d %H:%M')}

"""
    
    report += f"""---

## ⏰ ベスト投稿時間帯

"""
    
    for i, (hour, data) in enumerate(best_hours, 1):
        report += f"{i}. **{hour:02d}時台**: エンゲージメント率 {data['avg_engagement_rate']:.2f}% (投稿数: {data['count']}件)\n"
    
    report += f"""

---

## 📝 コンテンツ分析

### 文字数
- **平均文字数**: {avg_char_count:.0f}文字
- **最短**: {min(char_counts)}文字 | **最長**: {max(char_counts)}文字

### 絵文字の効果
{emoji_effect if emoji_effect else "データ不足"}

---

## ⚠️ 改善が必要な投稿

"""
    
    for i, post in enumerate(worst_posts, 1):
        report += f"""{i}. **{post['engagement_rate']:.2f}%** - {post['text'][:60]}...
"""
    
    report += f"""

---

## 💡 次のアクションプラン (Plan)

### ✅ 続けること (Keep)

"""
    
    # 推奨事項を生成
    if best_hours:
        best_hour = best_hours[0][0]
        report += f"1. **{best_hour:02d}時台の投稿を増やす** - 最も反応が良い時間帯です\n"
    
    if top_posts:
        top_post = top_posts[0]
        if len(top_post['text']) < 100:
            report += f"2. **短めの投稿が好調** - {len(top_post['text'])}文字程度が効果的\n"
        else:
            report += f"2. **長文投稿が好調** - {len(top_post['text'])}文字程度の詳細な内容が効果的\n"
    
    if emoji_effect and "+" in emoji_effect:
        report += "3. **絵文字の使用を継続** - エンゲージメント率が高い傾向\n"
    
    report += f"""

### 🔄 改善すること (Improve)

"""
    
    # 改善提案
    if worst_posts:
        report += f"1. **低パフォーマンス投稿の分析** - なぜ反応が悪かったのか振り返る\n"
    
    if best_hours and len(best_hours) > 0:
        avoid_hours = [h for h in range(24) if h not in [bh[0] for bh in best_hours[:5]]]
        if avoid_hours:
            report += f"2. **投稿時間の最適化** - {avoid_hours[0]:02d}時台などは避ける\n"
    
    report += f"""

### 🆕 試すこと (Try)

1. **新しいコンテンツタイプを試す** - 質問形式、投票、リスト形式など
2. **異なる時間帯にテスト投稿** - まだ試していない時間帯を探る
3. **ハッシュタグの効果を検証** - 使用有無でA/Bテスト

---

## 📅 次の3日間の投稿スケジュール提案

推奨投稿時刻:
"""
    
    # 次の3日間の推奨スケジュール
    for day in range(1, 4):
        date = (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d')
        if best_hours:
            for hour, _ in best_hours[:2]:  # トップ2の時間帯
                report += f"- {date} {hour:02d}:00\n"
    
    report += f"""

---

## 🔗 詳細データ

詳細な分析データは `{ANALYTICS_FILE}` を参照してください。

---

**次回レポート**: 3日後

"""
    
    return report


def analyze_competitors():
    """
    競合投稿URLから投稿を分析
    """
    print("\n" + "="*70)
    print("🔍 競合投稿分析を実行中...")
    print("="*70)

    # 競合投稿URLリストを読み込む
    competitor_posts = load_competitor_posts()

    if not competitor_posts:
        print("⚠️  競合投稿URLが登録されていません")
        print(f"   {COMPETITORS_FILE} に投稿URLを追加してください")
        print("\nURLの追加方法:")
        print("1. Threadsアプリで気になる投稿を開く")
        print("2. 右上の「...」メニューから「リンクをコピー」")
        print(f"3. {COMPETITORS_FILE} に貼り付け")
        return

    print(f"\n分析対象投稿数: {len(competitor_posts)}件\n")

    all_threads = []
    success_count = 0
    fail_count = 0

    for i, post_data in enumerate(competitor_posts, 1):
        post_id = post_data['post_id']
        category = post_data['category']

        print(f"[{i}/{len(competitor_posts)}] 投稿ID: {post_id[:20]}... を分析中...")

        # 投稿の詳細を取得
        details = get_thread_details(post_id)

        if details:
            details['competitor_category'] = category
            details['note'] = post_data['note']
            all_threads.append(details)
            save_competitor_analytics(details)
            success_count += 1
            print(f"  ✓ 取得成功")
        else:
            fail_count += 1
            print(f"  ✗ 取得失敗（APIアクセス権限がない可能性があります）")

        time.sleep(2)  # レート制限対策

    print(f"\n{'='*70}")
    print(f"分析完了: 成功 {success_count}件 / 失敗 {fail_count}件")
    print(f"{'='*70}\n")

    if not all_threads:
        print("⚠️  投稿データを取得できませんでした")
        print("\n【原因】")
        print("Threads APIの制限により、自分のアクセストークンでは")
        print("他人の投稿を取得できない可能性があります。")
        print("\n【代替案】")
        print("1. 手動で競合の投稿を記録する")
        print("2. 自分の投稿のみでPDCA分析を行う")
        print("3. 公開されている投稿統計ツールを利用する")
        return

    # レポート生成
    report = generate_competitor_report(all_threads)

    # ファイルに保存
    with open(COMPETITOR_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ レポートを {COMPETITOR_REPORT_FILE} に保存しました")
    print(f"   詳細データ: {COMPETITOR_ANALYTICS_FILE}\n")

    return report


def generate_competitor_report(threads):
    """
    競合分析レポートをMarkdown形式で生成

    Args:
        threads: 競合の投稿データのリスト

    Returns:
        Markdownレポート
    """
    total_threads = len(threads)

    # 時間帯別分析
    hourly_distribution = defaultdict(int)
    for thread in threads:
        hour = thread.get('posted_hour', 0)
        hourly_distribution[hour] += 1

    # 文字数分析
    char_counts = [thread.get('char_count', 0) for thread in threads]
    avg_char_count = sum(char_counts) / len(char_counts) if char_counts else 0

    # 絵文字使用率
    with_emoji = [t for t in threads if t.get('has_emoji', False)]
    emoji_rate = (len(with_emoji) / total_threads * 100) if total_threads > 0 else 0

    # 曜日別分布
    day_distribution = defaultdict(int)
    for thread in threads:
        day = thread.get('posted_day', 'Unknown')
        day_distribution[day] += 1

    # メディアタイプ分布
    media_distribution = defaultdict(int)
    for thread in threads:
        media_type = thread.get('media_type', 'TEXT')
        media_distribution[media_type] += 1

    # 最も活発な時間帯
    top_hours = sorted(hourly_distribution.items(), key=lambda x: x[1], reverse=True)[:5]

    # カテゴリ別分析
    category_stats = defaultdict(lambda: {'count': 0, 'avg_char': 0, 'total_char': 0})
    for thread in threads:
        category = thread.get('competitor_category', 'その他')
        category_stats[category]['count'] += 1
        category_stats[category]['total_char'] += thread.get('char_count', 0)

    for category in category_stats:
        if category_stats[category]['count'] > 0:
            category_stats[category]['avg_char'] = (
                category_stats[category]['total_char'] / category_stats[category]['count']
            )

    # Markdownレポート生成
    now = datetime.now().strftime('%Y年%m月%d日 %H:%M')

    report = f"""# 🔍 競合アカウント分析レポート

**生成日時**: {now}
**分析投稿数**: {total_threads}件
**分析期間**: 過去7日間程度

---

## 📊 全体サマリー

| 指標 | 値 |
|------|-----|
| **総投稿数** | {total_threads}件 |
| **平均文字数** | {avg_char_count:.0f}文字 |
| **絵文字使用率** | {emoji_rate:.1f}% |

---

## ⏰ 投稿時間帯の傾向

### トップ5時間帯

"""

    for i, (hour, count) in enumerate(top_hours, 1):
        percentage = (count / total_threads * 100) if total_threads > 0 else 0
        report += f"{i}. **{hour:02d}時台**: {count}件 ({percentage:.1f}%)\n"

    report += f"""

### 時間帯別分布

"""

    # 時間帯を4つに分ける
    time_blocks = {
        '朝 (6-11時)': sum(hourly_distribution[h] for h in range(6, 12)),
        '昼 (12-17時)': sum(hourly_distribution[h] for h in range(12, 18)),
        '夜 (18-23時)': sum(hourly_distribution[h] for h in range(18, 24)),
        '深夜 (0-5時)': sum(hourly_distribution[h] for h in range(0, 6))
    }

    for block, count in time_blocks.items():
        percentage = (count / total_threads * 100) if total_threads > 0 else 0
        report += f"- {block}: {count}件 ({percentage:.1f}%)\n"

    report += f"""

---

## 📝 コンテンツ分析

### 文字数

- **平均**: {avg_char_count:.0f}文字
- **最短**: {min(char_counts) if char_counts else 0}文字
- **最長**: {max(char_counts) if char_counts else 0}文字

### 絵文字の使用

- **使用率**: {emoji_rate:.1f}% ({len(with_emoji)}/{total_threads}件)

### メディアタイプ

"""

    for media_type, count in sorted(media_distribution.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_threads * 100) if total_threads > 0 else 0
        report += f"- **{media_type}**: {count}件 ({percentage:.1f}%)\n"

    report += f"""

---

## 📅 曜日別の傾向

"""

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_names = {
        'Monday': '月曜日',
        'Tuesday': '火曜日',
        'Wednesday': '水曜日',
        'Thursday': '木曜日',
        'Friday': '金曜日',
        'Saturday': '土曜日',
        'Sunday': '日曜日'
    }

    for day in day_order:
        count = day_distribution.get(day, 0)
        if total_threads > 0:
            percentage = (count / total_threads * 100)
            report += f"- {day_names.get(day, day)}: {count}件 ({percentage:.1f}%)\n"

    report += f"""

---

## 🎯 カテゴリ別分析

"""

    for category, stats in sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        report += f"""### {category}

- 投稿数: {stats['count']}件
- 平均文字数: {stats['avg_char']:.0f}文字

"""

    report += f"""---

## 💡 インサイトと推奨事項

### 発見されたパターン

"""

    # インサイトの自動生成
    if top_hours:
        top_hour = top_hours[0][0]
        report += f"1. **人気の投稿時間帯**: {top_hour:02d}時台が最も投稿が多い\n"

    if emoji_rate > 50:
        report += f"2. **絵文字の活用**: {emoji_rate:.0f}%の投稿で絵文字が使用されている\n"
    elif emoji_rate < 20:
        report += f"2. **絵文字使用は控えめ**: {emoji_rate:.0f}%のみが絵文字を使用\n"

    if avg_char_count < 100:
        report += f"3. **短文投稿が主流**: 平均{avg_char_count:.0f}文字の簡潔な投稿\n"
    elif avg_char_count > 200:
        report += f"3. **詳細な投稿**: 平均{avg_char_count:.0f}文字の長文投稿\n"

    # 時間帯別の推奨
    if time_blocks['夜 (18-23時)'] > time_blocks['朝 (6-11時)']:
        report += f"4. **夜間の投稿が多い**: 18-23時台の投稿が活発\n"

    report += f"""

### あなたの投稿戦略への提案

"""

    # 提案を生成
    if top_hours:
        report += f"1. **投稿時間**: {top_hours[0][0]:02d}時台を試してみる\n"

    report += f"2. **文字数**: {avg_char_count:.0f}文字前後を目安にする\n"

    if emoji_rate > 50:
        report += f"3. **絵文字**: 競合の多くが絵文字を使用しているため、活用を検討\n"

    report += f"""

---

## 📚 サンプル投稿

以下は分析対象の投稿例です:

"""

    # サンプル投稿を5件表示
    for i, thread in enumerate(threads[:5], 1):
        text = thread.get('text', '')[:100]
        hour = thread.get('posted_hour', 0)
        char_count = thread.get('char_count', 0)
        username = thread.get('username', '不明')

        report += f"""### サンプル {i}

- **投稿者**: @{username}
- **投稿時刻**: {hour:02d}時台
- **文字数**: {char_count}文字
- **内容**: {text}...

"""

    report += f"""---

## 🔗 詳細データ

詳細な分析データは `{COMPETITOR_ANALYTICS_FILE}` を参照してください。

---

**次回分析**: 1週間後

"""

    return report


def suggest_next_posts():
    """
    次の投稿IDとテンプレートを提案
    """
    posts = load_schedule()
    
    if not posts:
        next_id = 1
    else:
        max_id = max(int(p['id']) for p in posts if p['id'].isdigit())
        next_id = max_id + 1
    
    # 過去の分析データから最適な時間を提案
    best_times = []
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            hourly_rates = defaultdict(list)
            for row in reader:
                try:
                    hour = int(row['posted_hour'])
                    rate = float(row['engagement_rate'])
                    hourly_rates[hour].append(rate)
                except:
                    continue
            
            # 平均エンゲージメント率が高い時間帯
            avg_rates = {h: sum(rates)/len(rates) for h, rates in hourly_rates.items()}
            best_times = sorted(avg_rates.items(), key=lambda x: x[1], reverse=True)[:3]
    
    print("\n" + "="*70)
    print("📝 次の投稿テンプレート")
    print("="*70)
    print(f"\n次のID: {next_id}")
    
    if best_times:
        print("\n推奨投稿時間:")
        for hour, rate in best_times:
            print(f"  - {hour:02d}:00 (平均エンゲージメント率: {rate:.2f}%)")
    
    # CSVテンプレート生成
    tomorrow = datetime.now() + timedelta(days=1)
    csv_template = "\n# 次の投稿を追加してください（以下の行をコピー）\n"
    
    for i in range(3):  # 3日分
        date = (tomorrow + timedelta(days=i)).strftime('%Y-%m-%d')
        if best_times:
            for j, (hour, _) in enumerate(best_times[:2]):  # 1日2回
                csv_template += f"{next_id + i*2 + j},{date} {hour:02d}:00,ここに投稿テキストを入力\n"
        else:
            csv_template += f"{next_id + i},{date} 09:00,ここに投稿テキストを入力\n"
            csv_template += f"{next_id + i + 1},{date} 18:00,ここに投稿テキストを入力\n"
    
    print(csv_template)
    print("\n" + "="*70)


# ============================================
# 投稿処理
# ============================================

def check_and_post():
    """スケジュールをチェックして投稿"""
    global DRY_RUN

    posts = load_schedule()
    posted_log = load_posted_log()
    current_time = datetime.now()

    posts_to_do = []

    for post in posts:
        post_id = post['id']

        if post_id in posted_log:
            continue

        try:
            scheduled_time = datetime.strptime(post['datetime'], '%Y-%m-%d %H:%M')
        except ValueError:
            print(f"警告: 無効な日時形式 (ID: {post_id}): {post['datetime']}")
            continue

        if current_time >= scheduled_time:
            posts_to_do.append({
                'id': post_id,
                'scheduled_time': scheduled_time,
                'text': post['text']
            })

    posts_to_do.sort(key=lambda x: x['scheduled_time'])

    if not posts_to_do:
        print("投稿待ちの項目はありません")
        return

    print(f"\n投稿待ち: {len(posts_to_do)}件")

    if DRY_RUN:
        print("\n[ドライラン] 以下の投稿が実行されます:\n")

    for i, post in enumerate(posts_to_do):
        post_id = post['id']
        text = post['text']

        print(f"\n[{i+1}/{len(posts_to_do)}] 投稿ID: {post_id}")
        print(f"  スケジュール: {post['scheduled_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  テキスト: {text[:80]}{'...' if len(text) > 80 else ''}")

        if DRY_RUN:
            print(f"  → [ドライラン] 実際には投稿されません")
            continue

        threads_post_id = create_threads_post(text)

        if threads_post_id:
            posted_log[post_id] = {
                'posted_at': datetime.now().isoformat(),
                'scheduled_at': post['scheduled_time'].isoformat(),
                'text': text,
                'threads_post_id': threads_post_id
            }
            save_posted_log(posted_log)

        if i < len(posts_to_do) - 1:
            wait_time = MIN_INTERVAL_SECONDS
            print(f"  → 次の投稿まで {wait_time}秒待機...")
            time.sleep(wait_time)


# ============================================
# メイン処理
# ============================================

def validate_config():
    """設定の検証"""
    global DRY_RUN

    print("\n✓ 環境変数の確認")

    has_token = ACCESS_TOKEN != 'YOUR_ACCESS_TOKEN_HERE'
    has_user_id = USER_ID != 'YOUR_USER_ID_HERE'

    if not has_token:
        if DRY_RUN:
            print("  ⚠ THREADS_ACCESS_TOKEN が設定されていません（ドライランモードのためスキップ）")
        else:
            print("  ✗ THREADS_ACCESS_TOKEN が設定されていません")
            return False
    else:
        # トークンの最初の数文字だけ表示
        masked_token = ACCESS_TOKEN[:8] + "..." if len(ACCESS_TOKEN) > 8 else "***"
        print(f"  ✓ ACCESS_TOKEN: 設定済み ({masked_token})")

    if not has_user_id:
        if DRY_RUN:
            print("  ⚠ THREADS_USER_ID が設定されていません（ドライランモードのためスキップ）")
        else:
            print("  ✗ THREADS_USER_ID が設定されていません")
            return False
    else:
        print(f"  ✓ USER_ID: 設定済み ({USER_ID})")

    print("\n✓ CSVファイルの読み込み")
    if not os.path.exists(CSV_FILE):
        print(f"  ✗ {CSV_FILE} が見つかりません")
        return False
    else:
        posts = load_schedule()
        print(f"  ✓ ファイル: {CSV_FILE}")
        print(f"  ✓ 投稿数: {len(posts)}件")

    return True


def main():
    """メイン関数"""
    global DRY_RUN, CSV_FILE

    parser = argparse.ArgumentParser(
        description='Threads API 予約投稿 + PDCA分析スクリプト',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python threads_pdca.py                    # 投稿チェック＆実行
  python threads_pdca.py --dry-run          # 投稿をシミュレート（実際には投稿しない）
  python threads_pdca.py --csv test.csv     # 別のCSVファイルを使用
  python threads_pdca.py pdca                    # 3日間PDCAレポート生成
  python threads_pdca.py suggest                 # 次の投稿を提案
  python threads_pdca.py full-cycle              # フルサイクル（分析→提案）
  python threads_pdca.py analyze-competitors     # 競合アカウント分析
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        choices=['pdca', 'suggest', 'full-cycle', 'analyze-competitors'],
        help='実行するコマンド（指定しない場合は投稿モード）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='ドライランモード（実際には投稿せず、動作確認のみ）'
    )

    parser.add_argument(
        '--csv',
        type=str,
        help='使用するCSVファイルのパス（デフォルト: posts_schedule.csv）'
    )

    args = parser.parse_args()

    # ドライランモードの設定
    if args.dry_run:
        DRY_RUN = True

    # CSVファイルのパス設定
    if args.csv:
        CSV_FILE = args.csv

    # コマンド実行
    if args.command == 'pdca':
        # PDCAレポート生成
        generate_3day_report()
    elif args.command == 'suggest':
        # 次の投稿を提案
        suggest_next_posts()
    elif args.command == 'full-cycle':
        # フルサイクル（分析→提案）
        generate_3day_report()
        suggest_next_posts()
    elif args.command == 'analyze-competitors':
        # 競合分析
        analyze_competitors()
    else:
        # 投稿モード
        print("=" * 70)
        if DRY_RUN:
            print("Threads 予約投稿スクリプト (ドライランモード)")
        else:
            print("Threads 予約投稿スクリプト")
        print("=" * 70)

        # 設定検証
        if not validate_config():
            print("\n⚠️  設定に問題があります。上記のエラーを確認してください。")
            sys.exit(1)

        check_and_post()

        if DRY_RUN:
            print("\n" + "=" * 70)
            print("ドライラン完了")
            print("実際に投稿する場合は --dry-run オプションを外してください")
            print("=" * 70)


if __name__ == '__main__':
    # ヘルプ表示の場合は環境変数チェックをスキップ
    if '-h' in sys.argv or '--help' in sys.argv:
        main()
        sys.exit(0)

    # ドライランモードかどうかをチェック
    is_dry_run = '--dry-run' in sys.argv

    # pdca, suggest, full-cycleコマンドは認証情報チェックをスキップ（実行時にチェックされる）
    is_read_only_command = any(cmd in sys.argv for cmd in ['pdca', 'suggest', 'full-cycle'])

    # ドライランモードまたは読み取り専用コマンド以外では認証情報が必須
    if not is_dry_run and not is_read_only_command:
        if ACCESS_TOKEN == 'YOUR_ACCESS_TOKEN_HERE' or USER_ID == 'YOUR_USER_ID_HERE':
            print("\n⚠️  認証情報が設定されていません！")
            print("環境変数を設定してください：")
            print("  export THREADS_ACCESS_TOKEN='your_token'")
            print("  export THREADS_USER_ID='your_user_id'")
            print("\nまたは、動作確認だけなら --dry-run オプションを使用してください：")
            print("  python threads_pdca.py --dry-run")
            sys.exit(1)

    main()
