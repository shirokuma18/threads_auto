# Threads競合分析・投稿戦略ガイド

## 📋 目次

1. [事前準備](#事前準備)
2. [基本的な使い方](#基本的な使い方)
3. [分析の流れ](#分析の流れ)
4. [投稿戦略の立て方](#投稿戦略の立て方)
5. [API制限と注意事項](#api制限と注意事項)

---

## 事前準備

### 必要な環境
```bash
pip install requests pandas python-dotenv
```

### `.env`ファイルに追加
```env
THREADS_ACCESS_TOKEN=your_long_lived_access_token
THREADS_USER_ID=your_user_id
```

---

## 基本的な使い方

### 1. シンプルなキーワード検索

```python
from threads_competitor_analyzer import ThreadsCompetitorAnalyzer

analyzer = ThreadsCompetitorAnalyzer()

# キーワードで投稿を検索
threads = analyzer.keyword_search('副業', limit=50)

for thread in threads:
    print(f"@{thread['username']}: {thread['text'][:50]}...")
```

### 2. トレンド分析

```python
# 複数キーワードのトレンドを7日間分析
keywords = ['副業', '朝活', '時間管理']
trend_df = analyzer.analyze_keyword_trends(keywords, days=7)

# CSVに保存
trend_df.to_csv('trend_analysis.csv', index=False, encoding='utf-8-sig')
```

### 3. コンテンツパターン分析

```python
# 特定キーワードの投稿パターンを分析
patterns = analyzer.content_pattern_analysis('副業', days=30)

# 結果:
# - 疑問形の割合
# - 絵文字の使用率
# - ハッシュタグの有無
# - 文字数分布
```

### 4. 投稿戦略の自動生成

```python
# キーワードから最適な投稿戦略を生成
keywords = ['副業', '仕事術', 'ワークライフバランス']
strategies = analyzer.generate_posting_strategy(keywords, days=14)

# 結果:
# - 推奨投稿頻度
# - 最適文字数
# - フォーマット推奨
```

---

## 分析の流れ

### STEP 1: ニッチの特定

まず、あなたのアカウントが狙うべきニッチを明確にします。

**現在の投稿トピック（POSTING_GUIDELINES.mdより）:**
- 眠い、疲れた、残業、忙しい（仕事系）
- 寝れない、集中できない（悩み系）
- 副業、早起き、続かない（自己啓発系）
- やる気、ストレス、自分時間（メンタル系）

**競合分析用キーワード:**
```python
primary_keywords = ['副業', '仕事術', 'ワークライフバランス']
secondary_keywords = ['朝活', '時間管理', '自己投資', 'ストレス解消']
trending_keywords = ['ハロウィン', 'インサイト祭り']  # 時事ネタ
```

### STEP 2: 競合の投稿パターンを分析

```python
analyzer = ThreadsCompetitorAnalyzer()

# 各キーワードの投稿頻度を確認
for keyword in primary_keywords:
    trend_df = analyzer.analyze_keyword_trends([keyword], days=14)
    print(f"{keyword}: {trend_df['posts_per_day'].values[0]:.1f} posts/day")
```

### STEP 3: 成功パターンの抽出

```python
# 人気投稿を分析（自分の投稿のみインサイト取得可能）
popular_df = analyzer.discover_popular_posts('副業')

# トップ10の投稿パターンを確認
top_10 = popular_df.head(10)
print(top_10[['username', 'text_length', 'has_media', 'text']])
```

### STEP 4: コンテンツパターンの把握

```python
# 各キーワードのコンテンツパターン
for keyword in primary_keywords:
    patterns = analyzer.content_pattern_analysis(keyword, days=30)

    print(f"\n{keyword}:")
    print(f"  疑問形: {patterns['has_question']:.0f}%")
    print(f"  絵文字: {patterns['has_emoji']:.0f}%")
    print(f"  短文(<100字): {patterns['short_form']:.0f}%")
```

---

## 投稿戦略の立て方

### 現在のアカウント設定

**投稿スケジュール:**
- 11枠/日（8, 10, 12, 15, 17, 19, 20, 21, 22, 23, 24時）
- 各枠5投稿、6分間隔
- **合計55投稿/日**

**現在の投稿バランス（POSTING_GUIDELINES.mdより）:**
- 短文・共感系: 60-90文字
- Tips・価値提供系: 120-180文字
- 権威性・実績系: 100-150文字

### 分析結果を反映した改善策

#### 1. キーワード戦略

```python
# 分析結果から各キーワードの投稿頻度を決定
keyword_strategy = {
    '副業': 10,  # 10投稿/日（人気が高い）
    '仕事術': 8,
    'ワークライフバランス': 6,
    '朝活': 5,
    '時間管理': 5,
    'ストレス解消': 5,
    '自己投資': 4,
    'その他': 12  # トレンド・時事ネタ
}
```

#### 2. コンテンツフォーマット戦略

分析結果を基に、各キーワードに最適なフォーマットを適用:

```python
# 例: '副業' キーワードの分析結果
# - 疑問形: 35% → 疑問形を使う
# - 絵文字: 60% → 絵文字を必ず入れる
# - 短文: 45%, 中文: 40% → 短文・中文を混在

副業_投稿例 = [
    {
        "text": "副業、土日だけで3ヶ月続けた結果👀",  # 短文・疑問形風
        "thread_text": "平日は何もしない。\n土日2時間だけ。\n\n焦らず続けるのが大事。\n少しずつ形になってきた。",
        "category": "副業"
    },
    {
        "text": "副業を続けるコツって何だと思う？💭\n\n僕は「成果を求めない」ことだと思ってる。",  # 疑問形
        "thread_text": "最初は結果が出なくて当然。\n続けることだけに集中する。\n\n3ヶ月目で少しずつ見えてきた。",
        "category": "副業"
    }
]
```

#### 3. 投稿タイミング戦略

```python
# 分析結果: '副業' は夜の時間帯に投稿が多い
# → 19時, 20時, 21時, 22時に集中配置

投稿タイミング = {
    '8時': ['朝活', '早起き', '仕事術'],
    '12時': ['仕事術', '時間管理', 'ストレス'],
    '15時': ['疲れた', '眠い', '集中できない'],
    '19時': ['副業', '仕事終わり', 'ワークライフバランス'],
    '20時': ['副業', 'ストレス解消', '自己投資'],
    '21時': ['副業', '夜のルーティン', '寝れない'],
    '23時': ['睡眠', 'ストレス', '振り返り']
}
```

### 実践: 新しい投稿を生成

```python
# threads_competitor_analyzer.py の分析結果を基に
# posts_schedule.csv を更新

# 1. 分析実行
analyzer = ThreadsCompetitorAnalyzer()
strategies = analyzer.generate_posting_strategy(['副業', '仕事術', '朝活'], days=14)

# 2. 戦略を反映した投稿を生成
# （手動で posts_schedule.csv に追加、または自動生成スクリプトを作成）

# 3. POSTING_GUIDELINES.md に従いつつ、
#    分析結果の「疑問形の割合」「絵文字使用率」などを反映
```

---

## API制限と注意事項

### レート制限

- **キーワード検索**: 7日間で500クエリ
- **推奨**: 1日あたり70クエリまで

### データ取得制限

- **期間**: 2024年4月13日以降のデータのみ
- **インサイト**: 自分の投稿のみ詳細データ取得可能
- **公開投稿**: テキスト、ユーザー名、タイムスタンプは取得可能

### ベストプラクティス

```python
# 1. レート制限を考慮した実行間隔
import time

for keyword in keywords:
    analyzer.keyword_search(keyword)
    time.sleep(2)  # 2秒待機

# 2. クエリ数の管理
print(f"Remaining queries: {analyzer.rate_limit_remaining}/500")

# 3. 定期実行（1日1回がおすすめ）
# cron or GitHub Actions で自動化
```

---

## 実践例: 1週間の分析サイクル

### 月曜日: トレンド分析

```python
# 週末の投稿トレンドを確認
keywords = ['副業', '仕事術', 'ワークライフバランス']
trend_df = analyzer.analyze_keyword_trends(keywords, days=3)
```

### 水曜日: コンテンツパターン更新

```python
# 人気投稿のパターンを確認
for keyword in keywords[:2]:
    patterns = analyzer.content_pattern_analysis(keyword, days=7)
    # パターンを投稿に反映
```

### 金曜日: 週末投稿の準備

```python
# 次週の投稿戦略を生成
strategies = analyzer.generate_posting_strategy(keywords, days=7)
# 土日の投稿スケジュールを更新
```

---

## まとめ

このツールを使って：

1. **競合の投稿パターンを理解** → 人気トピック・フォーマットを把握
2. **データに基づいた投稿戦略** → 感覚ではなく数字で判断
3. **継続的な改善** → 毎週分析して戦略を更新

**次のステップ:**
1. `threads_competitor_analyzer.py` を実行
2. 生成されたCSVファイルを確認
3. `posts_schedule.csv` に反映
4. POSTING_GUIDELINES.md を更新
