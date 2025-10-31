# 🚀 Threads自動投稿 + PDCA分析システム

Threads APIを使った予約投稿とPDCA分析を自動化するツール

## 📋 目次

- [特徴](#特徴)
- [セットアップ](#セットアップ)
- [ファイル構成](#ファイル構成)
- [使い方](#使い方)
- [GitHub Actions自動化](#github-actions自動化)
- [投稿の流れ](#投稿の流れ)
- [ローカル分析](#ローカル分析)
- [トラブルシューティング](#トラブルシューティング)

---

## ✨ 特徴

### コア機能
- **確実な予約投稿** - 1日4回（8時、12時、18時、21時 JST）自動投稿
- **重複投稿防止** - 2層チェック（DB + CSV履歴）で安全
- **自動クリーンアップ** - 投稿済みを自動削除、posts_schedule.csvを常に最新に
- **ローカル分析** - Threads APIで過去投稿を分析、結果はローカル保存
- **トークン管理** - 長期トークン（60日）の自動監視

### アーキテクチャの特徴
- ✅ DBはGitHub Actionsキャッシュで管理（git競合なし）
- ✅ posts_schedule.csvが唯一の予約マスターデータ
- ✅ posted_history.csvで重複を防止
- ✅ 開発環境でのgit pullが不要
- ✅ リポジトリサイズが増えない設計

---

## 🛠️ セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd threads_auto
```

### 2. 依存関係のインストール

```bash
pip install requests
```

### 3. Threads APIトークンの取得

詳細は **[TOKEN_SETUP.md](TOKEN_SETUP.md)** を参照してください。

**簡易手順:**

1. [Meta for Developers](https://developers.facebook.com/)でアプリ作成
2. Threads APIを有効化
3. 短期トークンを取得
4. 長期トークン（60日）に変換

```bash
python3 setup_long_lived_token.py
```

### 4. GitHub Secretsの設定

GitHubリポジトリの `Settings > Secrets and variables > Actions` で設定:

- `THREADS_ACCESS_TOKEN` - 長期トークン
- `THREADS_USER_ID` - ユーザーID

### 5. 初回実行

GitHub Actionsワークフローを手動実行すると、自動的にDBが初期化されます。

---

## 📁 ファイル構成

### 必須ファイル

```
threads_auto/
├── README.md                           # このファイル
├── .env                                # ローカル用環境変数（.gitignore）
├── .gitignore                          # Git除外設定
│
├── 【予約投稿管理】
├── posts_schedule.csv                  # 予約投稿マスターデータ（git追跡）
├── posted_history.csv                  # 投稿履歴（重複防止用、git追跡）
├── threads.db                          # 実行時DB（GitHub Actionsキャッシュ、.gitignore）
│
├── 【実行スクリプト】
├── threads_sqlite.py                   # メイン投稿スクリプト
├── migrate_to_sqlite.py                # DB初期化・CSVインポート
├── setup_long_lived_token.py           # トークン取得・更新
├── analyze_local.py                    # ローカル分析スクリプト
├── check_db_size.py                    # DBサイズチェック
│
├── 【ドキュメント】
├── TOKEN_SETUP.md                      # トークン設定ガイド
├── CONTENT_MANAGEMENT.md               # コンテンツ管理ガイド
├── POSTING_LOGIC.md                    # 投稿ロジック詳細
├── POST_CREATION_MANUAL.md             # 投稿作成マニュアル（ペルソナ）
├── VIRAL_POST_STRATEGY.md              # バズる投稿戦略（ペルソナ）
├── EXPERIMENT_DAY1-3.md                # 実験レポート（参考）
├── learnings.md                        # 仮説検証ログ（PDCA改善履歴）⭐重要
│
└── 【GitHub Actions】
    └── .github/workflows/
        ├── threads-pdca.yml            # 投稿+PDCA自動化
        ├── merge-automation.yml        # automation→main 自動マージ
        └── token-refresh.yml           # トークン監視
```

### データフロー

```
[main ブランチ]
  posts_schedule.csv         予約投稿を追加（手動編集）
         ↓
[GitHub Actions]             スケジュール実行（10分おき）
         ↓
[threads.db]                 キャッシュから復元 → 投稿実行
         ↓
[Threads API]                投稿
         ↓
[automation ブランチ]
  posted_history.csv         投稿履歴に追記
  posts_schedule.csv         投稿済み行を自動削除
         ↓
[git commit & push]          automation ブランチにコミット [auto]
         ↓
[毎日0時]                    automation → main に自動マージ
```

---

## 🚀 使い方

### 新しい投稿を追加

`posts_schedule.csv`を編集して、新しい行を追加:

```csv
id,datetime,text,status,category
101,2025-11-03 08:00,"投稿テキスト...",pending,恋愛
102,2025-11-03 12:00,"投稿テキスト...",pending,仕事
```

コミット&プッシュすると、GitHub Actionsが自動で投稿します。

### 投稿作成のガイドライン

詳細は **[CONTENT_MANAGEMENT.md](CONTENT_MANAGEMENT.md)** を参照:

- **投稿フォーマット**: 会話形式、500文字前後
- **カテゴリ**: 恋愛、仕事、お金、メンタル、占い
- **投稿時間**: 8時、12時、18時、21時 JST
- **ペルソナ**: 20-30代の社会人女性

---

## 🌿 ブランチ運用戦略

### ブランチ構成

このプロジェクトは2つのブランチで運用されます：

```
main (開発用)
  ↓ 手動開発・新機能追加
  ↓
automation (自動更新用)
  ← GitHub Actionsが自動コミット
  ↓
  ↓ 毎日0時に自動マージ
  ↓
main
```

### ブランチの役割

| ブランチ | 用途 | 更新方法 |
|---------|------|---------|
| `main` | 開発・新規投稿追加 | 手動コミット&プッシュ |
| `automation` | 投稿履歴の自動更新 | GitHub Actionsが自動コミット |

### メリット

✅ **開発がスムーズ**: mainで自由に開発・コミット・プッシュできる
✅ **コンフリクト回避**: 自動更新は別ブランチなので競合しない
✅ **レビュー可能**: 自動更新の内容を確認してからマージできる
✅ **ロールバック簡単**: 問題があれば自動マージ前に戻せる

### 開発フロー

#### 新しい投稿を追加する場合

```bash
# main ブランチで作業
git checkout main
git pull origin main

# posts_schedule.csv を編集
vim posts_schedule.csv

# コミット&プッシュ
git add posts_schedule.csv
git commit -m "Add: 新しい投稿を追加"
git push origin main
```

#### automation ブランチを手動でマージする場合

```bash
# main ブランチに切り替え
git checkout main
git pull origin main

# automation ブランチをマージ
git merge origin/automation -m "Merge automation updates"
git push origin main
```

通常は **毎日0時（JST）に自動マージ** されるため、手動マージは不要です。

### 自動マージの仕組み

`.github/workflows/merge-automation.yml`が毎日0時（JST）に実行され、以下を行います：

1. `automation` ブランチの変更を取得
2. コンフリクトがないか確認
3. 問題なければ `main` にマージ
4. コンフリクトがある場合は通知して手動マージを促す

### automation ブランチの内容

GitHub Actionsによって以下のファイルが自動更新されます：

- `posted_history.csv` - 投稿履歴の追記
- `posts_schedule.csv` - 投稿済み行の削除

コミットメッセージの形式：
```
Update: Posted 15 total, 2516 remaining [auto]
```

---

## ⚙️ GitHub Actions自動化

### 投稿スケジュール

`.github/workflows/threads-pdca.yml`で自動実行:

| 時刻（JST） | 時刻（UTC） | 実行内容 |
|------------|------------|---------|
| 8:00       | 23:00      | 投稿チェック |
| 12:00      | 3:00       | 投稿チェック |
| 18:00      | 9:00       | 投稿チェック |
| 21:00      | 12:00      | 投稿チェック |
| 20:00（3日ごと） | 11:00 | PDCAレポート生成 |

### 手動実行

GitHub Actionsタブから手動実行可能:

- **post**: 投稿のみ実行
- **pdca**: PDCAレポートのみ生成
- **full-cycle**: 投稿 + PDCAレポート

### 自動処理の内容

1. **データベース復元**: GitHub Actionsキャッシュから`threads.db`を復元
2. **投稿実行**: `python3 threads_sqlite.py post`
3. **ブランチ切り替え**: `automation` ブランチに切り替え
4. **履歴更新**: 投稿済みを`posted_history.csv`に追記
5. **自動クリーンアップ**: `posts_schedule.csv`から投稿済み行を削除
6. **コミット**: `automation` ブランチに自動コミット&プッシュ（`[auto]`付き）
7. **キャッシュ保存**: 更新後の`threads.db`をキャッシュに保存
8. **自動マージ**: 毎日0時に `automation` → `main` をマージ

---

## 📝 投稿の流れ

### 投稿ルール

詳細は **[POSTING_LOGIC.md](POSTING_LOGIC.md)** を参照。

**投稿条件:**
```
scheduled_at <= 現在時刻（JST）
かつ
status = 'pending'
かつ
posted_history.csvに記録なし
```

**実行間隔:**
- 投稿間隔: 10秒
- タイムアウト: 2分

### 重複防止の仕組み

2層チェックで確実に重複を防ぎます:

1. **DB状態チェック**: `status = 'pending'`のみ取得
2. **CSV履歴チェック**: `posted_history.csv`に記録がないか確認

これにより、キャッシュが期限切れになっても重複投稿しません。

### DBリカバリー

キャッシュが無効になった場合の自動リカバリー:

```bash
# 今日投稿すべきpending投稿 = 0
# かつ
# 今日のposted投稿 = 0
# の場合のみ、CSVから再インポート
```

---

## 📚 学習ログの更新

### learnings.md とは

投稿パフォーマンスの仮説検証結果を記録するログファイルです。
セッションをまたいでも知見が蓄積され、同じ失敗を繰り返さないための重要なドキュメントです。

### 気づきを記録する

```bash
# 新しい気づきを追加
python3 threads_sqlite.py update-learnings --text "今日の気づき"
```

### 記録される内容

- 📊 検証データ（投稿数、平均表示回数など）
- 💡 仮説（今日試したこと）
- ✅/❌ 結果（うまくいった/いかなかった理由）
- 🎯 改善アクション（次にやること）

### 重要な注意事項

**新しいセッションを開始したら、必ず最初に learnings.md を読んでください。**
過去の成功/失敗パターンが記録されており、投稿戦略の根拠となります。

---

## 📊 ローカル分析

### 分析スクリプトの実行

```bash
# 環境変数を読み込み
export $(cat .env | xargs)

# 分析実行（最新20件の投稿を分析）
python3 analyze_local.py
```

### 生成されるファイル

分析結果はローカルのみに保存されます（`.gitignore`に含まれる）:

- `analysis_results.json` - 詳細な分析データ
- `analysis_report.md` - 人間が読みやすいレポート

### レポート内容

- 📈 サマリー（ビュー数、いいね数、エンゲージメント率）
- 🔥 エンゲージメント率 TOP 5
- ❤️ いいね数 TOP 5
- 💡 改善ポイント

### 分析結果の活用方法

1. `analysis_report.md`を確認
2. 反応が良かった投稿の特徴を分析
3. 新しい投稿を`posts_schedule.csv`に追加
4. `git push`でデプロイ

---

## 🔄 トークン管理

### トークンの有効期限

- **長期トークン**: 60日間有効
- **自動監視**: 毎週日曜 20:00 JST にチェック

### トークンが期限切れになった場合

GitHub Issueに自動通知されます:

1. Issuesタブで通知を確認
2. 新しい短期トークンを取得（[Meta for Developers](https://developers.facebook.com/)）
3. 長期トークンに変換:
   ```bash
   python3 setup_long_lived_token.py
   ```
4. GitHub Secretsを更新

詳細は **[TOKEN_SETUP.md](TOKEN_SETUP.md)** を参照。

---

## 📊 PDCA分析（GitHub Actions）

### レポート生成

3日ごとに自動生成される`pdca_report.md`には以下が含まれます:

- 📈 サマリー（期間内の総計）
- 🏆 トップパフォーマンス投稿
- 🎯 カテゴリ別パフォーマンス
- ⏰ ベスト投稿時間帯
- 💡 次のアクションプラン（Keep/Improve/Try）

レポートは自動的にGitHub Issueに投稿されます。

---

## 🔧 トラブルシューティング

### 投稿が実行されない

1. **posts_schedule.csvを確認**
   - `datetime`が現在時刻より過去か？
   - `status`が`pending`になっているか？

2. **GitHub Actionsログを確認**
   - Actionsタブで最新の実行ログを確認
   - エラーメッセージをチェック

3. **手動実行でテスト**
   - GitHub Actionsタブで手動実行
   - モード: `post`

### トークンエラー

```
Error validating access token: Session has expired
```

→ **[TOKEN_SETUP.md](TOKEN_SETUP.md)** を参照してトークンを再取得

### DBキャッシュが無効になった

通常は自動でリカバリーされますが、手動で確認したい場合:

```bash
# ローカルでDBを初期化
python3 migrate_to_sqlite.py init
python3 threads_sqlite.py import --csv posts_schedule.csv

# 状態を確認
sqlite3 threads.db "SELECT COUNT(*), status FROM posts GROUP BY status"
```

### 重複投稿が発生した場合

`posted_history.csv`に該当する`csv_id`が記録されていれば、次回から投稿されません。

手動で追加する場合:
```bash
echo "csv_id,posted_at" > posted_history.csv
echo "101,2025-11-01 08:15:23" >> posted_history.csv
```

---

## 📖 関連ドキュメント

### PDCA改善
- **[learnings.md](learnings.md)** - 仮説検証ログ（⭐最重要）
  - 毎日の検証データと気づき
  - 仮説の成功/失敗パターン
  - 次のアクションプラン
  - **新しいセッションで必ず最初に参照すること**

### 投稿管理
- **[CONTENT_MANAGEMENT.md](CONTENT_MANAGEMENT.md)** - コンテンツ管理の完全ガイド
  - ファイル構成と役割
  - 投稿追加方法
  - 重複防止の仕組み

- **[POSTING_LOGIC.md](POSTING_LOGIC.md)** - 投稿ロジックの詳細
  - 投稿スケジュール
  - 投稿選択ルール
  - DB状態管理

### トークン管理
- **[TOKEN_SETUP.md](TOKEN_SETUP.md)** - トークン設定の完全ガイド
  - 短期トークンの取得
  - 長期トークンへの変換
  - 自動監視の仕組み

### コンテンツ作成
- **[POST_CREATION_MANUAL.md](POST_CREATION_MANUAL.md)** - 投稿作成マニュアル
  - ターゲットペルソナ
  - 絶対NGルール
  - バズる投稿の6つの法則

- **[VIRAL_POST_STRATEGY.md](VIRAL_POST_STRATEGY.md)** - バズる投稿戦略
  - 投稿フォーマット
  - 投稿時間戦略
  - KPI目標

---

## 📈 投稿戦略

### 推奨投稿頻度

- **1日4回** - 4つの時間帯に分散
  - 8時台: 通勤中
  - 12時台: 昼休み
  - 18時台: 帰宅後
  - 21時台: 就寝前

### コンテンツMix

| カテゴリ | 割合 | 特徴 |
|---------|------|------|
| 恋愛・出会い | 30% | 共感されやすい |
| 仕事・転職 | 25% | 保存されやすい |
| お金・貯金 | 20% | シェアされやすい |
| メンタル | 15% | いいねが多い |
| 占い | 10% | エンゲージメント高い |

### 投稿フォーマット

全投稿は以下のルールに従います:

- ✅ **500文字前後** - パッと見で情報量がありそう
- ✅ **会話形式** - 漫画のように読める
- ✅ **具体的な数字** - リアリティがある
- ✅ **リスト形式** - 保存されやすい
- ✅ **ビフォーアフター** - 気づきを与える

---

## 💾 データベースサイズ管理

### GitHubの制限

threads.dbは`.gitignore`に含まれているため、リポジトリサイズに影響しません。

GitHub Actionsキャッシュの制限:
- **保存期間**: 7日間（定期実行で自動更新）
- **サイズ制限**: 10GB（十分な容量）

### サイズチェック

```bash
# DBサイズと統計を確認
python3 check_db_size.py

# 簡易チェック
python3 check_db_size.py --quiet
```

---

## 🎯 クイックスタート

### 1. 環境構築（初回のみ）

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd threads_auto

# 2. トークンを取得
python3 setup_long_lived_token.py

# 3. GitHub Secretsを設定
# Settings > Secrets and variables > Actions
# - THREADS_ACCESS_TOKEN
# - THREADS_USER_ID
```

### 2. 投稿を追加

```bash
# posts_schedule.csvを編集
# 新しい行を追加:
# 103,2025-11-03 08:00,"投稿テキスト...",pending,恋愛

# コミット&プッシュ
git add posts_schedule.csv
git commit -m "Add: 新しい投稿を追加"
git push
```

### 3. 自動投稿を確認

- GitHub Actionsタブで実行状況を確認
- 投稿後、`posted_history.csv`と`posts_schedule.csv`が自動更新される

---

## 📝 ライセンス

MIT License

---

**Happy Posting! 🚀**
