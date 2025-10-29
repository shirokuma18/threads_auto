#!/usr/bin/env python3
"""
古い投稿データをアーカイブするスクリプト
DBサイズ削減のため
"""

import sqlite3
import csv
import os
import argparse
from datetime import datetime, timedelta


DB_FILE = 'threads.db'
ARCHIVE_DIR = 'archive/posts'


def archive_old_posts(days_old=90, delete=False):
    """
    古い投稿をCSVにエクスポートし、オプションでDBから削除

    Args:
        days_old: 何日前より古いデータをアーカイブするか
        delete: DBから削除するかどうか
    """
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d')
    archive_filename = f"{ARCHIVE_DIR}/posts_before_{cutoff_date}.csv"

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # アーカイブ対象の投稿を取得
    cursor.execute("""
        SELECT * FROM posts
        WHERE status = 'posted'
          AND posted_at < ?
        ORDER BY posted_at
    """, (cutoff_date,))

    posts = cursor.fetchall()

    if not posts:
        print(f"⚠️  {days_old}日前より古い投稿はありません")
        conn.close()
        return 0

    print(f"\n📦 {len(posts)}件の投稿をアーカイブします")
    print(f"   期間: 〜 {cutoff_date}")
    print(f"   出力先: {archive_filename}")

    # CSVにエクスポート
    with open(archive_filename, 'w', encoding='utf-8', newline='') as f:
        if posts:
            fieldnames = posts[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for post in posts:
                writer.writerow(dict(post))

    print(f"✅ エクスポート完了: {archive_filename}")

    # 削除オプション
    if delete:
        post_ids = [post['id'] for post in posts]
        placeholders = ','.join('?' * len(post_ids))

        # 関連する分析データも削除
        cursor.execute(f"""
            DELETE FROM analytics
            WHERE post_id IN ({placeholders})
        """, post_ids)
        analytics_deleted = cursor.rowcount

        # 投稿を削除
        cursor.execute(f"""
            DELETE FROM posts
            WHERE id IN ({placeholders})
        """, post_ids)
        posts_deleted = cursor.rowcount

        conn.commit()

        print(f"🗑️  削除完了:")
        print(f"   投稿: {posts_deleted}件")
        print(f"   分析データ: {analytics_deleted}件")

        # VACUUM（DBファイルサイズを実際に削減）
        print(f"\n🔧 データベースを最適化中...")
        cursor.execute("VACUUM")

        # 削減されたサイズを表示
        size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
        print(f"✅ 最適化完了")
        print(f"   現在のDBサイズ: {size_mb:.2f} MB")

    else:
        print(f"\n💡 ヒント:")
        print(f"   DBから削除するには --delete オプションを使用してください")
        print(f"   python3 archive_old_posts.py --older-than {days_old} --delete")

    conn.close()
    return len(posts)


def main():
    parser = argparse.ArgumentParser(
        description='古い投稿データをアーカイブ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 90日前より古いデータをCSVにエクスポート（削除しない）
  python3 archive_old_posts.py --older-than 90

  # エクスポート + DBから削除
  python3 archive_old_posts.py --older-than 90 --delete

  # 1年前より古いデータをアーカイブ
  python3 archive_old_posts.py --older-than 365 --delete
        """
    )

    parser.add_argument(
        '--older-than',
        type=int,
        default=90,
        help='何日前より古いデータをアーカイブするか（デフォルト: 90日）'
    )

    parser.add_argument(
        '--delete',
        action='store_true',
        help='DBから削除する（エクスポート後）'
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("📦 投稿データアーカイブツール")
    print("="*70)

    if args.delete:
        print(f"\n⚠️  警告: {args.older_than}日前より古いデータをDBから削除します")
        confirm = input("続行しますか？ (yes/no): ")
        if confirm.lower() != 'yes':
            print("中止しました")
            return

    count = archive_old_posts(args.older_than, args.delete)

    print("\n" + "="*70)
    print(f"✅ アーカイブ完了: {count}件")
    print("="*70)
    print()


if __name__ == '__main__':
    main()
