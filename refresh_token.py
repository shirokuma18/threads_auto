#!/usr/bin/env python3
"""
Threads API トークン自動更新スクリプト

長期トークンをリフレッシュして、さらに60日間有効な新しいトークンを取得します。
GitHub Actions で定期実行することで、トークン切れを防ぎます。
"""

import requests
import sys
import os
import json
from datetime import datetime, timedelta

def get_token_info(access_token):
    """トークンの有効期限情報を取得（デバッグ用）"""
    url = "https://graph.threads.net/v1.0/me"
    params = {
        "fields": "id,username",
        "access_token": access_token
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('id'), data.get('username')
    except requests.exceptions.RequestException as e:
        return None, None


def refresh_long_lived_token(current_token):
    """
    長期トークンをリフレッシュして新しい長期トークン（60日間）を取得

    注意: この機能はThreads API v1.0では現在サポートされていない可能性があります。
    その場合は、定期的に手動でトークンを再生成する必要があります。
    """
    url = "https://graph.threads.net/access_token"
    params = {
        "grant_type": "th_refresh_token",
        "access_token": current_token
    }

    print("🔄 トークンをリフレッシュ中...")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        new_token = data.get('access_token')
        expires_in = data.get('expires_in')

        if not new_token:
            print("⚠️  新しいトークンが取得できませんでした")
            return None, None

        expires_in_days = expires_in // (24 * 3600) if expires_in else None
        expiry_date = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

        print(f"✅ トークンリフレッシュ成功")
        print(f"   有効期限: {expires_in_days}日間")
        if expiry_date:
            print(f"   期限日: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")

        return new_token, expiry_date

    except requests.exceptions.RequestException as e:
        print(f"⚠️  トークンリフレッシュ失敗: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = error_detail.get('error', {}).get('message', '')
                print(f"   エラー詳細: {error_msg}")

                # リフレッシュがサポートされていない場合
                if 'unsupported' in error_msg.lower() or 'invalid' in error_msg.lower():
                    print("\n❌ Threads API ではトークンの自動リフレッシュが")
                    print("   サポートされていない可能性があります。")
                    print("\n📝 対処方法:")
                    print("   1. setup_long_lived_token.py を定期実行")
                    print("   2. 新しい短期トークンを手動で取得")
                    print("   3. GitHub Secrets を更新")
            except:
                print(f"   レスポンス: {e.response.text[:200]}")

        return None, None


def update_github_secret(secret_name, secret_value):
    """
    GitHub Secrets を更新（GitHub CLI 使用）

    注意: GitHub Actions の GITHUB_TOKEN には Secrets 更新権限がないため、
    Personal Access Token (PAT) が必要です。
    """
    # この機能は現在コメントアウト
    # 理由: GitHub Actions の GITHUB_TOKEN では Secrets を更新できない
    # 代わりに、定期的に手動で更新するか、別の方法を検討
    pass


def update_env_file(new_token, expiry_date, user_id, username):
    """/.envファイルにリフレッシュ履歴を追記"""
    env_file = ".env"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')

    # 既存の.envを読み込む
    existing_content = ""
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()

    # リフレッシュエントリを作成
    refresh_entry = f"""
# ================================================
# Token Refresh: {now}
# ================================================

# トークンリフレッシュ - {now}
# 有効期限: 60日間 (期限日: {expiry_date.strftime('%Y-%m-%d') if expiry_date else 'N/A'})
THREADS_ACCESS_TOKEN={new_token}
THREADS_USER_ID={user_id}
THREADS_USERNAME={username}

# ================================================
# 以下は過去の履歴
# ================================================
"""

    # .envファイルを更新
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(refresh_entry)
        if existing_content:
            f.write("\n")
            f.write(existing_content)

    print(f"\n✅ .envファイルを更新しました")


def check_token_validity(access_token):
    """トークンが有効かチェック"""
    print("🔍 トークンの有効性をチェック中...")

    user_id, username = get_token_info(access_token)

    if user_id:
        print(f"✅ トークンは有効です")
        print(f"   User ID: {user_id}")
        print(f"   Username: @{username}")
        return True, user_id, username
    else:
        print("❌ トークンが無効です")
        return False, None, None


def main():
    print("=" * 70)
    print("Threads API トークン自動更新スクリプト")
    print("=" * 70)

    # 環境変数からトークンを取得
    current_token = os.getenv('THREADS_ACCESS_TOKEN')

    if not current_token:
        print("\n❌ エラー: THREADS_ACCESS_TOKEN 環境変数が設定されていません")
        print("\n.envファイルを確認するか、環境変数を設定してください:")
        print("  export THREADS_ACCESS_TOKEN=your_token_here")
        sys.exit(1)

    print(f"\n現在のトークン: {current_token[:20]}...")

    # トークンの有効性をチェック
    is_valid, user_id, username = check_token_validity(current_token)

    if not is_valid:
        print("\n❌ 現在のトークンが無効です。")
        print("\n📝 対処方法:")
        print("   python3 setup_long_lived_token.py を実行して")
        print("   新しいトークンを取得してください。")
        sys.exit(1)

    # トークンをリフレッシュ
    new_token, expiry_date = refresh_long_lived_token(current_token)

    if not new_token:
        print("\n⚠️  トークンのリフレッシュに失敗しました")
        print("\n📋 Threads API の仕様:")
        print("   現在、Threads API では自動リフレッシュが")
        print("   サポートされていない可能性があります。")
        print("\n📝 推奨される対処方法:")
        print("   1. 有効期限が近づいたら GitHub Actions で通知")
        print("   2. setup_long_lived_token.py で新しいトークンを取得")
        print("   3. GitHub Secrets を手動で更新")
        sys.exit(1)

    # .envファイルを更新
    update_env_file(new_token, expiry_date, user_id, username)

    print("\n" + "=" * 70)
    print("✅ トークンのリフレッシュが完了しました！")
    print("=" * 70)
    print("\n次のステップ:")
    print("1. GitHub Secrets を更新してください:")
    print(f"   - THREADS_ACCESS_TOKEN: {new_token[:20]}...")
    print(f"   - THREADS_USER_ID: {user_id}")
    print("\n2. 更新先:")
    print("   https://github.com/ibkuroyagi/threads_auto/settings/secrets/actions")

    # 出力ファイルに情報を保存（GitHub Actions 用）
    output_file = os.getenv('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"new_token={new_token}\n")
            f.write(f"user_id={user_id}\n")
            f.write(f"expiry_date={expiry_date.strftime('%Y-%m-%d') if expiry_date else ''}\n")
            f.write(f"needs_manual_update=false\n")


if __name__ == "__main__":
    main()
