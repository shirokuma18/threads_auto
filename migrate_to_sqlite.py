#!/usr/bin/env python3
"""
CSV → SQLite マイグレーションスクリプト
既存のCSVとposted_log.jsonをSQLiteに移行
"""

import sqlite3
import csv
import json
import argparse
import os
from datetime import datetime


DB_FILE = 'threads.db'
CSV_FILE = 'posts_schedule.csv'
LOG_FILE = 'posted_log.json'


def create_database():
    """データベースとテーブルを作成"""
    print("\n" + "="*70)
    print("📦 データベースを作成中...")
    print("="*70)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # postsテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            csv_id TEXT UNIQUE,
            scheduled_at DATETIME NOT NULL,
            text TEXT NOT NULL,
            thread_text TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            category TEXT,
            char_count INTEGER,
            has_emoji BOOLEAN DEFAULT 0,

            threads_post_id TEXT,
            posted_at DATETIME,
            error_message TEXT
        )
    """)

    # インデックス
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_scheduled_at ON posts(scheduled_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category)")

    # analyticsテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            threads_post_id TEXT NOT NULL,

            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            replies INTEGER DEFAULT 0,
            reposts INTEGER DEFAULT 0,
            quotes INTEGER DEFAULT 0,

            engagement INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0,

            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            permalink TEXT,

            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_post_id ON analytics(post_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_engagement_rate ON analytics(engagement_rate)")

    # competitorsテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT NOT NULL UNIQUE,
            threads_post_id TEXT NOT NULL,
            username TEXT,
            category TEXT,
            note TEXT,

            text TEXT,
            posted_at DATETIME,
            char_count INTEGER,
            has_emoji BOOLEAN DEFAULT 0,

            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            analyzed_at DATETIME
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_competitors_category ON competitors(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_competitors_posted_at ON competitors(posted_at)")

    conn.commit()
    conn.close()

    print(f"  ✓ データベース作成完了: {DB_FILE}")
    print(f"  ✓ テーブル: posts, analytics, competitors")


def import_csv(csv_file=CSV_FILE):
    """CSVファイルからpostsテーブルにインポート"""
    print("\n" + "="*70)
    print(f"📥 CSVファイルをインポート中: {csv_file}")
    print("="*70)

    if not os.path.exists(csv_file):
        print(f"  ✗ ファイルが見つかりません: {csv_file}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    imported = 0
    skipped = 0

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_id = row.get('id', '').strip()
            datetime_str = row.get('datetime', '').strip()
            text = row.get('text', '').strip()
            thread_text = row.get('thread_text', '').strip() or None

            if not csv_id or not datetime_str or not text:
                print(f"  ⚠ スキップ: 不完全なデータ (ID: {csv_id})")
                skipped += 1
                continue

            try:
                # 日時のパース
                scheduled_at = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')

                # テキスト分析
                char_count = len(text)
                has_emoji = any(ord(c) > 127 for c in text)

                # カテゴリの推定（キーワードベース）
                category = detect_category(text)

                # 挿入
                cursor.execute("""
                    INSERT INTO posts (
                        csv_id, scheduled_at, text, thread_text, status,
                        char_count, has_emoji, category
                    ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
                """, (csv_id, scheduled_at, text, thread_text, char_count, has_emoji, category))

                imported += 1

            except sqlite3.IntegrityError:
                print(f"  ⚠ スキップ: 既に存在 (ID: {csv_id})")
                skipped += 1
            except Exception as e:
                print(f"  ✗ エラー (ID: {csv_id}): {e}")
                skipped += 1

    conn.commit()
    conn.close()

    print(f"\n  ✓ インポート完了:")
    print(f"    - 成功: {imported}件")
    print(f"    - スキップ: {skipped}件")


def import_log(log_file=LOG_FILE):
    """posted_log.jsonから投稿済み情報をインポート"""
    print("\n" + "="*70)
    print(f"📥 投稿ログをインポート中: {log_file}")
    print("="*70)

    if not os.path.exists(log_file):
        print(f"  ⚠ ファイルが見つかりません: {log_file}")
        return

    with open(log_file, 'r', encoding='utf-8') as f:
        log_data = json.load(f)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    updated = 0
    not_found = 0

    for csv_id, log_entry in log_data.items():
        threads_post_id = log_entry.get('threads_post_id')
        posted_at_str = log_entry.get('posted_at')

        if not threads_post_id or not posted_at_str:
            continue

        try:
            posted_at = datetime.fromisoformat(posted_at_str)

            # postsテーブルを更新
            cursor.execute("""
                UPDATE posts
                SET status = 'posted',
                    threads_post_id = ?,
                    posted_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE csv_id = ?
            """, (threads_post_id, posted_at, csv_id))

            if cursor.rowcount > 0:
                updated += 1
            else:
                not_found += 1
                print(f"  ⚠ DB内に見つからない (CSV ID: {csv_id})")

        except Exception as e:
            print(f"  ✗ エラー (CSV ID: {csv_id}): {e}")

    conn.commit()
    conn.close()

    print(f"\n  ✓ インポート完了:")
    print(f"    - 更新: {updated}件")
    print(f"    - 未発見: {not_found}件")


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


def show_stats():
    """データベースの統計を表示"""
    print("\n" + "="*70)
    print("📊 データベース統計")
    print("="*70)

    if not os.path.exists(DB_FILE):
        print(f"  ✗ データベースが見つかりません: {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 投稿数
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM posts WHERE status = 'pending'")
    pending_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM posts WHERE status = 'posted'")
    posted_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM posts WHERE status = 'failed'")
    failed_posts = cursor.fetchone()[0]

    print(f"\n📝 投稿統計:")
    print(f"  - 総数: {total_posts}件")
    print(f"  - 未投稿: {pending_posts}件")
    print(f"  - 投稿済み: {posted_posts}件")
    print(f"  - 失敗: {failed_posts}件")

    # カテゴリ別
    cursor.execute("""
        SELECT category, COUNT(*)
        FROM posts
        GROUP BY category
        ORDER BY COUNT(*) DESC
    """)
    categories = cursor.fetchall()

    if categories:
        print(f"\n📂 カテゴリ別:")
        for category, count in categories:
            print(f"  - {category}: {count}件")

    # 直近の投稿予定
    cursor.execute("""
        SELECT csv_id, scheduled_at, substr(text, 1, 50)
        FROM posts
        WHERE status = 'pending'
        ORDER BY scheduled_at
        LIMIT 5
    """)
    upcoming = cursor.fetchall()

    if upcoming:
        print(f"\n📅 直近の投稿予定:")
        for csv_id, scheduled_at, text_preview in upcoming:
            print(f"  - [{scheduled_at}] {text_preview}...")

    conn.close()


def export_to_csv(output_file='posts_export.csv'):
    """SQLiteからCSVにエクスポート"""
    print("\n" + "="*70)
    print(f"📤 CSVにエクスポート中: {output_file}")
    print("="*70)

    if not os.path.exists(DB_FILE):
        print(f"  ✗ データベースが見つかりません: {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT csv_id, scheduled_at, text, status, category
        FROM posts
        ORDER BY scheduled_at
    """)

    rows = cursor.fetchall()

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'datetime', 'text', 'status', 'category'])

        for row in rows:
            csv_id, scheduled_at, text, status, category = row
            # datetimeを文字列に変換
            dt = datetime.fromisoformat(scheduled_at).strftime('%Y-%m-%d %H:%M')
            writer.writerow([csv_id, dt, text, status, category])

    conn.close()

    print(f"  ✓ エクスポート完了: {len(rows)}件")


