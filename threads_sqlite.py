#!/usr/bin/env python3
"""
Threads API 予約投稿 + PDCA分析スクリプト (SQLite版)
3日サイクルでPDCAを回すことに特化
"""

import sqlite3
import csv
import time
import requests
import json
import argparse
import os
import sys
import re
from datetime import datetime, timedelta
from collections import defaultdict


# ============================================
# 設定項目
# ============================================
ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN_HERE')
USER_ID = os.getenv('THREADS_USER_ID', 'YOUR_USER_ID_HERE')

# ファイルパス
DB_FILE = os.getenv('DB_FILE', 'threads.db')
PDCA_REPORT_FILE = 'pdca_report.md'
COMPETITOR_REPORT_FILE = 'competitor_report.md'

# レート制限対策
MIN_INTERVAL_SECONDS = 3600  # 1時間

# ドライランモード
DRY_RUN = False

# ============================================
# Threads API
# ============================================
API_BASE_URL = 'https://graph.threads.net/v1.0'


def get_db_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能に
    return conn


def create_threads_post(text):
    """Threads APIで投稿を作成"""
    global DRY_RUN

    if DRY_RUN:
        print(f"  → [ドライラン] 投稿をシミュレート中...")
        print(f"  → [ドライラン] 実際には投稿されません")
        time.sleep(0.5)
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


def get_post_insights(threads_post_id):
    """投稿の分析データを取得"""
    try:
        url = f'{API_BASE_URL}/{threads_post_id}'
        params = {
            'fields': 'id,text,timestamp,permalink',
            'access_token': ACCESS_TOKEN
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        insights_url = f'{API_BASE_URL}/{threads_post_id}/insights'
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
            'threads_post_id': threads_post_id,
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
# データベース操作
# ============================================

def get_pending_posts():
    """未投稿で投稿時刻を過ぎたものを取得"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 日本時間（JST = UTC+9）で現在時刻を取得
    from datetime import timezone, timedelta
    jst = timezone(timedelta(hours=9))
    current_time = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        SELECT id, csv_id, scheduled_at, text, category
        FROM posts
        WHERE status = 'pending'
          AND scheduled_at <= ?
        ORDER BY scheduled_at
    """, (current_time,))

    posts = cursor.fetchall()
    conn.close()

    return [dict(row) for row in posts]


def mark_as_posted(post_id, threads_post_id):
    """投稿を投稿済みとしてマーク"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE posts
        SET status = 'posted',
            threads_post_id = ?,
            posted_at = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (threads_post_id, datetime.now(), post_id))

    conn.commit()
    conn.close()


def mark_as_failed(post_id, error_message):
    """投稿を失敗としてマーク"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE posts
        SET status = 'failed',
            error_message = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (error_message, post_id))

    conn.commit()
    conn.close()


def save_analytics(post_id, analytics_data):
    """分析データを保存"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO analytics (
            post_id, threads_post_id,
            views, likes, replies, reposts, quotes,
            engagement, engagement_rate,
            permalink, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id,
        analytics_data['threads_post_id'],
        analytics_data['views'],
        analytics_data['likes'],
        analytics_data['replies'],
        analytics_data['reposts'],
        analytics_data['quotes'],
        analytics_data['engagement'],
        analytics_data['engagement_rate'],
        analytics_data['permalink'],
        datetime.now()
    ))

    conn.commit()
    conn.close()


def get_recent_posts(days=3):
    """過去N日間の投稿済み投稿を取得"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        SELECT id, csv_id, text, posted_at, threads_post_id, category, scheduled_at
        FROM posts
        WHERE status = 'posted'
          AND posted_at >= ?
        ORDER BY posted_at DESC
    """, (cutoff_date,))

    posts = cursor.fetchall()
    conn.close()

    return [dict(row) for row in posts]


# ============================================
# 投稿管理コマンド
# ============================================

def add_post(scheduled_at, text, category=None):
    """新しい投稿を追加"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 最新のcsv_idを取得
    cursor.execute("SELECT MAX(CAST(csv_id AS INTEGER)) FROM posts WHERE csv_id GLOB '[0-9]*'")
    result = cursor.fetchone()
    max_id = result[0] if result[0] else 0
    new_csv_id = str(max_id + 1)

    # テキスト分析
    char_count = len(text)
    has_emoji = any(ord(c) > 127 for c in text)

    # カテゴリ自動検出
    if not category:
        category = detect_category(text)

    cursor.execute("""
        INSERT INTO posts (
            csv_id, scheduled_at, text, status,
            category, char_count, has_emoji
        ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
    """, (new_csv_id, scheduled_at, text, category, char_count, has_emoji))

    conn.commit()
    post_id = cursor.lastrowid
    conn.close()

    print(f"✅ 投稿を追加しました (ID: {new_csv_id})")
    print(f"   日時: {scheduled_at}")
    print(f"   カテゴリ: {category}")
    print(f"   文字数: {char_count}文字")

    return post_id


