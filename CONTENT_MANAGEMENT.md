# 📝 コンテンツ管理ガイド

このドキュメントでは、投稿の追加、管理、分析の方法を説明します。

---

## 📊 ファイル構成と役割

### 1. posts_schedule.csv - 予約投稿マスターデータ

**役割:** これから投稿する内容のマスターデータ（唯一の情報源）

**形式:**
```csv
id,datetime,text,status,category
101,2025-11-03 08:00,"私「好きな人に既読スルーされた…」...",pending,恋愛
102,2025-11-03 12:00,"私「転職活動を始めた」...",pending,仕事
```

**管理方法:**
- ✅ リポジトリにコミット（git追跡）
- ✅ 手動編集可能
- ✅ 差分が見える
- ✅ チーム開発で共有しやすい
- ✅ **投稿後は自動削除される**（常に最新の予約のみ）

**特徴:**
- 投稿が完了すると、GitHub Actionsが自動的にその行を削除
- 常に「未投稿の予約」のみが記録される
- これにより、ファイルサイズが増えない

---

### 2. posted_history.csv - 投稿履歴（重複防止用）

**役割:** 投稿済みのIDを記録し、重複投稿を防止

**形式:**
```csv
csv_id,posted_at
30,2025-10-30 08:15:23
101,2025-10-30 12:05:15
102,2025-10-30 12:10:30
```

**管理方法:**
- ✅ リポジトリにコミット（git追跡）
- ✅ GitHub Actionsで自動更新
- ✅ **重複投稿の防止に使用**
- ✅ 最小限のデータ（csv_id, posted_at のみ）

**役割:**
1. **重複防止:** キャッシュが消えても重複投稿しない
2. **投稿履歴:** 何をいつ投稿したかの記録
3. **軽量:** テキストのみで容量を圧迫しない

---

### 3. threads.db - 実行時データベース（キャッシュ）

**役割:** ワークフロー実行時の状態管理

**場所:**
- ローカル環境（開発時）
- GitHub Actionsキャッシュ（本番実行時）
- ❌ **リポジトリには含まれない**（.gitignore）

**内容:**
- posts テーブル: csv_id, scheduled_at, text, status, posted_at, threads_post_id
- status: 'pending' または 'posted'

**ライフサイクル:**
```
初回実行:
1. posts_schedule.csv からインポート
2. 全て status='pending'
3. GitHub Actionsキャッシュに保存

2回目以降:
1. キャッシュから復元
2. 投稿実行 → status='posted'
3. キャッシュに保存

キャッシュ消失時:
1. CSVから再インポート
2. posted_history.csv で重複チェック
3. 重複を除いて投稿
```

**特徴:**
- リポジトリに含まれないため、git競合が発生しない
- 開発環境でgit pullが不要
- キャッシュは7日間保持される

---

## 🆕 新しい投稿の追加方法

### 方法1: posts_schedule.csv を直接編集（推奨）

```bash
# 1. posts_schedule.csv を開いて新しい行を追加
vi posts_schedule.csv

# CSVの例:
# id,datetime,text,status,category
# 103,2025-11-03 08:00,"投稿テキスト...",pending,恋愛

# 2. コミット・プッシュ
git add posts_schedule.csv
git commit -m "Add: 新しい投稿を追加"
git push

# 3. 次回のワークフロー実行時に自動的に投稿される
```

**注意点:**
- **csv_id は一意にする** - 既存IDと重複しない数字を使用
- **datetime は JST で指定** - 例: 2025-11-03 08:00
- **status は 'pending' に設定**
- **category は正確に指定** - 恋愛、仕事、お金、メンタル、占い

**推奨IDの決め方:**
```bash
# 現在の最大IDを確認
tail -1 posts_schedule.csv | cut -d',' -f1

# 出力例: 102
# → 次のIDは 103 を使用
```

---

### 方法2: コマンドラインで一行追加

```bash
# 新しい投稿を追加（エスケープに注意）
echo '103,2025-11-03 12:00,"投稿テキストここに...",pending,仕事' >> posts_schedule.csv

# コミット・プッシュ
git add posts_schedule.csv
git commit -m "Add: 仕事カテゴリの投稿"
git push
```

---

### 方法3: スクリプトで一括追加

複数の投稿を一度に追加する場合:

```bash
# ローカルでDBを初期化
python3 migrate_to_sqlite.py init

# CSVから既存投稿をインポート
python3 threads_sqlite.py import --csv posts_schedule.csv

# スクリプトで新規投稿を追加
python3 threads_sqlite.py add \
  --datetime "2025-11-03 18:00" \
  --text "私「今日も疲れた...」友人「お疲れ様！」..." \
  --category "メンタル"

# DBからCSVにエクスポート
python3 threads_sqlite.py export --output posts_schedule.csv --status pending

# コミット
git add posts_schedule.csv
git commit -m "Add: 複数投稿を追加"
git push
```

---

