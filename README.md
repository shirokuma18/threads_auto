# 🚀 Threads自動投稿 + PDCA分析ツール

Threads APIを使った予約投稿とPDCA分析を自動化するツール（SQLite版）

## 📋 目次

- [特徴](#特徴)
- [セットアップ](#セットアップ)
- [使い方](#使い方)
- [投稿管理](#投稿管理)
- [PDCA分析](#pdca分析)
- [ディレクトリ構成](#ディレクトリ構成)
- [CSVからの移行](#csvからの移行)

---

## ✨ 特徴

### コア機能
- **SQLiteベースの投稿管理** - 大量の投稿も高速処理
- **予約投稿** - 指定時刻に自動投稿
- **PDCA分析** - エンゲージメント分析とレポート自動生成
- **投稿ステータス管理** - pending / posted / failed
- **カテゴリ自動検出** - 恋愛、仕事、お金、メンタル、占い
- **ドライランモード** - 実際に投稿せずにテスト可能

### SQLite移行のメリット
- ✅ 9,000件以上の投稿でも高速
- ✅ 未投稿のみをクエリで取得
- ✅ SQLで高度な分析が可能
- ✅ データの整合性とトランザクション
- ✅ CSVインポート/エクスポート可能

---

## 🛠️ セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd threads_auto
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. Threads API認証情報の取得

1. [Meta for Developers](https://developers.facebook.com/)にアクセス
2. アプリを作成
3. Threads APIを有効化
4. アクセストークンとユーザーIDを取得

### 4. 環境変数の設定

```bash
cp .env.example .env
```

`.env`ファイルを編集:

```bash
THREADS_ACCESS_TOKEN=your_access_token_here
THREADS_USER_ID=your_user_id_here
```

### 5. データベースの初期化

**既存CSVがある場合（マイグレーション）:**

```bash
python3 migrate_to_sqlite.py full
```

**新規セットアップの場合:**

```bash
python3 migrate_to_sqlite.py init
```

---

## 🚀 使い方

### 投稿実行

```bash
# 投稿時刻になった投稿を自動実行
python3 threads_sqlite.py post

# ドライランモード（実際には投稿しない）
python3 threads_sqlite.py post --dry-run
```

### 投稿一覧

```bash
# 全投稿を表示
python3 threads_sqlite.py list

# 未投稿のみ
python3 threads_sqlite.py list --status pending

# 今日の予定
python3 threads_sqlite.py list --today

# 明日の予定
python3 threads_sqlite.py list --tomorrow

# 表示件数を指定
python3 threads_sqlite.py list --limit 10
```

---

## 📝 投稿管理

### 投稿を追加

```bash
python3 threads_sqlite.py add \
  --datetime "2025-11-02 08:00" \
  --text "私「最近...」友人「...」" \
  --category "恋愛"
```

### CSVからインポート

```bash
python3 threads_sqlite.py import --csv new_posts.csv
```

**CSVフォーマット:**

```csv
id,datetime,text,status,category
1,2025-11-01 08:00,"投稿テキスト",pending,恋愛
2,2025-11-01 12:00,"投稿テキスト",pending,仕事
```

### CSVにエクスポート

```bash
# 全投稿をエクスポート
python3 threads_sqlite.py export --output backup.csv

# 未投稿のみエクスポート
python3 threads_sqlite.py export --output pending.csv --status pending
```

---

## 📊 PDCA分析

### 基本的な使い方

```bash
# 過去3日間のPDCAレポートを生成
python3 threads_sqlite.py pdca

# カスタム期間
python3 threads_sqlite.py pdca --days 7
```

### レポート内容

生成されるレポート（`pdca_report.md`）には以下が含まれます:

- 📈 **サマリー** - 総表示回数、エンゲージメント率
- 🏆 **トップパフォーマンス投稿** - 反応が良かった投稿
- 🎯 **カテゴリ別パフォーマンス** - どのテーマが効果的か
- ⏰ **ベスト投稿時間帯** - 最も反応が良い時間
- 📝 **コンテンツ分析** - 文字数、絵文字の効果
- ⚠️ **改善が必要な投稿** - 反応が悪かった投稿
- 💡 **次のアクションプラン** - Keep/Improve/Try

---

## 📁 ディレクトリ構成

```
threads_auto/
├── README.md                    # このファイル
├── requirements.txt             # Python依存関係
├── .env                         # 環境変数（要作成）
├── .gitignore                   # Git除外設定
│
├── threads_sqlite.py            # メインスクリプト
├── migrate_to_sqlite.py         # マイグレーションツール
├── threads.db                   # SQLiteデータベース
│
├── POST_CREATION_MANUAL.md      # 投稿作成マニュアル
├── VIRAL_POST_STRATEGY.md       # バズる投稿戦略
│
├── posts_schedule.csv           # CSVバックアップ（オプション）
├── pdca_report.md               # 生成されたレポート
│
└── archive/                     # 古いファイル
    ├── threads_pdca.py          # 旧版スクリプト（CSV版）
    └── ...
```

---

## 🗄️ データベース構造

### postsテーブル

| カラム | 型 | 説明 |
|--------|----|----|
| id | INTEGER | 主キー |
| csv_id | TEXT | CSV互換ID |
| scheduled_at | DATETIME | 投稿予定時刻 |
| text | TEXT | 投稿テキスト |
| status | TEXT | pending / posted / failed |
| category | TEXT | 恋愛、仕事、お金、メンタル、占い |
| threads_post_id | TEXT | Threads投稿ID |
| posted_at | DATETIME | 実際の投稿時刻 |

### analyticsテーブル

| カラム | 型 | 説明 |
|--------|----|----|
| id | INTEGER | 主キー |
| post_id | INTEGER | postsテーブルの外部キー |
| views | INTEGER | 表示回数 |
| likes | INTEGER | いいね数 |
| replies | INTEGER | 返信数 |
| engagement_rate | REAL | エンゲージメント率 |

---

## 📖 関連ドキュメント

- **[POST_CREATION_MANUAL.md](POST_CREATION_MANUAL.md)** - 投稿作成の完全ガイド
  - ターゲットペルソナ
  - 絶対NGルール
  - バズる投稿の6つの法則
  - 3つのテンプレート
  - チェックリスト

- **[VIRAL_POST_STRATEGY.md](VIRAL_POST_STRATEGY.md)** - バズる投稿戦略
  - バズる投稿の絶対ルール
  - 投稿フォーマット
  - 投稿時間戦略
  - KPI目標
  - PDCA改善

---

## 🔄 CSVからの移行

既存のCSVファイルがある場合、以下のコマンドで簡単に移行できます:

```bash
# 1. データベース作成 + CSVインポート + ログ統合
python3 migrate_to_sqlite.py full

# 2. 統計確認
python3 migrate_to_sqlite.py stats

# 3. 新スクリプトでテスト
python3 threads_sqlite.py post --dry-run
```

---

## ⚙️ GitHub Actions自動化

### ワークフロー設定

`.github/workflows/threads_auto.yml`を作成:

```yaml
name: Threads Auto Post

on:
  schedule:
    - cron: '0 * * * *'  # 毎時実行
  workflow_dispatch:

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run posting
        env:
          THREADS_ACCESS_TOKEN: ${{ secrets.THREADS_ACCESS_TOKEN }}
          THREADS_USER_ID: ${{ secrets.THREADS_USER_ID }}
        run: python3 threads_sqlite.py post
```

### Secrets設定

GitHubリポジトリの Settings > Secrets and variables > Actions で以下を設定:

- `THREADS_ACCESS_TOKEN`
- `THREADS_USER_ID`

---

## 🧪 テスト

### ドライランモード

実際には投稿せず、動作確認のみ行います:

```bash
python3 threads_sqlite.py post --dry-run
```

### テスト投稿の追加

過去の時刻で投稿を追加すると、すぐに実行されます:

```bash
python3 threads_sqlite.py add \
  --datetime "2025-10-30 10:00" \
  --text "テスト投稿" \
  --category "テスト"

python3 threads_sqlite.py post --dry-run
```

---

## 📈 投稿戦略

### 推奨投稿頻度

- **1日25投稿** - 4つの時間帯に分散
  - 8時台: 6投稿（通勤中）
  - 12時台: 6投稿（昼休み）
  - 18時台: 6投稿（帰宅後）
  - 21時台: 7投稿（就寝前）

### コンテンツMix

| カテゴリ | 割合 | 投稿数/日 |
|---------|------|-----------|
| 恋愛・出会い | 30% | 8投稿 |
| 仕事・転職 | 25% | 6投稿 |
| お金・貯金 | 20% | 5投稿 |
| メンタル | 15% | 4投稿 |
| 占い | 10% | 2投稿 |

### 投稿フォーマット

全投稿は以下のルールに従います:

- ✅ **500文字前後** - パッと見で情報量がありそう
- ✅ **会話形式** - 漫画のように読める
- ✅ **具体的な数字** - リアリティがある
- ✅ **リスト形式** - 保存されやすい
- ✅ **ビフォーアフター** - 気づきを与える

詳細は [POST_CREATION_MANUAL.md](POST_CREATION_MANUAL.md) を参照。

---

## 🔧 トラブルシューティング

### データベースが見つからない

```bash
python3 migrate_to_sqlite.py init
```

### 投稿が実行されない

1. 投稿予定時刻を確認:
   ```bash
   python3 threads_sqlite.py list --status pending --limit 5
   ```

2. 現在時刻より過去の時刻に設定されているか確認

3. ドライランで動作確認:
   ```bash
   python3 threads_sqlite.py post --dry-run
   ```

### API認証エラー

1. 環境変数が正しく設定されているか確認:
   ```bash
   echo $THREADS_ACCESS_TOKEN
   echo $THREADS_USER_ID
   ```

2. アクセストークンの有効期限を確認

---

## 💾 データベースサイズ管理

### GitHubの制限

- **ファイルサイズ**: 50MB以上で警告、100MB以上はプッシュ不可
- **リポジトリサイズ**: 推奨1GB以下

### サイズチェック

```bash
# DBサイズと統計を確認
python3 check_db_size.py

# 簡易チェック
python3 check_db_size.py --quiet
```

**出力例:**
```
✅ OK: DBサイズは正常範囲内です
   現在: 0.10 MB / 40 MB

📈 データベース統計:
   総投稿数: 29件
   投稿済み: 1件

🔮 サイズ予測:
   1投稿あたり: 3.45 KB
   1年後の予測: 30.83 MB
```

### 自動チェック（pre-commit hook）

コミット前に自動でDBサイズをチェックします：

- **40MB以上**: 警告（コミットは可能）
- **90MB以上**: エラー（コミット中止）

### データアーカイブ

古いデータをCSVにエクスポートしてDBから削除：

```bash
# 90日前より古いデータをエクスポート（削除しない）
python3 archive_old_posts.py --older-than 90

# エクスポート + DBから削除
python3 archive_old_posts.py --older-than 90 --delete

# 1年前より古いデータを削除
python3 archive_old_posts.py --older-than 365 --delete
```

アーカイブされたデータは `archive/posts/` に保存されます。

### DBサイズ最適化

```bash
# VACUUMで最適化（削除後の空き領域を回収）
sqlite3 threads.db 'VACUUM;'

# 最適化後のサイズ確認
python3 check_db_size.py
```

### GitHubからDBを除外（推奨）

大量のコミットでGitHub容量を消費しないよう、DBをGitから除外することを推奨：

```bash
# .gitignoreに追加
echo 'threads.db' >> .gitignore

# 既にコミット済みの場合は削除
git rm --cached threads.db
git commit -m "Remove threads.db from Git tracking"
```

**代替案**: GitHub Actionsで使う場合は、artifactsとして保存します（ワークフロー例参照）。

---

## 📝 ライセンス

MIT License

---

## 🤝 コントリビューション

Issue や Pull Request は大歓迎です！

---

**Happy Posting! 🚀**