def detect_category(text):
    """テキストからカテゴリを推定"""
    keywords = {
        '恋愛': ['彼氏', '彼女', '恋愛', 'マッチング', '出会い', '好き', 'デート', '結婚'],
        '仕事': ['転職', '仕事', '職場', '会社', '上司', '給料', '残業', 'キャリア'],
        'お金': ['貯金', 'お金', '節約', 'NISA', '投資', 'サブスク', 'クレカ', '浪費'],
        'メンタル': ['HSP', '繊細', '自己肯定感', 'ストレス', '疲れ', '不安', 'メンタル'],
        '占い': ['占い', '月星座', '数秘', 'タロット', 'ホロスコープ', 'スピリチュアル']
    }

    for category, words in keywords.items():
        if any(word in text for word in words):
            return category

    return 'その他'


def list_posts(status=None, limit=20, today=False, tomorrow=False):
    """投稿一覧を表示"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, csv_id, scheduled_at, substr(text, 1, 50) as preview, status, category FROM posts"
    params = []

    conditions = []
    if status:
        conditions.append("status = ?")
        params.append(status)

    if today:
        conditions.append("DATE(scheduled_at) = DATE('now', 'localtime')")
    elif tomorrow:
        conditions.append("DATE(scheduled_at) = DATE('now', 'localtime', '+1 day')")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY scheduled_at DESC LIMIT {limit}"

    cursor.execute(query, params)
    posts = cursor.fetchall()
    conn.close()

    if not posts:
        print("投稿が見つかりません")
        return

    print(f"\n投稿一覧 ({len(posts)}件):")
    print("-" * 100)

    for post in posts:
        post_dict = dict(post)
        print(f"[{post_dict['csv_id']}] {post_dict['scheduled_at']} | {post_dict['status']:8s} | {post_dict['category']:8s}")
        print(f"      {post_dict['preview']}...")
        print()


def import_from_csv(csv_file):
    """CSVファイルから投稿をインポート"""
    if not os.path.exists(csv_file):
        print(f"✗ ファイルが見つかりません: {csv_file}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    imported = 0
    skipped = 0

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_id = row.get('id', '').strip()
            datetime_str = row.get('datetime', '').strip()
            text = row.get('text', '').strip()
            category = row.get('category', '').strip() or None

            if not csv_id or not datetime_str or not text:
                skipped += 1
                continue

            try:
                scheduled_at = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                char_count = len(text)
                has_emoji = any(ord(c) > 127 for c in text)

                if not category:
                    category = detect_category(text)

                cursor.execute("""
                    INSERT INTO posts (
                        csv_id, scheduled_at, text, status,
                        category, char_count, has_emoji
                    ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
                """, (csv_id, scheduled_at, text, category, char_count, has_emoji))

                imported += 1

            except sqlite3.IntegrityError:
                skipped += 1
            except Exception as e:
                print(f"✗ エラー (ID: {csv_id}): {e}")
                skipped += 1

    conn.commit()
    conn.close()

    print(f"✅ インポート完了:")
    print(f"   成功: {imported}件")
    print(f"   スキップ: {skipped}件")


def export_to_csv(output_file, status=None):
    """投稿をCSVファイルにエクスポート"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT csv_id, scheduled_at, text, status, category FROM posts"
    params = []

    if status:
        query += " WHERE status = ?"
        params.append(status)

    query += " ORDER BY scheduled_at"

    cursor.execute(query, params)
    posts = cursor.fetchall()
    conn.close()

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'datetime', 'text', 'status', 'category'])

        for post in posts:
            post_dict = dict(post)
            dt = datetime.fromisoformat(post_dict['scheduled_at']).strftime('%Y-%m-%d %H:%M')
            writer.writerow([
                post_dict['csv_id'],
                dt,
                post_dict['text'],
                post_dict['status'],
                post_dict['category']
            ])

    print(f"✅ エクスポート完了: {len(posts)}件 → {output_file}")