## 📋 投稿の管理

### 投稿スケジュールの確認

**posts_schedule.csv を確認:**
```bash
# 全ての予約を表示
cat posts_schedule.csv

# 件数を確認
wc -l posts_schedule.csv

# 今日の投稿を確認（macOS）
TODAY=$(date '+%Y-%m-%d')
grep "$TODAY" posts_schedule.csv
```

**ローカルDBで確認（開発時）:**
```bash
# DBを初期化
python3 migrate_to_sqlite.py init
python3 threads_sqlite.py import --csv posts_schedule.csv

# 今日の投稿を確認
sqlite3 threads.db "SELECT csv_id, scheduled_at, category FROM posts WHERE DATE(scheduled_at) = date('now', '+9 hours') ORDER BY scheduled_at"

# 投稿総数を確認
sqlite3 threads.db "SELECT COUNT(*) FROM posts WHERE status='pending'"
```

---

### 投稿履歴の確認

**posted_history.csv を確認:**
```bash
# 全ての投稿履歴を表示
cat posted_history.csv

# 総投稿数を確認
tail -n +2 posted_history.csv | wc -l

# 今日の投稿を確認
TODAY=$(date '+%Y-%m-%d')
grep "$TODAY" posted_history.csv
```

**GitHub Actions ログを確認:**
```
https://github.com/ibkuroyagi/threads_auto/actions
→ 各ワークフロー実行のログを確認
→ 「投稿成功！ (ID: xxxxxxxxx)」で確認
```

---

## 🔄 投稿後の自動処理

### GitHub Actionsでの自動処理フロー

ワークフローが実行されると、以下の処理が自動で行われます:

```yaml
1. キャッシュからDBを復元
   └─ threads.db を復元（前回の投稿状態を保持）

2. 投稿実行
   └─ python3 threads_sqlite.py post

3. 投稿履歴を更新
   ├─ 投稿済みの csv_id を posted_history.csv に追記
   └─ 重複を削除してソート

4. 投稿済みをCSVから削除
   ├─ posts_schedule.csv から投稿済みの行を削除
   └─ 未投稿の予約のみ残す

5. 変更を自動コミット
   ├─ posted_history.csv の更新
   ├─ posts_schedule.csv のクリーンアップ
   └─ git push（[skip ci] 付き）

6. DBをキャッシュに保存
   └─ 次回実行時に使用
```

**メリット:**
- ✅ posts_schedule.csv は常に最新の予約のみ
- ✅ posted_history.csv で重複防止
- ✅ 手動でのファイル管理が不要
- ✅ git pull しても問題なし

---

## 🔍 重複投稿の防止

### 2層の重複チェック

システムは2つの方法で重複投稿を防ぎます:

**1. DB状態チェック:**
```python
# threads.db の status で判定
SELECT * FROM posts WHERE status='pending'
# status='posted' の投稿は取得されない
```

**2. CSV履歴チェック:**
```python
# posted_history.csv で判定
if csv_id in posted_ids:
    print(f"  ⚠️  すでに投稿済み")
    mark_as_posted(post_id, f"duplicate_{csv_id}")
    continue
```

**重複防止の動作:**
```
キャッシュが有効な場合:
└─ DB の status='posted' で判定 → 重複なし

キャッシュが消失した場合:
├─ CSVから再インポート（全て status='pending'）
└─ posted_history.csv で判定 → 重複なし
```

これにより、**キャッシュが消えても重複投稿しません**。

---

## 🧹 投稿の削除・修正

### 未投稿の予約を削除

```bash
# 1. posts_schedule.csv から該当行を削除
vi posts_schedule.csv

# 2. コミット
git add posts_schedule.csv
git commit -m "Remove: 不要な投稿を削除"
git push
```

### 未投稿の予約を修正

```bash
# 1. posts_schedule.csv を編集
vi posts_schedule.csv

# 2. コミット
git add posts_schedule.csv
git commit -m "Update: 投稿内容を修正"
git push
```

### 投稿済みを削除（取り消し）

投稿済みの場合は、Threadsから直接削除する必要があります:

```bash
# 1. Threads の Web UI で投稿を削除
# https://www.threads.net/@your_username

# 2. posted_history.csv から該当行を削除（手動）
vi posted_history.csv

# 3. コミット
git add posted_history.csv
git commit -m "Fix: 誤投稿の履歴を削除"
git push
```

---

## 📊 ローカル分析

### 分析スクリプトの実行

Threads APIを使って過去の投稿を分析できます:

```bash
# 環境変数を読み込み
export $(cat .env | xargs)

# 分析実行（最新20件の投稿を分析）
python3 analyze_local.py
```

### 生成されるファイル

分析結果はローカルのみに保存されます（`.gitignore`に含まれる）:

```
analysis_results.json  - 詳細な分析データ
analysis_report.md     - 人間が読みやすいレポート
```

### 分析結果の活用

