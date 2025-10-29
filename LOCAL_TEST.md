# 🧪 ローカルでの動作確認ガイド

GitHub Actionsで実行する前に、ローカル環境で動作確認する方法を説明します。

---

## 📋 前提条件

- Python 3.7以上がインストールされていること
- Threads APIのアクセストークンとユーザーIDを取得済み

---

## ステップ1: 環境変数の設定（2分）

### 方法A: `.env`ファイルを使う（推奨）

1. `.env`ファイルを作成:

```bash
cp .env.example .env
```

2. `.env`ファイルを編集して、実際の値を設定:

```bash
# .env
THREADS_ACCESS_TOKEN=your_actual_token_here
THREADS_USER_ID=your_user_id_here
```

3. 環境変数を読み込む:

```bash
export $(cat .env | xargs)
```

### 方法B: 直接エクスポート

```bash
export THREADS_ACCESS_TOKEN='your_actual_token_here'
export THREADS_USER_ID='your_user_id_here'
```

### 確認

環境変数が設定されているか確認:

```bash
echo $THREADS_ACCESS_TOKEN
echo $THREADS_USER_ID
```

---

## ステップ2: 依存関係のインストール（1分）

```bash
pip install requests
```

または、requirements.txtがある場合:

```bash
pip install -r requirements.txt
```

---

## ステップ3: ドライラン（実際の投稿なし）

**重要**: まず本番投稿せずに動作確認しましょう！

### 3-1. スケジュールの確認

```bash
python threads_pdca.py --dry-run
```

これにより、以下が確認できます:
- ✅ 環境変数が正しく設定されているか
- ✅ CSVファイルが読み込めるか
- ✅ どの投稿が実行されるか（実際には投稿しません）

### 3-2. 出力例

```
======================================================================
Threads 予約投稿スクリプト (ドライランモード)
======================================================================

✓ 環境変数の確認
  - ACCESS_TOKEN: 設定済み (xxxx...で始まる)
  - USER_ID: 設定済み (12345678...)

✓ CSVファイルの読み込み
  - ファイル: posts_schedule.csv
  - 投稿数: 5件

投稿待ち: 2件

[ドライラン] 以下の投稿が実行されます:

[1/2] 投稿ID: 1
  スケジュール: 2025-10-29 20:00
  テキスト: おはようございます！今日も良い一日を 🌞
  → [実際には投稿されません]

[2/2] 投稿ID: 2
  スケジュール: 2025-10-29 22:00
  テキスト: ランチタイム。今日のお昼は何にしようかな 🍜
  → [実際には投稿されません]
```

---

## ステップ4: テスト投稿（1件だけ）

動作確認ができたら、1件だけテスト投稿してみましょう。

### 4-1. テスト用CSVを作成

```bash
# posts_schedule_test.csv
id,datetime,text
test1,2025-10-29 23:00,テスト投稿です。動作確認中 🧪
```

### 4-2. テスト実行

```bash
# 環境変数でテスト用CSVを指定
export CSV_FILE=posts_schedule_test.csv
python threads_pdca.py
```

または、スクリプトに直接指定:

```bash
python threads_pdca.py --csv posts_schedule_test.csv
```

---

## ステップ5: 各機能のテスト

### 5-1. PDCAレポート生成のテスト

```bash
python threads_pdca.py pdca
```

**注意**: 過去3日間に投稿がない場合、レポートは生成されません。

### 5-2. 次の投稿提案のテスト

```bash
python threads_pdca.py suggest
```

### 5-3. フルサイクルテスト

```bash
python threads_pdca.py full-cycle
```

---

## 📊 動作確認チェックリスト

実際にActionsで実行する前に、以下を確認してください:

- [ ] **環境変数**: `THREADS_ACCESS_TOKEN`と`THREADS_USER_ID`が設定されている
- [ ] **依存関係**: `requests`ライブラリがインストールされている
- [ ] **CSVファイル**: `posts_schedule.csv`が存在し、フォーマットが正しい
- [ ] **ドライラン**: `--dry-run`で投稿内容が正しく表示される
- [ ] **テスト投稿**: 1件のテスト投稿が成功する
- [ ] **投稿ログ**: `posted_log.json`が正しく生成される
- [ ] **PDCAレポート**: 過去の投稿があればレポートが生成される