# ============================================
# 投稿処理
# ============================================

def check_and_post():
    """スケジュールをチェックして投稿"""
    global DRY_RUN
    from datetime import timezone, timedelta

    # 現在時刻を表示
    jst = timezone(timedelta(hours=9))
    current_time_jst = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n📅 現在時刻（JST）: {current_time_jst}")

    posts = get_pending_posts()

    if not posts:
        print("投稿待ちの項目はありません")
        return

    print(f"\n✅ 投稿対象: {len(posts)}件")
    print(f"時刻範囲: {posts[0]['scheduled_at']} 〜 {posts[-1]['scheduled_at']}")

    if DRY_RUN:
        print("\n[ドライラン] 以下の投稿が実行されます:\n")

    for i, post in enumerate(posts):
        post_id = post['id']
        csv_id = post['csv_id']
        text = post['text']
        scheduled_at = post['scheduled_at']
        category = post.get('category', '未分類')

        print(f"\n[{i+1}/{len(posts)}] 投稿ID: {csv_id} | {scheduled_at} | [{category}]")
        print(f"  テキスト: {text[:80]}{'...' if len(text) > 80 else ''}")

        if DRY_RUN:
            print(f"  → [ドライラン] 実際には投稿されません")
            continue

        threads_post_id = create_threads_post(text)

        if threads_post_id:
            mark_as_posted(post_id, threads_post_id)
        else:
            mark_as_failed(post_id, "API投稿エラー")

        if i < len(posts) - 1:
            wait_time = MIN_INTERVAL_SECONDS
            print(f"  → 次の投稿まで {wait_time}秒待機...")
            time.sleep(wait_time)


# ============================================
# PDCA分析
# ============================================

