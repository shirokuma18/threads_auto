#!/usr/bin/env python3
"""
Threads プロフィール更新スクリプト

使用方法:
1. このスクリプトを編集して、PROFILE_BIOの内容を変更
2. python3 update_profile.py --dry-run で確認
3. python3 update_profile.py で実行
"""

import requests
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

# ===== ここを編集 =====
PROFILE_BIO = """あの頃の教室の匂い
忘れていた放課後の光

毎日更新される短編小説です
そっと覗いてみてください"""
# ====================


def get_current_profile():
    """現在のプロフィール情報を取得"""
    try:
        url = f'{API_BASE_URL}/{USER_ID}'
        params = {
            'fields': 'id,username,name,threads_profile_picture_url,threads_biography',
            'access_token': ACCESS_TOKEN
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"✗ プロフィール取得エラー: {e}")
        return None


def update_profile(bio):
    """プロフィールを更新

    注意: Threads APIでは現在、プロフィール更新機能が制限されている可能性があります。
    その場合は、Threadsアプリから手動で更新してください。
    """
    if DRY_RUN:
        print("[ドライラン] 実際には更新されません")
        print(f"\n更新予定のプロフィール:")
        print("-" * 70)
        print(bio)
        print("-" * 70)
        return True

    try:
        url = f'{API_BASE_URL}/{USER_ID}'
        params = {'access_token': ACCESS_TOKEN}
        data = {'biography': bio}

        response = requests.post(url, params=params, data=data)
        response.raise_for_status()

        print("✓ プロフィール更新成功！")
        return True

    except Exception as e:
        print(f"✗ プロフィール更新エラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"エラー詳細: {error_detail}")
            except:
                print(f"レスポンス: {e.response.text[:200]}")

        print("\n⚠️  Threads APIではプロフィール更新がサポートされていない可能性があります")
        print("その場合は、Threadsアプリから手動で更新してください:")
        print("1. Threadsアプリを開く")
        print("2. プロフィール画面を開く")
        print("3. 「プロフィールを編集」をタップ")
        print("4. 自己紹介欄を編集")
        return False


def main():
    print("=" * 70)
    print("📝 Threads プロフィール更新")
    if DRY_RUN:
        print("   [ドライランモード]")
    print("=" * 70)
    print()

    # 現在のプロフィールを取得
    print("現在のプロフィールを取得中...")
    current = get_current_profile()

    if current:
        print("\n現在のプロフィール:")
        print(f"ユーザー名: @{current.get('username', 'N/A')}")
        print(f"表示名: {current.get('name', 'N/A')}")
        print(f"自己紹介:")
        print("-" * 70)
        print(current.get('threads_biography', '(未設定)'))
        print("-" * 70)
    else:
        print("⚠️  現在のプロフィールを取得できませんでした")

    # プロフィールを更新
    print("\n新しいプロフィールに更新します...")
    update_profile(PROFILE_BIO)

    print("\n✅ 処理完了")


if __name__ == '__main__':
    main()
