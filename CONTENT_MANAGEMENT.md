# 📝 投稿管理ガイド

このドキュメントでは、過去の投稿管理と新しい投稿の追加方法を説明します。

---

## 📊 ファイル構成と役割

### 1. posts_schedule.csv - 投稿マスターデータ

**役割:** これから投稿する内容のマスターデータ

**形式:**
```csv
id,datetime,text,category
30,2025-10-30 00:35,"私「深夜に目が覚めちゃった」...",メンタル
101,2025-10-30 07:15,"私「好きな人に既読スルーされた…」...",恋愛
```

**管理方法:**
- ✅ リポジトリにコミット
- ✅ 手動編集可能
- ✅ 差分が見える
- ✅ チーム開発で共有しやすい

---

### 2. threads.db - 実行時のデータベース

**役割:** ワークフロー実行時の状態管理

**場所:**
- ローカル環境（開発時）
- GitHub Actions キャッシュ（本番実行時）
- ❌ リポジトリには含まれない（.gitignore）

**内容:**
- posts テーブル: csv_id, scheduled_at, text, status, posted_at, threads_post_id
- status: 'pending' または 'posted'

**ライフサイクル:**
```
初回実行:
1. posts_schedule.csv からインポート
2. 全て status='pending'
3. キャッシュに保存

2回目以降:
1. キャッシュから復元
2. 投稿実行 → status='posted'
3. キャッシュに保存
```

---

### 3. posted_history.csv - 投稿履歴（推奨追加）

**役割:** 過去に投稿したものの永続的な記録

**形式:**
```csv
csv_id,posted_at,threads_post_id,category
30,2025-10-30 08:15:23,1234567890_post1,メンタル
101,2025-10-30 12:05:15,1234567890_post2,恋愛
```

**管理方法:**
- ✅ リポジトリにコミット
- ✅ GitHub Actions で自動更新
- ✅ 重複投稿の防止に使用
- ✅ 分析データとして活用可能

---

## 🆕 新しい投稿の追加方法

### 方法1: posts_schedule.csv を直接編集（推奨）

```bash
# 1. posts_schedule.csv を編集
# 新しい行を追加
echo "999,2025-11-01 12:00,新しい投稿内容,恋愛" >> posts_schedule.csv

# 2. コミット・プッシュ
git add posts_schedule.csv
git commit -m "Add new post for 2025-11-01 12:00"
git push

# 3. 次回のワークフロー実行時に自動的に投稿される
```

**注意点:**
- csv_id は一意にする（既存IDと重複しない）
- datetime は JST で指定
- category は正確に指定（恋愛、仕事、お金、メンタル、占い、その他）

---

### 方法2: スクリプトで追加

```bash
# 既存のDBに投稿を追加（ローカル開発時）
sqlite3 threads.db <<SQL
INSERT INTO posts (csv_id, scheduled_at, text, category, status)
VALUES (999, '2025-11-01 12:00:00', '新しい投稿内容', '恋愛', 'pending');
SQL

# CSVにエクスポート（同期）
python3 threads_sqlite.py export --csv posts_schedule.csv

# コミット
git add posts_schedule.csv
git commit -m "Add new post"
git push
```

---

## 📋 過去の投稿の管理

### 投稿履歴の確認

**ローカル環境:**
```bash
# DBから投稿履歴を確認
sqlite3 threads.db "SELECT csv_id, posted_at, status, category FROM posts WHERE status='posted' ORDER BY posted_at DESC LIMIT 10"

# 今日の投稿を確認
sqlite3 threads.db "SELECT csv_id, posted_at, substr(text, 1, 50) FROM posts WHERE DATE(posted_at) = date('now', '+9 hours')"
```

**GitHub Actions ログ:**
```
https://github.com/ibkuroyagi/threads_auto/actions
→ 各ワークフロー実行のログを確認
→ 「投稿成功！ (ID: xxxxxxxxx)」で確認
```

---

### posted_history.csv の活用

**投稿後に自動的に記録:**

ワークフローに以下を追加することで、投稿履歴をリポジトリに保存できます：

```yaml
- name: 投稿履歴を更新
  run: |
    # DBから今日のposted投稿を抽出
    sqlite3 threads.db -header -csv \
      "SELECT csv_id, posted_at, threads_post_id, category FROM posts WHERE status='posted' AND DATE(posted_at) = date('now', '+9 hours')" \
      >> posted_history.csv

    # 重複を削除してソート
    sort -u posted_history.csv -o posted_history.csv

    # コミット
    if ! git diff --quiet posted_history.csv; then
      git config user.email "github-actions[bot]@users.noreply.github.com"
      git config user.name "github-actions[bot]"
      git add posted_history.csv
      git commit -m "Update posting history [skip ci]"
      git push
    fi
```