def generate_pdca_report(days=3):
    """PDCAレポートを生成"""
    print("\n" + "="*70)
    print(f"📊 過去{days}日間のPDCAレポートを生成中...")
    print("="*70)

    recent_posts = get_recent_posts(days)

    if not recent_posts:
        print(f"⚠️  過去{days}日間の投稿がありません")
        return

    print(f"\n過去{days}日間の投稿数: {len(recent_posts)}件")
    print("分析データを取得中...\n")

    # 各投稿の分析データを取得
    analytics_results = []
    for i, post in enumerate(recent_posts, 1):
        print(f"[{i}/{len(recent_posts)}] 投稿 {post['csv_id']} を分析中...")
        analytics = get_post_insights(post['threads_post_id'])
        if analytics:
            analytics['posted_at'] = datetime.fromisoformat(post['posted_at'])
            analytics['csv_id'] = post['csv_id']
            analytics['category'] = post['category']
            analytics_results.append(analytics)

            # DB に保存
            save_analytics(post['id'], analytics)
            print(f"  ✓ 完了")
        time.sleep(2)

    if not analytics_results:
        print("⚠️  分析データを取得できませんでした")
        return

    # レポート生成
    report = generate_pdca_markdown(analytics_results, days)

    # ファイルに保存
    with open(PDCA_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ レポートを {PDCA_REPORT_FILE} に保存しました")
    print("\n" + report)


def generate_pdca_markdown(analytics_results, days):
    """PDCAレポートをMarkdown形式で生成"""
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

    # カテゴリ別分析
    category_performance = defaultdict(lambda: {'count': 0, 'engagement_rate': 0})
    for a in analytics_results:
        cat = a.get('category', 'その他')
        category_performance[cat]['count'] += 1
        category_performance[cat]['engagement_rate'] += a['engagement_rate']

    for cat in category_performance:
        category_performance[cat]['avg_engagement_rate'] = (
            category_performance[cat]['engagement_rate'] /
            category_performance[cat]['count']
        )

    # トップパフォーマンス投稿
    top_posts = sorted(analytics_results, key=lambda x: x['engagement_rate'], reverse=True)[:3]
    worst_posts = sorted(analytics_results, key=lambda x: x['engagement_rate'])[:3]

    # 文字数分析
    char_counts = [len(a['text']) for a in analytics_results]
    avg_char_count = sum(char_counts) / len(char_counts) if char_counts else 0

    # Markdownレポート生成
    now = datetime.now().strftime('%Y年%m月%d日 %H:%M')

    report = f"""# 📊 Threads PDCA レポート

**生成日時**: {now}
**分析期間**: 過去{days}日間
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
        report += f"""### {i}位: {post['engagement_rate']:.2f}% [{post.get('category', '')}]

- **テキスト**: {post['text'][:80]}...
- **表示回数**: {post['views']:,}
- **いいね**: {post['likes']:,} | **返信**: {post['replies']:,} | **リポスト**: {post['reposts']:,}
- **投稿時刻**: {post['posted_at'].strftime('%m/%d %H:%M')}

"""

    report += f"""---

## 🎯 カテゴリ別パフォーマンス

"""

    for cat, data in sorted(category_performance.items(), key=lambda x: x[1]['avg_engagement_rate'], reverse=True):
        report += f"- **{cat}**: {data['avg_engagement_rate']:.2f}% (投稿数: {data['count']}件)\n"

    report += f"""

---

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

---

## ⚠️ 改善が必要な投稿

"""

    for i, post in enumerate(worst_posts, 1):
        report += f"""{i}. **{post['engagement_rate']:.2f}%** [{post.get('category', '')}] - {post['text'][:60]}...
"""

    report += f"""

---

## 💡 次のアクションプラン (Plan)

### ✅ 続けること (Keep)

"""

    if best_hours:
        best_hour = best_hours[0][0]
        report += f"1. **{best_hour:02d}時台の投稿を増やす** - 最も反応が良い時間帯です\n"

    # トップカテゴリ
    top_category = max(category_performance.items(), key=lambda x: x[1]['avg_engagement_rate'])
    report += f"2. **{top_category[0]}カテゴリが好調** - エンゲージメント率 {top_category[1]['avg_engagement_rate']:.2f}%\n"

    if top_posts:
        top_post = top_posts[0]
        if len(top_post['text']) < 200:
            report += f"3. **短めの投稿が好調** - {len(top_post['text'])}文字程度が効果的\n"
        else:
            report += f"3. **長文投稿が好調** - {len(top_post['text'])}文字程度の詳細な内容が効果的\n"

    report += f"""

### 🔄 改善すること (Improve)

"""

    # ワーストカテゴリ
    worst_category = min(category_performance.items(), key=lambda x: x[1]['avg_engagement_rate'])
    report += f"1. **{worst_category[0]}カテゴリの改善** - エンゲージメント率が低い ({worst_category[1]['avg_engagement_rate']:.2f}%)\n"
    report += f"2. **低パフォーマンス投稿の分析** - なぜ反応が悪かったのか振り返る\n"

    report += f"""

### 🆕 試すこと (Try)

1. **新しいコンテンツタイプを試す** - 質問形式、投票、リスト形式など
2. **異なる時間帯にテスト投稿** - まだ試していない時間帯を探る
3. **反応が良いカテゴリを増やす** - {top_category[0]}の投稿を増やす

---

**次回レポート**: {days}日後

"""

    return report


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

    print("\n✓ データベースの確認")
    if not os.path.exists(DB_FILE):
        print(f"  ✗ {DB_FILE} が見つかりません")
        print(f"  → python migrate_to_sqlite.py full を実行してください")
        return False
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"  ✓ データベース: {DB_FILE}")
        print(f"  ✓ 投稿数: {count}件")

    return True


def main():
    """メイン関数"""
    global DRY_RUN, DB_FILE

    parser = argparse.ArgumentParser(
        description='Threads API 予約投稿 + PDCA分析スクリプト (SQLite版)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 投稿実行
  python threads_sqlite.py post                # 投稿チェック＆実行
  python threads_sqlite.py post --dry-run      # ドライラン

  # 投稿管理
  python threads_sqlite.py list                # 投稿一覧
  python threads_sqlite.py list --status pending --limit 10
  python threads_sqlite.py list --today        # 今日の予定

  python threads_sqlite.py add                 # 投稿追加（対話式）
  python threads_sqlite.py import --csv new.csv
  python threads_sqlite.py export --output backup.csv

  # PDCA分析
  python threads_sqlite.py pdca                # 過去3日間
  python threads_sqlite.py pdca --days 7       # 過去7日間
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='post',
        choices=['post', 'list', 'add', 'import', 'export', 'pdca'],
        help='実行するコマンド'
    )

    parser.add_argument('--dry-run', action='store_true', help='ドライランモード')
    parser.add_argument('--status', type=str, help='投稿ステータス (pending/posted/failed)')
    parser.add_argument('--limit', type=int, default=20, help='表示件数')
    parser.add_argument('--today', action='store_true', help='今日の投稿のみ')
    parser.add_argument('--tomorrow', action='store_true', help='明日の投稿のみ')
    parser.add_argument('--csv', type=str, help='CSVファイルパス')
    parser.add_argument('--output', type=str, help='出力ファイルパス')
    parser.add_argument('--days', type=int, default=3, help='PDCA分析の日数')
    parser.add_argument('--datetime', type=str, help='投稿日時 (YYYY-MM-DD HH:MM)')
    parser.add_argument('--text', type=str, help='投稿テキスト')
    parser.add_argument('--category', type=str, help='カテゴリ')

    args = parser.parse_args()

    if args.dry_run:
        DRY_RUN = True

    # コマンド実行
    if args.command == 'post':
        # 投稿モード
        print("=" * 70)
        if DRY_RUN:
            print("Threads 予約投稿スクリプト (ドライランモード)")
        else:
            print("Threads 予約投稿スクリプト")
        print("=" * 70)

        if not validate_config():
            print("\n⚠️  設定に問題があります。上記のエラーを確認してください。")
            sys.exit(1)

        check_and_post()

        if DRY_RUN:
            print("\n" + "=" * 70)
            print("ドライラン完了")
            print("実際に投稿する場合は --dry-run オプションを外してください")
            print("=" * 70)

    elif args.command == 'list':
        list_posts(args.status, args.limit, args.today, args.tomorrow)

    elif args.command == 'add':
        if args.datetime and args.text:
            add_post(args.datetime, args.text, args.category)
        else:
            print("使用方法: python threads_sqlite.py add --datetime \"2025-11-02 08:00\" --text \"投稿内容\" --category \"恋愛\"")

    elif args.command == 'import':
        if args.csv:
            import_from_csv(args.csv)
        else:
            print("使用方法: python threads_sqlite.py import --csv posts.csv")

    elif args.command == 'export':
        output = args.output or 'posts_export.csv'
        export_to_csv(output, args.status)

    elif args.command == 'pdca':
        generate_pdca_report(args.days)


if __name__ == '__main__':
    if '-h' in sys.argv or '--help' in sys.argv:
        main()
        sys.exit(0)

    is_dry_run = '--dry-run' in sys.argv
    is_read_only = any(cmd in sys.argv for cmd in ['list', 'export', 'pdca', 'add', 'import'])

    if not is_dry_run and not is_read_only:
        if ACCESS_TOKEN == 'YOUR_ACCESS_TOKEN_HERE' or USER_ID == 'YOUR_USER_ID_HERE':
            print("\n⚠️  認証情報が設定されていません！")
            print("環境変数を設定してください：")
            print("  export THREADS_ACCESS_TOKEN='your_token'")
            print("  export THREADS_USER_ID='your_user_id'")
            print("\nまたは、動作確認だけなら --dry-run オプションを使用してください：")
            print("  python threads_sqlite.py post --dry-run")
            sys.exit(1)

    main()
