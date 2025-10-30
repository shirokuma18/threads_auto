# 📋 投稿ロジックとデータベース管理の詳細

このドキュメントでは、Threads 自動投稿システムの投稿ルール、スケジュール、データベース管理の仕組みを詳しく説明します。

---

## 🕐 投稿スケジュールとルール

### 1. ワークフローの実行スケジュール

GitHub Actions で1日4回自動実行されます：

```yaml
schedule:
  - cron: '0 23,3,9,12 * * *'  # UTC時刻
```

| UTC時刻 | JST時刻 | 投稿タイミング |
|---------|---------|--------------|
| 23:00 | 08:00 | 朝の投稿 |
| 03:00 | 12:00 | 昼の投稿 |
| 09:00 | 18:00 | 夕方の投稿 |
| 12:00 | 21:00 | 夜の投稿 |

---

### 2. 投稿対象の決定ロジック

**コアロジック（`threads_sqlite.py` の `get_pending_posts()`）:**

```python
# 現在時刻（JST）を取得
jst = timezone(timedelta(hours=9))
current_time = datetime.now(jst)  # 例: 2025-10-30 12:00:00

# SQLクエリ
SELECT * FROM posts
WHERE status = 'pending'
  AND scheduled_at <= '2025-10-30 12:00:00'
ORDER BY scheduled_at
```

**ルール:**
1. **status が 'pending'** の投稿のみ
2. **scheduled_at <= current_time** の投稿のみ
3. **scheduled_at の昇順** で並べ替え
4. **すべてまとめて投稿** （時刻範囲で分割しない）

---

### 3. 具体例: 2025年10月30日 12:00 JST に実行した場合

**データベースの投稿スケジュール:**

| csv_id | scheduled_at | status | カテゴリ | 投稿される？ |
|--------|--------------|--------|---------|------------|
| 30 | 2025-10-30 00:35 | pending | メンタル | ✅ Yes |
| 101 | 2025-10-30 07:15 | pending | 恋愛 | ✅ Yes |
| 102 | 2025-10-30 07:32 | pending | 仕事 | ✅ Yes |
| 103 | 2025-10-30 07:48 | pending | 恋愛 | ✅ Yes |
| 104 | 2025-10-30 08:22 | pending | その他 | ✅ Yes |
| 105 | 2025-10-30 08:38 | pending | 恋愛 | ✅ Yes |
| 27 | 2025-10-30 08:45 | pending | メンタル | ✅ Yes |
| 28 | 2025-10-30 08:50 | pending | メンタル | ✅ Yes |
| 29 | 2025-10-30 08:55 | pending | お金 | ✅ Yes |
| 106 | 2025-10-30 11:42 | pending | 仕事 | ✅ Yes |
| 26 | 2025-10-30 12:00 | pending | テスト | ✅ Yes (ちょうど12:00) |
| **107** | **2025-10-30 12:08** | pending | 仕事 | ❌ No (12:08 > 12:00) |
| 108 | 2025-10-30 12:25 | pending | お金 | ❌ No |
| 112 | 2025-10-30 17:18 | pending | 恋愛 | ❌ No |
| 117 | 2025-10-30 22:15 | pending | 恋愛 | ❌ No |

**結果:**
- **投稿対象: 11件** (00:35 〜 12:00)
- **投稿されない: 14件** (12:08 〜 23:28)

---

### 4. 投稿の実行順序

**投稿は scheduled_at の昇順で実行:**

```
[1/11] 00:35 - メンタル投稿
  → 投稿成功
  → 10秒待機

[2/11] 07:15 - 恋愛投稿
  → 投稿成功
  → 10秒待機

[3/11] 07:32 - 仕事投稿
  → 投稿成功
  → 10秒待機

...

[11/11] 12:00 - テスト投稿
  → 投稿成功
  → 完了
```

**合計実行時間:** 約110秒（10秒間隔 × 10 + API処理時間）

---

## 💾 データベース管理の仕組み

### 1. データベースの状態遷移

```
初期状態 (リポジトリ):
├─ threads.db
│  ├─ 投稿1: status='pending', scheduled_at='2025-10-30 00:35'
│  ├─ 投稿2: status='pending', scheduled_at='2025-10-30 07:15'
│  └─ ...

ワークフロー実行 (GitHub Actions):
1. キャッシュからDBを復元
   └─ 前回実行時の状態（一部 status='posted'）

2. DBの検証
   ├─ 今日のpending投稿数をチェック
   ├─ 今日のposted投稿数をチェック
   └─ 必要に応じてリポジトリのDBでリカバリー

3. 投稿実行
   ├─ pending投稿を取得
   ├─ Threads API で投稿
   └─ status='pending' → status='posted' に更新

4. DBをリポジトリにコミット
   ├─ git add threads.db
   ├─ git commit -m "Update database: X posts published"
   └─ git push

5. DBをキャッシュに保存
   └─ 次回の実行で使用
```