**メリット:**
- ✅ テキストベース（差分が見える）
- ✅ 永続的な記録
- ✅ 分析に活用できる
- ✅ git pull で問題なし

---

## 🔍 重複投稿の防止

### 現在の仕組み（キャッシュベース）

```
1. キャッシュから threads.db を復元
2. status='posted' の投稿はスキップ
3. 重複は防止される

問題:
- キャッシュが消えると重複投稿の可能性
- 7日間はキャッシュが保持されるので実質問題なし
```

### 改善案（posted_history.csv を使用）

```python
# threads_sqlite.py に追加
def check_already_posted(csv_id):
    """posted_history.csv をチェック"""
    with open('posted_history.csv', 'r') as f:
        reader = csv.DictReader(f)
        posted_ids = {row['csv_id'] for row in reader}
    return csv_id in posted_ids

# 投稿前にチェック
if check_already_posted(csv_id):
    print(f"  ⚠️  すでに投稿済み (csv_id: {csv_id})")
    continue
```

---

## 🗂️ ファイル管理のベストプラクティス

### リポジトリに含めるもの

```
threads_auto/
├── posts_schedule.csv      ✅ マスターデータ
├── posted_history.csv       ✅ 投稿履歴（推奨）
├── threads_sqlite.py        ✅ スクリプト
├── .github/workflows/       ✅ ワークフロー
├── .gitignore              ✅ 除外設定
└── README.md               ✅ ドキュメント
```

### リポジトリから除外するもの（.gitignore）

```
# データベース（実行時に生成）
threads.db
threads.db-*

# 環境変数（機密情報）
.env

# 一時ファイル
posted_log.json
analytics_data.csv
*.pyc
__pycache__/
```

---

## 📝 運用フロー

### 日常の運用

```
1. 新しい投稿を追加したい
   → posts_schedule.csv を編集
   → git commit & push

2. 投稿履歴を確認したい
   → posted_history.csv を確認
   → または GitHub Actions ログを確認

3. 過去の投稿を分析したい
   → posted_history.csv を使用
   → PDCAレポートを確認
```

### トラブル時の対応

**キャッシュが消えた:**
```
→ 次回実行時に CSVから自動的に再構築
→ posted_history.csv があれば重複チェック可能
```

**間違った投稿をしてしまった:**
```
→ Threads の Web UI で削除
→ posts_schedule.csv から削除
→ posted_history.csv から削除（手動）
```

**投稿が重複した:**
```
→ posted_history.csv を確認
→ 重複したエントリを削除
→ 次回から重複チェック機能を有効化
```

---

## 🎯 推奨される改善実装

### ステップ1: posted_history.csv の導入

1. ファイルを作成:
```bash
echo "csv_id,posted_at,threads_post_id,category" > posted_history.csv
git add posted_history.csv
git commit -m "Add posting history file"
```

2. ワークフローに履歴記録を追加（上記参照）

3. threads_sqlite.py に重複チェック機能を追加

---

### ステップ2: 新規投稿の自動取り込み

posts_schedule.csv が更新されたら、自動的に threads.db に反映：

```python
def sync_from_csv():
    """CSVから新規投稿を取り込む"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 既存のcsv_idを取得
    cursor.execute("SELECT csv_id FROM posts")
    existing_ids = {row[0] for row in cursor.fetchall()}

    # CSVを読み込み
    with open('posts_schedule.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] not in existing_ids:
                # 新規投稿を追加
                cursor.execute(...)
                print(f"📝 新規投稿を追加: {row['id']}")

    conn.commit()
    conn.close()
```

---

## 📚 まとめ

**現在の設計:**
- ✅ threads.db はキャッシュのみ（リポジトリに含めない）
- ✅ posts_schedule.csv で投稿を管理
- ⚠️ 投稿履歴の永続化が不十分

**推奨される改善:**
- ✅ posted_history.csv を追加
- ✅ 投稿後に自動的に履歴を記録
- ✅ 重複チェック機能を実装

**メリット:**
- ✅ 開発体験が向上（git pull で問題なし）
- ✅ リポジトリサイズが増えない
- ✅ 投稿履歴が永続的に保持される
- ✅ テキストベースで管理が容易