def main():
    parser = argparse.ArgumentParser(
        description='CSV → SQLite マイグレーションツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 1. データベース初期化
  python migrate_to_sqlite.py init

  # 2. CSVをインポート
  python migrate_to_sqlite.py import-csv

  # 3. posted_log.jsonをインポート
  python migrate_to_sqlite.py import-log

  # 4. 統計確認
  python migrate_to_sqlite.py stats

  # 5. 全工程を一括実行
  python migrate_to_sqlite.py full

  # 6. CSVにエクスポート（バックアップ）
  python migrate_to_sqlite.py export --output backup.csv
        """
    )

    parser.add_argument(
        'command',
        choices=['init', 'import-csv', 'import-log', 'stats', 'export', 'full'],
        help='実行するコマンド'
    )

    parser.add_argument('--csv', type=str, default=CSV_FILE, help='CSVファイルのパス')
    parser.add_argument('--log', type=str, default=LOG_FILE, help='ログファイルのパス')
    parser.add_argument('--output', type=str, default='posts_export.csv', help='出力CSVファイル')

    args = parser.parse_args()

    if args.command == 'init':
        create_database()

    elif args.command == 'import-csv':
        import_csv(args.csv)

    elif args.command == 'import-log':
        import_log(args.log)

    elif args.command == 'stats':
        show_stats()

    elif args.command == 'export':
        export_to_csv(args.output)

    elif args.command == 'full':
        # 全工程を実行
        create_database()
        import_csv(args.csv)
        import_log(args.log)
        show_stats()
        print("\n" + "="*70)
        print("✅ マイグレーション完了！")
        print("="*70)
        print("\n次のステップ:")
        print("  1. python threads_sqlite.py --dry-run  # ドライランでテスト")
        print("  2. python threads_sqlite.py            # 本番実行")

    print()


if __name__ == '__main__':
    main()