---

### 2. キャッシュとリポジトリの使い分け

**GitHub Actions のキャッシュ:**
- **目的:** ワークフロー間でデータを高速に共有
- **キー:** `threads-db-v2-{commit-sha}`
- **有効期限:** 7日間（アクセスがない場合）
- **メリット:** 高速復元（数秒）
- **デメリット:** 永続的ではない

**リポジトリの threads.db:**
- **目的:** 永続的なデータ保存
- **更新タイミング:** 投稿実行後に自動コミット
- **メリット:** 完全な履歴、永続的
- **デメリット:** バイナリファイル（差分が見づらい）

---

### 3. データベース検証ロジック

**キャッシュ復元後の検証:**

```bash
# 1. 今日の投稿状況を確認
CURRENT_DATE=$(TZ=Asia/Tokyo date '+%Y-%m-%d')
TODAY_PENDING=$(sqlite3 threads.db "SELECT COUNT(*) FROM posts WHERE status='pending' AND DATE(scheduled_at) = '$CURRENT_DATE'")
TODAY_POSTED=$(sqlite3 threads.db "SELECT COUNT(*) FROM posts WHERE status='posted' AND DATE(posted_at) = '$CURRENT_DATE'")

echo "📊 キャッシュDB: pending (今日 $TODAY_PENDING 件) / posted (今日 $TODAY_POSTED 件)"

# 2. リカバリーの判断
if [ "$TODAY_PENDING" -eq 0 ] && [ "$TODAY_POSTED" -eq 0 ]; then
  # 今日のpendingもpostedもない → キャッシュが壊れている
  echo "⚠️  今日の投稿がありません。リポジトリのthreads.dbを使用します。"
  git checkout threads.db
elif [ "$TODAY_POSTED" -gt 0 ]; then
  # すでに投稿済み → キャッシュを信頼
  echo "✅ 今日すでに $TODAY_POSTED 件投稿済み。キャッシュDBを使用します。"
fi
```

**判断ロジック:**

| 今日のpending | 今日のposted | アクション |
|--------------|-------------|-----------|
| 0件 | 0件 | ⚠️ リポジトリDBでリカバリー |
| 0件 | 5件 | ✅ キャッシュDB使用（すでに投稿済み） |
| 10件 | 0件 | ✅ キャッシュDB使用（まだ投稿していない） |
| 10件 | 5件 | ✅ キャッシュDB使用（一部投稿済み） |

---

### 4. リポジトリへの自動コミット

**投稿後の処理:**

```bash
# 1. DBに変更があるかチェック
if git diff --quiet threads.db; then
  echo "📊 データベースに変更なし（投稿なし）"
else
  # 2. 変更があればコミット
  git config user.email "github-actions[bot]@users.noreply.github.com"
  git config user.name "github-actions[bot]"
  git add threads.db

  # 3. 今日の投稿数をカウント
  POSTED_COUNT=$(sqlite3 threads.db "SELECT COUNT(*) FROM posts WHERE status='posted' AND DATE(posted_at) = date('now', '+9 hours')")

  # 4. コミットメッセージに投稿数を含める
  git commit -m "Update database: ${POSTED_COUNT} posts published [skip ci]"

  # 5. プッシュ
  git push
fi
```

**コミットメッセージの例:**
```
Update database: 9 posts published [skip ci]
```

**[skip ci] の意味:**
- GitHub Actions を再トリガーしない
- 無限ループを防ぐ

---

## 🔄 1日の投稿フロー（例）

### 2025年10月30日のタイムライン

**00:00 JST - 日付変更**
- DB: 25件のpending投稿（00:35 〜 23:28）

**08:00 JST - 朝の投稿（1回目）**
```
1. キャッシュ復元 → リポジトリDBを使用（初回）
2. 投稿対象: 1件（00:35）
3. 投稿実行 → status='posted'
4. DBをコミット: "Update database: 1 posts published"
5. 残りpending: 24件
```

**12:00 JST - 昼の投稿（2回目）**
```
1. キャッシュ復元 → 前回のDB（1件posted）
2. 検証: 今日のposted=1件 → キャッシュDB使用
3. 投稿対象: 10件（07:15 〜 12:00）
4. 投稿実行 → 10件 status='posted'
5. DBをコミット: "Update database: 11 posts published"
6. 残りpending: 14件
```

