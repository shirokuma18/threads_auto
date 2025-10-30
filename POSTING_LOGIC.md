# 📋 投稿ロジックとスケジュール

このドキュメントでは、Threads自動投稿システムの投稿ルール、スケジュール、データベース管理の仕組みを説明します。

---

## 🕐 投稿スケジュールとルール

### 1. ワークフローの実行スケジュール

GitHub Actionsで1日4回自動実行されます：

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

**PDCA分析:**
- 3日ごとに自動実行（UTC 11:00 = JST 20:00）
- GitHub Issueにレポート投稿

---

### 2. 投稿対象の決定ロジック

**投稿条件:**
```python
# 現在時刻（JST）を取得
jst = timezone(timedelta(hours=9))
current_time = datetime.now(jst)

# 投稿対象のクエリ
SELECT * FROM posts
WHERE status = 'pending'
  AND scheduled_at <= current_time
ORDER BY scheduled_at
```

**ルール:**
1. **status が 'pending'** の投稿のみ
2. **scheduled_at <= current_time** の投稿のみ
3. **posted_history.csv に記録がない** 投稿のみ
4. **scheduled_at の昇順** で並べ替え
5. **すべてまとめて投稿** （時刻範囲で分割しない）

---

### 3. 重複防止の仕組み

システムは**2層の重複チェック**で確実に重複を防ぎます：

**レイヤー1: DB状態チェック**
```python
# threads.db の status で判定
SELECT * FROM posts WHERE status='pending'
# status='posted' の投稿は取得されない
```

**レイヤー2: CSV履歴チェック**
```python
# posted_history.csv で判定
posted_ids = load_posted_history()
if csv_id in posted_ids:
    print(f"  ⚠️  すでに投稿済み")
    mark_as_posted(post_id, f"duplicate_{csv_id}")
    continue
```

**動作:**
```
キャッシュが有効な場合:
└─ DB の status='posted' で判定 → 重複なし

キャッシュが消失した場合:
├─ CSVから再インポート（全て status='pending'）
└─ posted_history.csv で判定 → 重複なし
```

これにより、**キャッシュが消えても重複投稿しません**。

---

### 4. 具体例: 2025年10月30日 12:00 JST に実行した場合

**データベースの投稿スケジュール:**

| csv_id | scheduled_at | status | カテゴリ | 投稿される？ |
|--------|--------------|--------|---------|------------|
| 1 | 2025-10-30 08:05 | pending | 占い | ✅ Yes |
| 2 | 2025-10-30 08:22 | pending | 恋愛 | ✅ Yes |
| 3 | 2025-10-30 08:38 | pending | 仕事 | ✅ Yes |
| 4 | 2025-10-30 08:47 | pending | お金 | ✅ Yes |
| 5 | 2025-10-30 08:52 | pending | メンタル | ✅ Yes |
| 6 | 2025-10-30 08:58 | pending | 恋愛 | ✅ Yes |
| 7 | 2025-10-30 12:03 | pending | 恋愛 | ❌ No (12:03 > 12:00) |
| 8 | 2025-10-30 12:18 | pending | 仕事 | ❌ No |
| ... | ... | ... | ... | ❌ No |

**結果:**
- **投稿対象: 6件** (08:05 〜 12:00未満)
- **投稿されない: 18件** (12:03以降)

**投稿の実行順序:**
```
[1/6] 08:05 - 占い投稿
  → 投稿成功
  → 10秒待機

[2/6] 08:22 - 恋愛投稿
  → 投稿成功
  → 10秒待機

...

[6/6] 11:58 - 投稿
  → 投稿成功
  → 完了
```

**合計実行時間:** 約60秒（10秒間隔 × 5 + API処理時間）

---

## 💾 データベース管理の仕組み

### 1. データフロー

