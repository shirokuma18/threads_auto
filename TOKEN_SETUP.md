# 🔑 Threads API トークンセットアップガイド

このガイドでは、短期トークンから長期トークン（60日間有効）を取得し、自動投稿を設定する手順を説明します。

---

## 📋 事前準備

### 1. Meta App を作成

1. https://developers.facebook.com/apps/ にアクセス
2. 「Create App」をクリック
3. App Type: **Business** を選択
4. App Name を入力して作成

### 2. Threads API を有効化

1. 作成したアプリのダッシュボードを開く
2. 左メニューから「Add Products」を選択
3. **Threads** を選択して「Set Up」
4. 権限を設定:
   - `threads_basic`
   - `threads_content_publish`

### 3. 必要な情報を取得

#### **App Secret を取得:**
1. 左メニュー「Settings」→「Basic」
2. **App Secret** をコピー（「Show」をクリックして表示）
   - ⚠️ この値は機密情報です。絶対に公開しないでください

#### **短期アクセストークンを取得:**
1. https://developers.facebook.com/tools/explorer/ にアクセス
2. 作成したアプリを選択
3. 「Generate Access Token」をクリック
4. 必要な権限を選択:
   - `threads_basic`
   - `threads_content_publish`
5. トークンをコピー

---

## 🚀 長期トークン取得手順

### ステップ1: スクリプトを実行

```bash
python3 setup_long_lived_token.py
```

### ステップ2: 情報を入力

スクリプトが以下を順番に聞いてきます：

1. **短期アクセストークン**
   ```
   短期アクセストークンを入力してください:
   > [Meta Graph API Explorer でコピーしたトークンを貼り付け]
   ```

2. **App Secret**
   ```
   Meta App の App Secret を入力してください:
   > [App Settings でコピーした App Secret を貼り付け]
   ```

### ステップ3: 自動処理

スクリプトが以下を自動で実行します：

1. ✅ ユーザー情報を取得（User ID, Username）
2. ✅ 長期トークンに交換（60日間有効）
3. ✅ `.env` ファイルに履歴と共に保存

**実行例:**
```
======================================================================
Threads API 長期トークン取得スクリプト
======================================================================

📋 ユーザー情報を取得中...
✅ ユーザー情報取得成功
   User ID: 1234567890
   Username: @your_username

🔄 長期トークンに交換中...
✅ 長期トークン取得成功
   Token Type: Bearer
   有効期限: 60日間
   期限日: 2025-12-29 10:35:00

✅ .envファイルを更新しました: .env

======================================================================
✅ すべての処理が完了しました！
======================================================================
```

---

## 📝 `.env` ファイルの形式

スクリプト実行後、`.env` ファイルに以下のように記録されます：

```env
# ================================================
# Token Update: 2025-10-30 10:35:00 JST
# ================================================

# [1] 短期トークン取得 - 2025-10-30 10:35:00 JST
THREADS_ACCESS_TOKEN_SHORT=THQVJNRk1...

# [2] ユーザー情報取得 - 2025-10-30 10:35:00 JST
THREADS_USER_ID=1234567890
THREADS_USERNAME=your_username

# [3] 長期トークン取得 - 2025-10-30 10:35:00 JST
# 有効期限: 60日間 (期限日: 2025-12-29)
THREADS_ACCESS_TOKEN=THAASu6I...

# ================================================
# 以下は過去の履歴
# ================================================
```

---

## 🔐 GitHub Secrets を更新

`.env` ファイルの情報を GitHub Secrets に登録します：

### 1. GitHub リポジトリの設定を開く

https://github.com/ibkuroyagi/threads_auto/settings/secrets/actions

### 2. 以下のシークレットを更新

| シークレット名 | 値 | 説明 |
|--------------|-----|------|
| `THREADS_ACCESS_TOKEN` | `.env` の `THREADS_ACCESS_TOKEN` の値 | 長期トークン（60日間有効） |
| `THREADS_USER_ID` | `.env` の `THREADS_USER_ID` の値 | あなたの Threads User ID |

### 3. 更新方法

1. 既存のシークレットをクリック
2. 「Update secret」をクリック
3. `.env` からコピーした値を貼り付け
4. 「Update secret」を保存