---

## 🐛 トラブルシューティング

### エラー: "認証情報が設定されていません"

**原因**: 環境変数が設定されていない

**解決方法**:
```bash
# 環境変数が設定されているか確認
env | grep THREADS

# 設定されていなければ再度エクスポート
export THREADS_ACCESS_TOKEN='your_token'
export THREADS_USER_ID='your_user_id'
```

### エラー: "ModuleNotFoundError: No module named 'requests'"

**原因**: requestsライブラリがインストールされていない

**解決方法**:
```bash
pip install requests
```

### エラー: "No such file or directory: 'posts_schedule.csv'"

**原因**: CSVファイルが見つからない

**解決方法**:
```bash
# 現在のディレクトリを確認
pwd

# プロジェクトディレクトリに移動
cd /path/to/threads_auto

# CSVファイルが存在するか確認
ls -l posts_schedule.csv
```

### API エラー: "Invalid OAuth access token"

**原因**: アクセストークンが無効または期限切れ

**解決方法**:
1. [Meta for Developers](https://developers.facebook.com/)でトークンを再生成
2. 新しいトークンを環境変数に設定

### 投稿されない

**原因**: スケジュール時刻が未来の日時になっている

**解決方法**:
- CSVの`datetime`列を確認
- 現在時刻より過去の日時を設定（またはテスト時は現在時刻の数分後）

---

## 💡 ベストプラクティス

### 1. 段階的なテスト

```bash
# ステップ1: ドライラン
python threads_pdca.py --dry-run

# ステップ2: 1件テスト
python threads_pdca.py --csv posts_schedule_test.csv

# ステップ3: 本番スケジュール確認
python threads_pdca.py --dry-run

# ステップ4: 本番実行（または Actions に任せる）
```

### 2. ログファイルの確認

実行後、以下のファイルを確認:

```bash
# 投稿ログ
cat posted_log.json

# 分析データ（存在する場合）
cat analytics_data.csv

# PDCAレポート（生成された場合）
cat pdca_report.md
```

### 3. .gitignoreの設定

機密情報をコミットしないように:

```bash
# .gitignore に追加
.env
posted_log.json
analytics_data.csv
pdca_report.md
posts_schedule_test.csv
```

---

## 🚀 Actionsへの移行

ローカルでの動作確認が完了したら:

1. **環境変数をGitHub Secretsに設定**
   - Settings → Secrets and variables → Actions
   - `THREADS_ACCESS_TOKEN`と`THREADS_USER_ID`を追加

2. **CSVをリポジトリにプッシュ**
   ```bash
   git add posts_schedule.csv
   git commit -m "Add posts schedule"
   git push
   ```

3. **Actions タブで確認**
   - Actionsタブを開く
   - ワークフローが実行されているか確認
   - ログでエラーがないかチェック

---

## 📝 よくある質問

### Q1: ドライランモードでもAPI呼び出しが発生しますか？

**A**: いいえ、`--dry-run`では実際のAPI呼び出しは行われません。ローカルで安全にテストできます。

### Q2: テスト投稿はThreadsに表示されますか？

**A**: はい、`--dry-run`なしで実行すると実際に投稿されます。テストは非公開アカウントで行うか、テスト用の投稿を用意してください。

### Q3: ローカルとActionsで動作が異なる場合は？

**A**: 以下を確認:
- タイムゾーンの違い（ActionsはUTC）
- ファイルパスの違い
- 環境変数の設定

### Q4: 投稿時刻のテストはどうすればいい？

**A**: CSVの`datetime`を現在時刻の1-2分後に設定してテストしてください:
```csv
test1,2025-10-29 23:05,テスト投稿
```

---

## ✅ 準備完了の確認

以下のコマンドがすべて成功すれば準備完了です:

```bash
# 1. 環境変数の確認
env | grep THREADS

# 2. Pythonのバージョン確認
python --version

# 3. 依存関係の確認
python -c "import requests; print('requests OK')"

# 4. CSVファイルの確認
cat posts_schedule.csv

# 5. ドライラン
python threads_pdca.py --dry-run
```

すべて成功したら、GitHub Actionsでの自動実行に移行できます！

---

**質問があれば、Issueで聞いてください 💬**

Good luck! 🎯
