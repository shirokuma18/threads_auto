#!/usr/bin/env python3
"""
noteへの自動投稿スクリプト（Selenium使用）

警告:
- このスクリプトはSeleniumを使用してブラウザを自動操作します
- note側の仕様変更で動作しなくなる可能性があります
- 過度な自動投稿はnoteの利用規約に抵触する可能性があります
- 使用は自己責任でお願いします

事前準備:
1. Seleniumとブラウザドライバーのインストール
   pip install selenium webdriver-manager

2. note.comのログイン情報を環境変数に設定
   export NOTE_EMAIL="your-email@example.com"
   export NOTE_PASSWORD="your-password"

使い方:
    python3 note_auto_post.py note_articles/001_鈴の音.md
"""

import os
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class NoteAutoPoster:
    """note自動投稿クラス"""

    def __init__(self, headless=False):
        """初期化"""
        self.email = os.getenv('NOTE_EMAIL')
        self.password = os.getenv('NOTE_PASSWORD')

        if not self.email or not self.password:
            raise ValueError("NOTE_EMAILとNOTE_PASSWORDの環境変数を設定してください")

        # Chrome設定
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # ドライバー初期化
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """noteにログイン"""
        print("📝 noteにログイン中...")

        # ログインページを開く
        self.driver.get('https://note.com/login')
        time.sleep(2)

        try:
            # メールアドレス入力
            email_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, 'login_id'))
            )
            email_input.send_keys(self.email)

            # パスワード入力
            password_input = self.driver.find_element(By.NAME, 'password')
            password_input.send_keys(self.password)

            # ログインボタンをクリック
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()

            time.sleep(3)
            print("✓ ログイン成功")
            return True

        except Exception as e:
            print(f"✗ ログイン失敗: {e}")
            return False

    def create_article(self, title, content, tags=None):
        """記事を作成"""
        print(f"\n📄 記事作成中: {title}")

        try:
            # 新規記事作成ページを開く
            self.driver.get('https://note.com/post')
            time.sleep(2)

            # タイトル入力
            title_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="タイトル"]'))
            )
            title_input.send_keys(title)
            time.sleep(1)

            # 本文入力エリアをクリックして入力
            # noteのエディタは複雑なので、JavaScriptで直接入力
            self.driver.execute_script(
                f"document.querySelector('[contenteditable=\"true\"]').innerText = `{content}`"
            )
            time.sleep(2)

            print("✓ タイトルと本文を入力")

            # タグがあれば入力
            if tags:
                # TODO: タグ入力のセレクタを調整
                pass

            print("✓ 記事作成完了（下書き保存）")
            return True

        except Exception as e:
            print(f"✗ 記事作成失敗: {e}")
            return False

    def publish_article(self):
        """記事を公開"""
        print("\n📤 記事を公開中...")

        try:
            # 公開ボタンを探してクリック
            publish_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "公開")]'))
            )
            publish_button.click()
            time.sleep(2)

            # 公開設定で「無料」を選択（デフォルト）
            # 必要に応じて有料設定などを追加

            # 最終的な公開ボタンをクリック
            final_publish_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "公開する")]'))
            )
            final_publish_button.click()
            time.sleep(3)

            print("✓ 記事を公開しました")
            return True

        except Exception as e:
            print(f"✗ 公開失敗: {e}")
            return False

    def close(self):
        """ブラウザを閉じる"""
        self.driver.quit()


def parse_markdown_file(file_path):
    """Markdownファイルをパースしてタイトルと本文を取得"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 最初の # がタイトル
    lines = content.split('\n')
    title = ''
    body_lines = []

    for line in lines:
        if line.startswith('# ') and not title:
            title = line[2:].strip()
        elif title:
            body_lines.append(line)

    body = '\n'.join(body_lines).strip()

    return title, body


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 note_auto_post.py <markdown_file>")
        print("例: python3 note_auto_post.py note_articles/001_鈴の音.md")
        sys.exit(1)

    markdown_file = Path(sys.argv[1])
    if not markdown_file.exists():
        print(f"✗ ファイルが見つかりません: {markdown_file}")
        sys.exit(1)

    print("=" * 70)
    print("📝 note自動投稿")
    print("=" * 70)
    print()

    # Markdownファイルをパース
    title, content = parse_markdown_file(markdown_file)
    print(f"タイトル: {title}")
    print(f"本文: {len(content)}文字")
    print()

    # 自動投稿実行
    poster = None
    try:
        poster = NoteAutoPoster(headless=False)

        # ログイン
        if not poster.login():
            print("✗ ログインに失敗しました")
            sys.exit(1)

        # 記事作成
        if not poster.create_article(title, content):
            print("✗ 記事作成に失敗しました")
            sys.exit(1)

        # ユーザーに確認を求める
        response = input("\n記事を公開しますか？ (y/N): ")
        if response.lower() == 'y':
            if poster.publish_article():
                print("\n✅ 投稿完了！")
            else:
                print("\n⚠️  公開に失敗しました（下書きとして保存されています）")
        else:
            print("\n📌 下書きとして保存されました。手動で公開してください。")

    except Exception as e:
        print(f"\n✗ エラー: {e}")
        sys.exit(1)

    finally:
        if poster:
            time.sleep(2)
            poster.close()


if __name__ == '__main__':
    main()