---

## ✅ 動作確認

### 1. GitHub Actions で手動実行

1. https://github.com/ibkuroyagi/threads_auto/actions にアクセス
2. 「Threads PDCA Automation」を選択
3. 「Run workflow」をクリック
4. Mode: `post` を選択
5. 実行

### 2. ログを確認

以下のログが表示されれば成功です：

```
✓ 環境変数の確認
  ✓ ACCESS_TOKEN: 設定済み (THAASu6I...)
  ✓ USER_ID: 設定済み (1234567890)

📅 現在時刻（JST）: 2025-10-30 10:35:00
✅ 投稿対象: 9件
時刻範囲: 2025-10-30 00:35 〜 2025-10-30 08:55

[1/9] 投稿ID: 30 | 2025-10-30 00:35 | [メンタル]
  → コンテナ作成中...
  ✓ 投稿成功！ (ID: 1234567890_1234567890)
```

---

## 🔄 トークンの自動チェック・更新

### 自動チェック機能（推奨）

このリポジトリには **トークンの自動チェック機能** が組み込まれています。

**実行スケジュール:**
- **毎週日曜日 20:00 JST** に自動実行
- トークンの有効性を確認
- 期限切れの場合は GitHub Issue で通知

**確認方法:**
1. https://github.com/ibkuroyagi/threads_auto/actions にアクセス
2. 「Token Auto-Refresh」ワークフローを確認
3. 実行結果のサマリーでトークンの状態を確認

### 手動更新のタイミング

長期トークンは **60日間** 有効です。

- **推奨:** 有効期限の **1週間前**
- **最遅:** 有効期限の **1日前**

### 手動更新の方法

1. 上記の手順で新しい短期トークンを取得
2. `python3 setup_long_lived_token.py` を再実行
3. GitHub Secrets を更新

### 期限切れ通知

トークンが期限切れになると：

1. ✉️ **GitHub Issue が自動作成されます**
   - タイトル: 🔑 Threads API トークンが期限切れです
   - ラベル: `token-expired`, `urgent`, `automation`

2. 📋 **対処手順が Issue に記載されます**
   - 新しいトークンの取得方法
   - GitHub Secrets の更新手順

3. ✅ **更新後、Issue をクローズ**

### カレンダーリマインダー設定

念のため、`.env` ファイルの期限日をカレンダーに登録しておくことをおすすめします。

---

## ⚠️ セキュリティ注意事項

### ❌ 絶対にやってはいけないこと

1. **`.env` ファイルをコミットしない**
   - すでに `.gitignore` に含まれています
   - 確認: `git status` で `.env` が表示されないこと

2. **トークンを公開しない**
   - GitHub Issues, Pull Requests, コメントなどに貼り付けない
   - スクリーンショットに写り込まないように注意

3. **App Secret を共有しない**
   - チームメンバーであっても、必要最小限の人にのみ共有

### ✅ セキュリティベストプラクティス

1. **定期的にトークンを更新**
   - 60日ごとに更新（有効期限前に）

2. **古いトークンは無効化**
   - Meta App の設定で古いトークンを無効化

3. **アクセスログを確認**
   - GitHub Actions のログで不審な活動がないか確認

---

## 🆘 トラブルシューティング

### エラー: "Error validating access token"

**原因:** トークンが無効または期限切れ

**解決策:**
1. 新しい短期トークンを取得
2. スクリプトを再実行
3. GitHub Secrets を更新

### エラー: "Invalid client_secret"

**原因:** App Secret が間違っている

**解決策:**
1. Meta App の Settings > Basic で正しい App Secret を確認
2. スクリプトを再実行

### エラー: "Permissions error"

**原因:** 必要な権限が付与されていない

**解決策:**
1. Meta Graph API Explorer で権限を確認
2. `threads_basic`, `threads_content_publish` を有効化
3. 新しいトークンを取得

---

## 📞 サポート

問題が解決しない場合は、以下を確認してください：

1. **Threads API ドキュメント**
   https://developers.facebook.com/docs/threads

2. **Meta for Developers サポート**
   https://developers.facebook.com/support/

3. **このリポジトリの Issues**
   https://github.com/ibkuroyagi/threads_auto/issues