```
[posts_schedule.csv]
予約投稿マスターデータ（git追跡）
         ↓
[GitHub Actions実行]
1日4回（8時、12時、18時、21時 JST）
         ↓
[threads.db]
キャッシュから復元 → 投稿実行
         ↓
[Threads API]
投稿
         ↓
[posted_history.csv]
投稿履歴に追記（git追跡）
         ↓
[posts_schedule.csv]
投稿済み行を自動削除（git追跡）
         ↓
[git commit & push]
変更を自動コミット（[skip ci]付き）
         ↓
[threads.db]
更新後のDBをキャッシュに保存
```

---

### 2. ファイルの役割

**posts_schedule.csv（予約マスターデータ）:**
- **役割:** これから投稿する予約のマスターデータ
- **場所:** リポジトリ（git追跡）
- **内容:** id, datetime, text, status, category
- **特徴:** 投稿後は自動削除される（常に未投稿の予約のみ）

**threads.db（実行時キャッシュ）:**
- **役割:** ワークフロー実行時の状態管理
- **場所:** GitHub Actionsキャッシュ（7日間保持）
- **内容:** posts テーブル（status: pending/posted）
- **特徴:** リポジトリに含まれない（.gitignore）

**posted_history.csv（投稿履歴）:**
- **役割:** 投稿済みのIDを記録し、重複を防止
- **場所:** リポジトリ（git追跡）
- **内容:** csv_id, posted_at
- **特徴:** 最小限のデータ、永続的な記録

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
  echo "⚠️  今日の投稿がありません。CSVから再インポートします。"
  rm -f threads.db
  python3 migrate_to_sqlite.py init
  python3 threads_sqlite.py import --csv posts_schedule.csv
elif [ "$TODAY_POSTED" -gt 0 ]; then
  # すでに投稿済み → キャッシュを信頼
  echo "✅ 今日すでに $TODAY_POSTED 件投稿済み。キャッシュDBを使用します。"
fi
```

**判断ロジック:**

| 今日のpending | 今日のposted | アクション |
|--------------|-------------|-----------|
| 0件 | 0件 | ⚠️ CSVから再インポート |
| 0件 | 5件 | ✅ キャッシュDB使用（すでに投稿済み） |
| 10件 | 0件 | ✅ キャッシュDB使用（まだ投稿していない） |
| 10件 | 5件 | ✅ キャッシュDB使用（一部投稿済み） |

---

## 🔄 1日の投稿フロー（例）

### 2025年10月30日のタイムライン

**00:00 JST - 日付変更**
- DB: 24件のpending投稿（08:05 〜 21:58）

**08:00 JST - 朝の投稿（1回目）**
```
1. キャッシュ復元 → CSVから初回インポート
2. 投稿対象: 0件（08:05が最初の投稿）
3. 投稿なし
4. DBをキャッシュに保存
```

**12:00 JST - 昼の投稿（2回目）**
```
1. キャッシュ復元 → 前回のDB
2. 検証: 今日のposted=0件、pending>0件 → キャッシュDB使用
3. 投稿対象: 6件（08:05 〜 11:58）
4. 投稿実行 → 6件 status='posted'
5. posted_history.csv に追記
6. posts_schedule.csv から6行削除
7. git commit & push ([skip ci])
8. DBをキャッシュに保存
9. 残りpending: 18件
```

**18:00 JST - 夕方の投稿（3回目）**
```
1. キャッシュ復元 → 前回のDB（6件posted）
2. 検証: 今日のposted=6件 → キャッシュDB使用
3. 投稿対象: 6件（12:03 〜 17:58）
4. 投稿実行 → 6件 status='posted'
5. posted_history.csv に追記
6. posts_schedule.csv から6行削除
7. git commit & push ([skip ci])
8. DBをキャッシュに保存
9. 残りpending: 12件
```

**21:00 JST - 夜の投稿（4回目）**
```
1. キャッシュ復元 → 前回のDB（12件posted）
2. 検証: 今日のposted=12件 → キャッシュDB使用
3. 投稿対象: 7件（18:05 〜 20:58）
4. 投稿実行 → 7件 status='posted'
5. posted_history.csv に追記
6. posts_schedule.csv から7行削除
7. git commit & push ([skip ci])
8. DBをキャッシュに保存
9. 残りpending: 5件
```

**21:08以降の投稿:**
- 残り5件は翌日08:00以降に投稿される
- または、手動実行で投稿可能

---

## ❓ よくある質問

### Q1: なぜ時刻範囲で区切らないの？

**A:** シンプルさと柔軟性のためです。

**現在の方式:**
- `scheduled_at <= current_time` のすべてを投稿
- メリット: 投稿漏れがない、スケジュール変更に柔軟

**時刻範囲で区切る方式の問題:**
- 08:00実行で「00:00〜07:59の投稿」に限定
- もし08:10に実行されたら、08:00〜08:10の投稿が漏れる
- スケジュール変更時にロジック変更が必要

---

### Q2: 投稿が重複する可能性は？

**A:** 重複は2層のチェックで防止されています。

**重複防止の仕組み:**
1. **status フィールド:**
   - 'pending' → 'posted' に変更
   - posted は二度と投稿されない

2. **posted_history.csv:**
   - 投稿後にcsv_idを記録
   - キャッシュが消失しても重複チェック可能

3. **検証ロジック:**
   - 今日のposted件数をチェック
   - すでに投稿済みならキャッシュDB使用

---

### Q3: キャッシュが消えたらどうなる？

**A:** CSVから自動的に再構築されます。

**キャッシュ消失時の動作:**
```bash
1. キャッシュなし → threads.db が存在しない
2. CSVから新規インポート
3. 全ての投稿が status='pending'
4. posted_history.csv で重複チェック
5. 重複を除いて投稿
```

**影響:**
- ✅ posted_history.csv があるため重複投稿しない
- ✅ 通常は1日1回の実行なので影響は限定的
- ✅ キャッシュは7日間保持されるため、実質問題なし

---

### Q4: 手動で投稿を追加したい場合は？

**A:** posts_schedule.csv を直接編集してください。

**方法:**
```bash
# ローカルでCSVを編集
vi posts_schedule.csv

