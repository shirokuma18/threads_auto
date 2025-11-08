#!/usr/bin/env python3
"""
Threads 投稿削除スクリプト

全ての投稿を取得して削除します。
"""

import requests
import time
import os
import sys
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv(override=True)

# Threads API設定
API_BASE_URL = 'https://graph.threads.net/v1.0'
ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
USER_ID = os.getenv('THREADS_USER_ID')

# ドライランモード
DRY_RUN = '--dry-run' in sys.argv


def get_all_posts():
    """全ての投稿を取得（ページネーション対応）"""
    all_posts = []
    url = f'{API_BASE_URL}/{USER_ID}/threads'
    params = {
        'fields': 'id,text,timestamp',
        'limit': 100,  # 最大値
        'access_token': ACCESS_TOKEN
    }

    print("📥 投稿を取得中...")

    while url:
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            posts = data.get('data', [])
            all_posts.extend(posts)

            print(f"  取得済み: {len(all_posts)}件")

            # 次のページがあるか確認
            paging = data.get('paging', {})
            url = paging.get('next')
            params = None  # 次のURLには既にパラメータが含まれている

        except Exception as e:
            print(f"✗ エラー: {e}")
            break

    print(f"\n✓ 合計 {len(all_posts)} 件の投稿を取得しました")
    return all_posts


def delete_post(post_id):
    """投稿を削除"""
    if DRY_RUN:
        print(f"  [ドライラン] 削除をシミュレート中... (ID: {post_id})")
        time.sleep(0.1)
        return True

    try:
        url = f'{API_BASE_URL}/{post_id}'
        params = {'access_token': ACCESS_TOKEN}

        response = requests.delete(url, params=params)
        response.raise_for_status()

        result = response.json()
        return result.get('success', False)

    except Exception as e:
        print(f"  ✗ 削除エラー: {e}")
        return False


def main():
    """メイン処理"""
    print("=" * 70)
    print("🗑️  Threads 投稿一括削除")
    if DRY_RUN:
        print("   [ドライランモード - 実際には削除されません]")
    print("=" * 70)
    print()

    # 全投稿を取得
    posts = get_all_posts()

    if not posts:
        print("\n削除する投稿がありません")
        return

    # 確認
    print(f"\n⚠️  {len(posts)} 件の投稿を削除します")

    if not DRY_RUN:
        # 確認なしで実行（--force フラグがある場合のみ）
        if '--force' not in sys.argv:
            print("\n実行するには --force フラグを付けてください")
            print("例: python3 delete_all_posts.py --force")
            return

        print("\n削除を開始します...")

    # 削除実行
    print("\n" + "=" * 70)
    print("🗑️  削除を開始します")
    print("=" * 70)

    success_count = 0
    fail_count = 0

    for i, post in enumerate(posts, 1):
        post_id = post.get('id')
        text_preview = post.get('text', '')[:50].replace('\n', ' ')

        print(f"\n[{i}/{len(posts)}] ID: {post_id}")
        print(f"本文: {text_preview}...")

        if delete_post(post_id):
            success_count += 1
            print("  ✓ 削除成功")
        else:
            fail_count += 1
            print("  ✗ 削除失敗")

        # レート制限対策（最後以外）
        if i < len(posts):
            time.sleep(1)

    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 削除完了")
    print("=" * 70)
    print(f"成功: {success_count} 件")
    print(f"失敗: {fail_count} 件")
    print("\n✅ 処理完了")


if __name__ == '__main__':
    main()
