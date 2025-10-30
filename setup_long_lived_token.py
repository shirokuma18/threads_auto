#!/usr/bin/env python3
"""
Threads API 長期トークン取得スクリプト

短期トークンから長期トークン（60日間有効）を取得し、
.envファイルに履歴と共に記録します。
"""

import requests
import sys
import os
from datetime import datetime, timedelta

def get_user_info(access_token):
    """アクセストークンからユーザー情報を取得"""
    url = "https://graph.threads.net/v1.0/me"
    params = {
        "fields": "id,username",
        "access_token": access_token
    }

    print("📋 ユーザー情報を取得中...")
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    user_id = data.get('id')
    username = data.get('username')

    print(f"✅ ユーザー情報取得成功")
    print(f"   User ID: {user_id}")
    print(f"   Username: @{username}")

    return user_id, username


def exchange_for_long_lived_token(short_token, app_secret):
    """短期トークンを長期トークン（60日間有効）に交換"""
    url = "https://graph.threads.net/access_token"
    params = {
        "grant_type": "th_exchange_token",
        "client_secret": app_secret,
        "access_token": short_token
    }

    print("\n🔄 長期トークンに交換中...")
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    long_lived_token = data.get('access_token')
    token_type = data.get('token_type')
    expires_in = data.get('expires_in')  # 秒単位

    # 有効期限を計算
    expires_in_days = expires_in // (24 * 3600) if expires_in else None
    expiry_date = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

    print(f"✅ 長期トークン取得成功")
    print(f"   Token Type: {token_type}")
    print(f"   有効期限: {expires_in_days}日間")
    if expiry_date:
        print(f"   期限日: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")

    return long_lived_token, expires_in_days, expiry_date


def update_env_file(short_token, user_id, username, long_token, expires_in_days, expiry_date):
    """/.envファイルを更新"""
    env_file = ".env"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')

    # 既存の.envを読み込む（存在する場合）
    existing_content = ""
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()

    # 新しいトークン情報を作成
    new_entry = f"""
# ================================================
# Token Update: {now}
# ================================================

# [1] 短期トークン取得 - {now}
THREADS_ACCESS_TOKEN_SHORT={short_token}

# [2] ユーザー情報取得 - {now}
THREADS_USER_ID={user_id}
THREADS_USERNAME={username}

# [3] 長期トークン取得 - {now}
# 有効期限: {expires_in_days}日間 (期限日: {expiry_date.strftime('%Y-%m-%d') if expiry_date else 'N/A'})
THREADS_ACCESS_TOKEN={long_token}

# ================================================
# 以下は過去の履歴
# ================================================
"""

    # .envファイルを更新
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(new_entry)
        if existing_content:
            # 既存の内容を履歴として追記
            f.write("\n")
            f.write(existing_content)

    print(f"\n✅ .envファイルを更新しました: {env_file}")


def main():
    print("=" * 70)
    print("Threads API 長期トークン取得スクリプト")
    print("=" * 70)

    # 短期トークンを入力
    if len(sys.argv) > 1:
        short_token = sys.argv[1]
    else:
        print("\n短期アクセストークンを入力してください:")
        short_token = input("> ").strip()

    if not short_token:
        print("❌ エラー: アクセストークンが入力されていません")
        sys.exit(1)

    # App Secretを入力
    if len(sys.argv) > 2:
        app_secret = sys.argv[2]
    else:
        print("\nMeta App の App Secret を入力してください:")
        print("(https://developers.facebook.com/apps/ > あなたのアプリ > Settings > Basic)")
        app_secret = input("> ").strip()

    if not app_secret:
        print("❌ エラー: App Secret が入力されていません")
        sys.exit(1)

    try:
        # ステップ1: ユーザー情報を取得
        user_id, username = get_user_info(short_token)

        # ステップ2: 長期トークンに交換
        long_token, expires_in_days, expiry_date = exchange_for_long_lived_token(short_token, app_secret)

        # ステップ3: .envファイルを更新
        update_env_file(short_token, user_id, username, long_token, expires_in_days, expiry_date)

        print("\n" + "=" * 70)
        print("✅ すべての処理が完了しました！")
        print("=" * 70)
        print("\n次のステップ:")
        print("1. GitHub Secrets を更新してください:")
        print(f"   - THREADS_ACCESS_TOKEN: {long_token[:20]}...")
        print(f"   - THREADS_USER_ID: {user_id}")
        print("\n2. GitHub リポジトリの Settings > Secrets and variables > Actions")
        print("   https://github.com/ibkuroyagi/threads_auto/settings/secrets/actions")
        print("\n3. .envファイルは機密情報を含むため、絶対にコミットしないでください")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ API エラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"エラー詳細: {error_detail}")
            except:
                print(f"レスポンス: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