# 新しい行を追加
echo '26,2025-10-31 10:00,"投稿テキスト...",pending,恋愛' >> posts_schedule.csv

# コミット・プッシュ
git add posts_schedule.csv
git commit -m "Add: 新しい投稿を追加"
git push
```

**注意:**
- csv_id は一意にする（既存IDと重複しない）
- datetime は JST で指定
- status は 'pending' に設定
- category は正確に指定（恋愛、仕事、お金、メンタル、占い）

---

## 🔍 デバッグとトラブルシューティング

### 投稿対象の確認

**ローカルで確認:**
```bash
# 今日の投稿スケジュール
TODAY=$(TZ=Asia/Tokyo date '+%Y-%m-%d')
grep "$TODAY" posts_schedule.csv

# 投稿総数を確認
tail -n +2 posts_schedule.csv | wc -l
```

**GitHub Actions ログの確認:**

ワークフローログで確認すべきポイント:

```
📊 キャッシュDB: pending 18 件 (今日 6 件) / posted (今日 6 件)
✅ 投稿対象: 6件
時刻範囲: 2025-10-30 12:03 〜 2025-10-30 17:58

[1/6] 投稿ID: 7 | 2025-10-30 12:03 | [恋愛]
  ✓ 投稿成功！
```

---

## 📚 参考

- **[threads_sqlite.py](./threads_sqlite.py)** - メインスクリプト
- **[.github/workflows/threads-pdca.yml](./.github/workflows/threads-pdca.yml)** - ワークフロー定義
- **[CONTENT_MANAGEMENT.md](./CONTENT_MANAGEMENT.md)** - コンテンツ管理ガイド
- **[EXPERIMENT_DAY1-3.md](./EXPERIMENT_DAY1-3.md)** - 3日間実験計画

---

**Happy Posting! 🚀**
