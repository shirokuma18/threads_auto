#!/usr/bin/env python3
"""
データベースサイズ監視スクリプト
GitHubの制限（50MB警告、100MB制限）をチェック
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta


DB_FILE = 'threads.db'
SIZE_WARNING_MB = 40  # 40MBで警告
SIZE_ERROR_MB = 90    # 90MBでエラー（GitHubは100MB制限）


def get_file_size_mb(filepath):
    """ファイルサイズをMB単位で取得"""
    if not os.path.exists(filepath):
        return 0
    size_bytes = os.path.getsize(filepath)
    size_mb = size_bytes / (1024 * 1024)
    return size_mb


def get_db_stats():
    """データベースの統計情報を取得"""
    if not os.path.exists(DB_FILE):
        return None

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 投稿数
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM posts WHERE status = 'posted'")
    posted_count = cursor.fetchone()[0]

    # 分析データ数
    cursor.execute("SELECT COUNT(*) FROM analytics")
    analytics_count = cursor.fetchone()[0]

    # 最古・最新の投稿
    cursor.execute("SELECT MIN(scheduled_at), MAX(scheduled_at) FROM posts")
    oldest, newest = cursor.fetchone()

    conn.close()

    return {
        'total_posts': total_posts,
        'posted_count': posted_count,
        'analytics_count': analytics_count,
        'oldest': oldest,
        'newest': newest
    }


def estimate_future_size(current_size_mb, stats):
    """将来のサイズを予測"""
    if not stats or stats['posted_count'] == 0:
        return None

    # 1投稿あたりの平均サイズ
    avg_size_per_post = current_size_mb / stats['total_posts']

    # 1年後の予測（1日25投稿×365日=9,125投稿追加）
    posts_per_year = 25 * 365
    estimated_size_1year = current_size_mb + (avg_size_per_post * posts_per_year)

    return {
        'avg_size_per_post_kb': avg_size_per_post * 1024,
        'estimated_1year_mb': estimated_size_1year
    }


def suggest_cleanup():
    """クリーンアップ方法を提案"""
    print("\n" + "="*70)
    print("📦 データベース容量削減方法")
    print("="*70)
    print()
    print("1. 古い投稿をアーカイブ:")
    print("   python3 archive_old_posts.py --older-than 90")
    print()
    print("2. 投稿済みデータをCSVにエクスポート:")
    print("   python3 threads_sqlite.py export --status posted --output archive.csv")
    print()
    print("3. DBを最適化（VACUUM）:")
    print("   sqlite3 threads.db 'VACUUM;'")
    print()
    print("4. DBをGitHubから除外（推奨）:")
    print("   echo 'threads.db' >> .gitignore")
    print("   git rm --cached threads.db")
    print()


def check_db_size(verbose=True, strict=False):
    """
    データベースサイズをチェック

    Args:
        verbose: 詳細情報を表示
        strict: 厳密モード（警告でもエラー終了）

    Returns:
        0: OK
        1: 警告
        2: エラー
    """
    if not os.path.exists(DB_FILE):
        if verbose:
            print(f"⚠️  {DB_FILE} が見つかりません")
        return 0

    size_mb = get_file_size_mb(DB_FILE)
    stats = get_db_stats()

    if verbose:
        print("\n" + "="*70)
        print("📊 データベースサイズチェック")
        print("="*70)
        print()
        print(f"ファイル: {DB_FILE}")
        print(f"サイズ: {size_mb:.2f} MB")
        print()

    # サイズチェック
    status = 0

    if size_mb >= SIZE_ERROR_MB:
        print(f"❌ エラー: DBサイズが {SIZE_ERROR_MB}MB を超えています！")
        print(f"   GitHubは100MBまでしかプッシュできません。")
        suggest_cleanup()
        status = 2
    elif size_mb >= SIZE_WARNING_MB:
        print(f"⚠️  警告: DBサイズが {SIZE_WARNING_MB}MB を超えています")
        print(f"   現在: {size_mb:.2f} MB")
        if strict:
            status = 2
        else:
            status = 1
    else:
        if verbose:
            print(f"✅ OK: DBサイズは正常範囲内です")
            print(f"   現在: {size_mb:.2f} MB / {SIZE_WARNING_MB} MB")

    # 統計情報
    if verbose and stats:
        print()
        print("📈 データベース統計:")
        print(f"   総投稿数: {stats['total_posts']:,}件")
        print(f"   投稿済み: {stats['posted_count']:,}件")
        print(f"   分析データ: {stats['analytics_count']:,}件")

        if stats['oldest'] and stats['newest']:
            print(f"   期間: {stats['oldest'][:10]} 〜 {stats['newest'][:10]}")

        # 将来予測
        estimate = estimate_future_size(size_mb, stats)
        if estimate:
            print()
            print("🔮 サイズ予測:")
            print(f"   1投稿あたり: {estimate['avg_size_per_post_kb']:.2f} KB")
            print(f"   1年後の予測: {estimate['estimated_1year_mb']:.2f} MB")

            if estimate['estimated_1year_mb'] > SIZE_WARNING_MB:
                print()
                print(f"⚠️  1年後に {SIZE_WARNING_MB}MB を超える見込みです")
                print(f"   定期的なアーカイブをお勧めします")

    if verbose:
        print()
        print("="*70)

    return status


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='データベースサイズ監視スクリプト'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='エラー時のみ出力'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='警告でもエラー終了'
    )

    args = parser.parse_args()

    status = check_db_size(verbose=not args.quiet, strict=args.strict)
    sys.exit(status)


if __name__ == '__main__':
    main()