```bash
# 1. レポートを確認
open analysis_report.md

# 2. 反応が良かった投稿の特徴を分析
#    - エンゲージメント率 TOP 5
#    - いいね数 TOP 5
#    - カテゴリ別パフォーマンス

# 3. 新しい投稿を posts_schedule.csv に追加
vi posts_schedule.csv

# 4. デプロイ
git add posts_schedule.csv
git commit -m "Add: 分析結果を反映した新規投稿"
git push
```

**分析結果はGitにコミットしません:**
- ✅ `.gitignore`に含まれる
- ✅ ローカルのみで参照
- ✅ リポジトリサイズに影響しない

---

## 🗂️ ファイル管理のベストプラクティス

### リポジトリに含めるもの

```
threads_auto/
├── posts_schedule.csv       ✅ 予約投稿マスターデータ
├── posted_history.csv        ✅ 投稿履歴（重複防止）
├── threads_sqlite.py         ✅ スクリプト
├── setup_long_lived_token.py ✅ トークン管理
├── analyze_local.py          ✅ 分析スクリプト
├── migrate_to_sqlite.py      ✅ DB初期化
├── check_db_size.py          ✅ ユーティリティ
├── .github/workflows/        ✅ ワークフロー
├── .gitignore               ✅ 除外設定
├── README.md                ✅ ドキュメント
└── ドキュメント類            ✅ 各種ガイド
```

### リポジトリから除外するもの（.gitignore）

```
# データベース（GitHub Actionsキャッシュで管理）
threads.db
threads.db-*

# 環境変数（機密情報）
.env

# ローカル分析結果（機密）
analysis_results.json
analysis_report.md

# 実行時に生成されるファイル
posted_log.json
analytics_data.csv
pdca_report.md
competitor_analytics.csv
competitor_report.md

# Python関連
__pycache__/
*.pyc
```

---

## 📝 日常の運用フロー

### 1. 新しい投稿を追加

```bash
# posts_schedule.csv を編集
vi posts_schedule.csv

# コミット・プッシュ
git add posts_schedule.csv
git commit -m "Add: 新規投稿"
git push

# → 次回の実行時に自動投稿される
```

### 2. 投稿履歴を確認

```bash
# posted_history.csv を確認
cat posted_history.csv | tail -10

# または GitHub Actions ログを確認
# https://github.com/ibkuroyagi/threads_auto/actions
```

### 3. 過去の投稿を分析

```bash
# ローカルで分析実行
export $(cat .env | xargs)
python3 analyze_local.py

# レポートを確認
open analysis_report.md

# 反応の良い投稿を参考に新規作成
```

### 4. トークンを更新（60日ごと）

```bash
# 長期トークンを取得
python3 setup_long_lived_token.py

# GitHub Secretsを更新
# https://github.com/ibkuroyagi/threads_auto/settings/secrets/actions
```

---

## 🔧 トラブルシューティング

### 投稿が実行されない

```bash
# 1. posts_schedule.csv を確認
cat posts_schedule.csv

# 2. datetime が現在時刻より過去か確認
date

# 3. status が 'pending' か確認
grep "pending" posts_schedule.csv

# 4. GitHub Actionsログを確認
# https://github.com/ibkuroyagi/threads_auto/actions
```

### 重複投稿が発生した

```bash
# 1. posted_history.csv を確認
cat posted_history.csv

# 2. 該当する csv_id が記録されているか確認
grep "csv_id" posted_history.csv

# 3. 記録されていない場合は手動で追加
echo "csv_id,posted_at" >> posted_history.csv
echo "101,2025-11-01 08:15:23" >> posted_history.csv

# 4. コミット
git add posted_history.csv
git commit -m "Fix: 重複投稿の履歴を追加"
git push
```

### キャッシュが無効になった

通常は自動でリカバリーされますが、手動で確認したい場合:

```bash
# ローカルでDBを初期化
python3 migrate_to_sqlite.py init
python3 threads_sqlite.py import --csv posts_schedule.csv

# 状態を確認
sqlite3 threads.db "SELECT COUNT(*), status FROM posts GROUP BY status"
```

---

## 📚 まとめ

**現在の設計:**
- ✅ threads.db はキャッシュのみ（リポジトリに含めない）
- ✅ posts_schedule.csv で予約を管理（投稿後は自動削除）
- ✅ posted_history.csv で投稿履歴を管理（重複防止）
- ✅ 分析結果はローカル保存（リポジトリに含めない）

**メリット:**
- ✅ 開発体験が向上（git pull で問題なし）
- ✅ リポジトリサイズが増えない
- ✅ 投稿履歴が永続的に保持される
- ✅ 重複投稿が確実に防止される
- ✅ テキストベースで管理が容易

**運用のポイント:**
- 新規投稿は posts_schedule.csv に追加
- 投稿履歴は自動更新される
- 分析結果を参考に次の投稿を作成
- 60日ごとにトークンを更新
