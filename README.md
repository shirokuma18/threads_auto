# Threads Auto Posting

Threadsへの自動投稿システム（シンプル設計）

## 🎯 コンセプト

**完全ステートレス = 究極のシンプルさ**

- 単一の情報源: `posts_schedule.csv`
- タームベースの投稿判定（8, 10, 12, 15, 17, 19, 20, 21, 22, 23, 24時）
- API照合による重複防止
- リポジトリへの影響ゼロ（ファイル書き込みなし）
- ブランチ分け不要（mainのみ）
- **スレッド形式投稿対応**（各ターム2/5投稿）

## 📁 プロジェクト構造

```
threads_auto/
├── posts_schedule.csv        # すべての投稿（永久保存、削除しない）
├── threads_simple.py         # メインスクリプト（ステートレス）
├── POSTING_GUIDELINES.md     # 投稿作成ガイドライン（必読）
├── learnings.md              # 仮説検証ログ
└── POST_CREATION_MANUAL.md   # 投稿作成マニュアル（長文向け）
```

## 🚀 使い方

### 投稿実行

```bash
# 通常実行
python3 threads_simple.py

# テスト実行（ドライラン）
python3 threads_simple.py --dry-run

# 毎朝の成果報告
python3 threads_simple.py daily-report
```

### 新しい投稿を追加

1. `posts_schedule.csv` に行を追加
2. `scheduled_at` に投稿時刻を設定（JST）
3. **削除不要** - すべての投稿が履歴として残ります

例:
```csv
id,datetime,text,category,topic,thread_text
100,2025-11-01 12:00,"新しい投稿内容",experience,お金,
```

## ⚙️ 自動実行スケジュール

GitHub Actionsで自動実行：

- **投稿**: 8, 10, 12, 15, 17, 19, 20, 21, 22, 23, 24時 JST（毎日11回、各5投稿 = 55投稿/日）
- **成果報告**: 9:00 JST（毎朝）

**投稿間隔:** 6分（スパム対策）
**スレッド形式:** 各ターム2/5投稿（続きがスレッド内に展開）

## 🎨 投稿戦略

### バランス型投稿構成

1. **リアルタイム試行錯誤** (30%) - 今まさに挑戦中の記録
2. **体験談ベースノウハウ** (50%) - 個人の物語として語る
3. **役立つノウハウ** (20%) - 保存・シェアされやすい

### スパム判定対策

- 数字は1-2個まで（羅列NG）
- 箇条書きは3個まで（多用NG）
- Before/After形式は避ける
- 感情表現を必ず入れる
- 完成形を避ける（「3日目」「続けられるかな」）

詳細: [POST_CREATION_MANUAL.md](POST_CREATION_MANUAL.md)

## 📊 仕組み

### ステートレスアーキテクチャ

```
現在時刻 → スケジュールターム判定（例：15:15 → 15:00ターム）
    ↓
Threads APIから最近の投稿取得
    ↓
posts_schedule.csvから該当タームの未投稿分を取得
    ↓
投稿実行（リポジトリへの影響なし）
```

**メリット:**
- ✅ 完全ステートレス（状態ファイル不要）
- ✅ 冪等性（同じタームで何度実行しても同じ結果）
- ✅ リポジトリへの影響ゼロ（ファイル書き込みなし）
- ✅ ブランチ分け不要（mainのみで動作）
- ✅ cron遅延に強い（±15分のずれに対応）
- ✅ 同期問題ゼロ（API照合で重複防止）

### システム進化履歴

**2025-10-31 午後 - ステートレス化:**
- `.last_posted_at` 削除 → 状態管理完全廃止
- タームベース判定導入（cron遅延対応）
- API照合による重複防止
- automationブランチ廃止 → mainのみ
- リポジトリへの影響ゼロ化

**2025-10-31 午前 - シンプル化:**
- `threads.db` 削除
- `posted_history.csv` 削除
- 時間範囲ベースの投稿導入

## 📝 学習ログ

`learnings.md` に仮説検証の結果を記録：

- 成功/失敗パターン
- スパム判定された投稿の分析
- コンテンツ戦略の改善履歴

**新しいセッション開始時は必ず `learnings.md` を読んでください。**

## 🔧 セットアップ

### 環境変数

`.env` ファイルに設定：

```bash
THREADS_ACCESS_TOKEN=your_token_here
THREADS_USER_ID=your_user_id_here
```

### トークン取得

```bash
python3 setup_long_lived_token.py
```

## 📊 競合分析・投稿戦略

### Threads API 競合分析ツール

実際のThreads APIを使った競合分析・投稿戦略の立案ツールを追加しました。

**利用可能な機能:**
- **キーワード検索API** - トレンドキーワードで投稿を検索
- **トレンド分析** - 投稿頻度、文字数、メディアタイプの分析
- **コンテンツパターン分析** - 疑問形、絵文字、ハッシュタグの使用率
- **投稿戦略の自動生成** - データに基づいた最適な投稿戦略

### 使い方

```bash
# 競合分析の実行
python3 threads_competitor_analyzer.py

# 生成されるファイル:
# - threads_keyword_trends.csv       # キーワード別トレンド
# - threads_popular_{keyword}.csv    # 人気投稿リスト
# - threads_posting_strategy.csv     # 推奨投稿戦略
```

**詳細:** [COMPETITOR_ANALYSIS_GUIDE.md](COMPETITOR_ANALYSIS_GUIDE.md)

**API制限:**
- キーワード検索: 7日間で500クエリ
- データ期間: 2024年4月13日以降

## 📚 ドキュメント

- **[POSTING_GUIDELINES.md](POSTING_GUIDELINES.md)** - 投稿作成ガイドライン（短文・高頻度投稿版、必読）
- **[COMPETITOR_ANALYSIS_GUIDE.md](COMPETITOR_ANALYSIS_GUIDE.md)** - 競合分析・投稿戦略ガイド
- [POST_CREATION_MANUAL.md](POST_CREATION_MANUAL.md) - 投稿作成の完全マニュアル（長文投稿向け）
- [learnings.md](learnings.md) - 仮説検証ログ
- [.claude/claude.md](.claude/claude.md) - Claude Code セッションガイド

## 🎯 成功の本質

**「中に人がいる感じ」「リアルな成長過程」**

- ✓ 試行錯誤している様子を記録する
- ✓ 学びを得て頑張っている姿を見せる
- ✓ 失敗も含めた成長の記録
- ✗ AI的な教科書的コンテンツは避ける
- ✗ 誰が書いたかわからない一般論は避ける

---

**運用開始日:** 2025-10-29
**システム刷新日:** 2025-10-31