**18:00 JST - 夕方の投稿（3回目）**
```
1. キャッシュ復元 → 前回のDB（11件posted）
2. 検証: 今日のposted=11件 → キャッシュDB使用
3. 投稿対象: 5件（12:08 〜 18:08）
4. 投稿実行 → 5件 status='posted'
5. DBをコミット: "Update database: 16 posts published"
6. 残りpending: 9件
```

**21:00 JST - 夜の投稿（4回目）**
```
1. キャッシュ復元 → 前回のDB（16件posted）
2. 検証: 今日のposted=16件 → キャッシュDB使用
3. 投稿対象: 0件（次の投稿は22:15）
4. 投稿なし
5. DBコミットなし
6. 残りpending: 9件
```

**22:15 〜 23:28 JST**
- 残り9件は翌日08:00に投稿される
- または、手動実行で投稿可能

---

## ❓ よくある質問

### Q1: なぜ時刻範囲で区切らないの？

**A:** シンプルさと柔軟性のためです。

**現在の方式:**
- scheduled_at <= current_time のすべてを投稿
- メリット: 投稿漏れがない、スケジュール変更に柔軟

**時刻範囲で区切る方式の問題:**
- 08:00実行で「00:00〜07:59の投稿」に限定
- もし08:10に実行されたら、08:00〜08:10の投稿が漏れる
- スケジュール変更時にロジック変更が必要

---

### Q2: 投稿が重複する可能性は？

**A:** 重複は防止されています。

**重複防止の仕組み:**
1. **status フィールド:**
   - 'pending' → 'posted' に変更
   - posted は二度と投稿されない

2. **DBの永続化:**
   - 投稿後にリポジトリにコミット
   - 次回実行時にposted状態が保持される

3. **検証ロジック:**
   - 今日のposted件数をチェック
   - すでに投稿済みならキャッシュDB使用

---

### Q3: キャッシュが壊れたらどうなる？

**A:** 自動リカバリーされます。

**リカバリーフロー:**
```
1. キャッシュ復元
2. 検証: 今日のpending=0 AND 今日のposted=0
3. 判定: キャッシュが壊れている
4. アクション: git checkout threads.db でリカバリー
5. 結果: リポジトリの正しいDBを使用
```

---

### Q4: リポジトリのDBが更新されるタイミングは？

**A:** 投稿実行後、自動的にコミットされます。

**タイミング:**
- 投稿スクリプト実行後
- キャッシュ保存前
- 投稿がない場合はコミットされない

**コミット例:**
```bash
$ git log --oneline -5
d64c273 Update database: 9 posts published [skip ci]
f74f60b Fix: Check for today's pending posts instead of total count
...
```

---

### Q5: 手動で投稿を追加・削除したい場合は？

**A:** リポジトリの threads.db を直接編集してください。

**方法:**
```bash
# ローカルでDBを編集
sqlite3 threads.db

# 新しい投稿を追加
INSERT INTO posts (csv_id, scheduled_at, text, category, status)
VALUES (999, '2025-10-31 10:00:00', '新しい投稿', '恋愛', 'pending');

# コミット・プッシュ
git add threads.db
git commit -m "Add manual post"
git push
```

**注意:**
- 次回のワークフロー実行時にキャッシュが更新される
- 手動編集は慎重に行ってください

---

## 🔍 デバッグとトラブルシューティング

### 投稿対象の確認

**ローカルで確認:**
```bash
# 今日の投稿スケジュール
sqlite3 threads.db "SELECT csv_id, scheduled_at, status, category FROM posts WHERE DATE(scheduled_at) = date('now', '+9 hours') ORDER BY scheduled_at"

# 投稿対象（現在時刻より前のpending）
CURRENT_TIME=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
sqlite3 threads.db "SELECT csv_id, scheduled_at, status FROM posts WHERE status='pending' AND scheduled_at <= '$CURRENT_TIME' ORDER BY scheduled_at"
```

### GitHub Actions ログの確認

**ワークフローログで確認すべきポイント:**

```
📊 キャッシュDB: pending 75 件 (今日 25 件) / posted (今日 0 件)
✅ 投稿対象: 9件
時刻範囲: 2025-10-30 00:35 〜 2025-10-30 08:55

[1/9] 投稿ID: 30 | 2025-10-30 00:35 | [メンタル]
  ✓ 投稿成功！
```

---

## 📚 参考

- [threads_sqlite.py](./threads_sqlite.py) - メインスクリプト
- [.github/workflows/threads-pdca.yml](./.github/workflows/threads-pdca.yml) - ワークフロー定義
- [EXPERIMENT_DAY1-3.md](./EXPERIMENT_DAY1-3.md) - 3日間実験計画
