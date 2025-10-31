# Threads Auto Posting

Threadsへの自動投稿システム（シンプル設計）

## 🎯 コンセプト

**シンプル = 信頼性**

- 単一の信頼できる情報源: `posts_schedule.csv`
- 時間範囲ベースの投稿（冪等性）
- データベース不要、履歴ファイル不要

## 📁 プロジェクト構造

```
threads_auto/
├── posts_schedule.csv        # すべての投稿（永久保存、削除しない）
├── .last_posted_at           # 最終実行時刻（自動更新）
├── threads_simple.py         # メインスクリプト
├── learnings.md              # 仮説検証ログ
└── POST_CREATION_MANUAL.md   # 投稿作成マニュアル
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

- **投稿**: 8:00, 12:00, 18:00, 21:00 JST（毎日4回）
- **成果報告**: 9:00 JST（毎朝）
- **マージ**: 0:00 JST（automation → main）

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

### シンプルアーキテクチャ

```
posts_schedule.csv (すべての投稿)
    +
.last_posted_at (最終実行時刻)
    ↓
scheduled_at が (last_posted_at, now] の範囲 → 投稿
```

**メリット:**
- ✅ 冪等性（何度実行しても同じ結果）
- ✅ 同期問題ゼロ
- ✅ CSVから削除不要（すべての投稿が永久保存）
- ✅ シンプル（バグが入りにくい）

### 旧システムからの変更点（2025-10-31）

**削除したもの:**
- `threads.db` - データベース不要に
- `posted_history.csv` - 履歴管理不要に
- 複雑な同期ロジック - 時間範囲ベースに

**理由:**
- 3つのファイル同期で発生していたバグ
- タイムゾーン問題による重複投稿
- 複雑さを排除してシンプルに

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

## 📚 ドキュメント

- **[POSTING_GUIDELINES.md](POSTING_GUIDELINES.md)** - 投稿作成ガイドライン（短文・高頻度投稿版、必読）
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
