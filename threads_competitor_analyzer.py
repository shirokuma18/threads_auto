#!/usr/bin/env python3
"""
Threads競合分析・投稿戦略ツール

実際のThreads API仕様に基づいた実装:
- キーワード検索API (GET /keyword_search)
- 公開投稿のインサイト取得
- 競合分析とトレンド把握
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import os
from dotenv import load_dotenv

load_dotenv()

class ThreadsCompetitorAnalyzer:
    def __init__(self, access_token=None):
        self.token = access_token or os.getenv('THREADS_ACCESS_TOKEN')
        self.base_url = 'https://graph.threads.net/v1.0'
        self.rate_limit_remaining = 500  # 7日間で500クエリ

    def keyword_search(self, keyword, since=None, until=None, limit=50):
        """
        キーワード検索API

        公式エンドポイント: GET /keyword_search

        Parameters:
        - keyword: 検索キーワード
        - since: Unix timestamp (開始日時)
        - until: Unix timestamp (終了日時)
        - limit: 取得件数（デフォルト50）

        Returns:
        - List of threads
        """
        url = f"{self.base_url}/keyword_search"
        params = {
            'q': keyword,
            'access_token': self.token,
            'limit': limit,
            'fields': 'id,text,username,timestamp,permalink,media_type,media_url,alt_text'
        }

        if since:
            params['since'] = since
        if until:
            params['until'] = until

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()

            self.rate_limit_remaining -= 1
            print(f"✓ Found {len(response.json().get('data', []))} threads for '{keyword}' (Rate limit: {self.rate_limit_remaining}/500)")

            return response.json().get('data', [])
        except requests.exceptions.HTTPError as e:
            print(f"✗ API Error: {e}")
            print(f"Response: {response.text}")
            return []

    def get_thread_insights(self, thread_id):
        """
        投稿のインサイトを取得

        公式エンドポイント: GET /{thread_id}/insights

        メトリクス: views, likes, replies, reposts, quotes, shares, clicks
        """
        url = f"{self.base_url}/{thread_id}/insights"
        params = {
            'metric': 'views,likes,replies,reposts,quotes,shares',  # clicks は有料プランのみ
            'access_token': self.token
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()

            data = response.json().get('data', [])
            metrics = {}
            for item in data:
                metric_name = item.get('name')
                values = item.get('values', [{}])
                metrics[metric_name] = values[0].get('value', 0) if values else 0

            return metrics
        except requests.exceptions.HTTPError:
            # 公開投稿でも自分以外のインサイトは取得できない可能性
            return {}

    def analyze_keyword_trends(self, keywords, days=7):
        """
        複数キーワードのトレンド分析

        Parameters:
        - keywords: List[str] - 分析するキーワードリスト
        - days: int - 過去何日分を分析するか

        Returns:
        - DataFrame with trend analysis
        """
        print("\n" + "="*70)
        print(f"📊 Keyword Trend Analysis (Past {days} days)")
        print("="*70 + "\n")

        # 時間範囲を設定
        until_time = int(datetime.now().timestamp())
        since_time = int((datetime.now() - timedelta(days=days)).timestamp())

        all_results = []

        for keyword in keywords:
            print(f"\n🔍 Analyzing: '{keyword}'")

            # キーワード検索
            threads = self.keyword_search(keyword, since=since_time, until=until_time, limit=100)

            if not threads:
                print(f"  No threads found for '{keyword}'")
                continue

            # 統計情報を集計
            total_threads = len(threads)
            usernames = [t.get('username') for t in threads]
            username_counts = Counter(usernames)

            # メディアタイプの分布
            media_types = Counter([t.get('media_type', 'TEXT') for t in threads])

            # 文字数の分析
            text_lengths = [len(t.get('text', '')) for t in threads]
            avg_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0

            # トップコントリビューター
            top_contributors = username_counts.most_common(5)

            result = {
                'keyword': keyword,
                'total_posts': total_threads,
                'avg_text_length': avg_length,
                'media_types': dict(media_types),
                'top_contributors': top_contributors,
                'posts_per_day': total_threads / days
            }

            all_results.append(result)

            # レート制限対策
            time.sleep(1)

            # 結果表示
            print(f"  📈 Posts: {total_threads} ({result['posts_per_day']:.1f}/day)")
            print(f"  📝 Avg Length: {avg_length:.0f} chars")
            print(f"  🎨 Media: {media_types}")
            print(f"  👤 Top: @{top_contributors[0][0]} ({top_contributors[0][1]} posts)")

        # DataFrame化
        df = pd.DataFrame(all_results)

        print("\n" + "="*70)
        print("📊 Summary")
        print("="*70)
        print(df[['keyword', 'total_posts', 'avg_text_length', 'posts_per_day']])

        return df

    def discover_popular_posts(self, keyword, min_engagement=0):
        """
        人気投稿の発見

        注意: 他人の投稿のインサイトは取得できない可能性が高い
        そのため、投稿の内容分析に焦点を当てる
        """
        print(f"\n🔥 Discovering popular posts for: '{keyword}'")

        # 過去7日間の投稿を取得
        since_time = int((datetime.now() - timedelta(days=7)).timestamp())
        threads = self.keyword_search(keyword, since=since_time, limit=100)

        if not threads:
            print("No threads found")
            return pd.DataFrame()

        analysis_data = []

        for thread in threads:
            thread_id = thread.get('id')
            text = thread.get('text', '')
            username = thread.get('username')
            timestamp = thread.get('timestamp')
            permalink = thread.get('permalink')
            media_type = thread.get('media_type', 'TEXT')

            # インサイト取得を試みる（自分の投稿のみ成功）
            insights = self.get_thread_insights(thread_id)

            analysis_data.append({
                'thread_id': thread_id,
                'username': username,
                'text': text[:100],
                'full_text': text,
                'timestamp': timestamp,
                'permalink': permalink,
                'media_type': media_type,
                'text_length': len(text),
                'has_media': media_type != 'TEXT',
                'views': insights.get('views', 0),
                'likes': insights.get('likes', 0),
                'replies': insights.get('replies', 0),
                'reposts': insights.get('reposts', 0),
                'quotes': insights.get('quotes', 0),
                'shares': insights.get('shares', 0)
            })

            time.sleep(0.5)  # レート制限対策

        df = pd.DataFrame(analysis_data)

        # エンゲージメント率を計算（データがある場合のみ）
        if df['views'].sum() > 0:
            df['engagement_rate'] = (df['likes'] + df['replies'] + df['reposts']) / df['views'].replace(0, 1) * 100
            df = df.sort_values('engagement_rate', ascending=False)

        print(f"\n✓ Analyzed {len(df)} posts")

        return df

    def content_pattern_analysis(self, keyword, days=30):
        """
        コンテンツパターン分析

        - 投稿のトーン（疑問形、断定形など）
        - 文字数分布
        - 絵文字の使用
        - ハッシュタグの有無
        """
        print(f"\n📝 Content Pattern Analysis: '{keyword}'")

        since_time = int((datetime.now() - timedelta(days=days)).timestamp())
        threads = self.keyword_search(keyword, since=since_time, limit=200)

        if not threads:
            return {}

        patterns = {
            'has_question': 0,
            'has_emoji': 0,
            'has_hashtag': 0,
            'has_url': 0,
            'short_form': 0,  # <100文字
            'medium_form': 0,  # 100-300文字
            'long_form': 0,  # >300文字
        }

        for thread in threads:
            text = thread.get('text', '')

            if '?' in text or '？' in text:
                patterns['has_question'] += 1

            # 絵文字検出（簡易版）
            if any(ord(c) > 127 for c in text):
                patterns['has_emoji'] += 1

            if '#' in text:
                patterns['has_hashtag'] += 1

            if 'http' in text:
                patterns['has_url'] += 1

            text_len = len(text)
            if text_len < 100:
                patterns['short_form'] += 1
            elif text_len < 300:
                patterns['medium_form'] += 1
            else:
                patterns['long_form'] += 1

        total = len(threads)
        percentages = {k: (v/total)*100 for k, v in patterns.items()}

        print(f"\n  Total analyzed: {total} posts")
        print(f"  Question format: {percentages['has_question']:.1f}%")
        print(f"  With emoji: {percentages['has_emoji']:.1f}%")
        print(f"  With hashtag: {percentages['has_hashtag']:.1f}%")
        print(f"  With URL: {percentages['has_url']:.1f}%")
        print(f"  Short (<100): {percentages['short_form']:.1f}%")
        print(f"  Medium (100-300): {percentages['medium_form']:.1f}%")
        print(f"  Long (>300): {percentages['long_form']:.1f}%")

        return percentages

    def generate_posting_strategy(self, keywords, days=14):
        """
        投稿戦略の生成

        複数キーワードを分析して、効果的な投稿戦略を提案
        """
        print("\n" + "="*70)
        print("🎯 POSTING STRATEGY GENERATOR")
        print("="*70 + "\n")

        strategies = []

        for keyword in keywords:
            print(f"\n📊 Analyzing '{keyword}'...")

            # トレンド分析
            trend_df = self.analyze_keyword_trends([keyword], days=days)

            # コンテンツパターン分析
            patterns = self.content_pattern_analysis(keyword, days=days)

            if not trend_df.empty:
                strategy = {
                    'keyword': keyword,
                    'recommended_frequency': f"{trend_df.iloc[0]['posts_per_day']:.1f} posts/day",
                    'optimal_length': f"{trend_df.iloc[0]['avg_text_length']:.0f} chars",
                    'use_question_format': patterns.get('has_question', 0) > 30,
                    'include_emoji': patterns.get('has_emoji', 0) > 50,
                    'include_hashtag': patterns.get('has_hashtag', 0) > 20,
                    'content_type': 'Short' if patterns.get('short_form', 0) > 50 else 'Medium'
                }

                strategies.append(strategy)

            time.sleep(2)

        # 戦略サマリー
        print("\n" + "="*70)
        print("📋 STRATEGY RECOMMENDATIONS")
        print("="*70 + "\n")

        for strategy in strategies:
            print(f"Keyword: '{strategy['keyword']}'")
            print(f"  Frequency: {strategy['recommended_frequency']}")
            print(f"  Length: {strategy['optimal_length']}")
            print(f"  Question format: {'✓' if strategy['use_question_format'] else '✗'}")
            print(f"  Emoji: {'✓' if strategy['include_emoji'] else '✗'}")
            print(f"  Hashtag: {'✓' if strategy['include_hashtag'] else '✗'}")
            print(f"  Type: {strategy['content_type']}-form content")
            print()

        return strategies


def main():
    """使用例"""

    # 初期化
    analyzer = ThreadsCompetitorAnalyzer()

    # 分析したいキーワード（あなたのニッチに合わせて調整）
    keywords = [
        '副業',
        '仕事術',
        '朝活',
        'ワークライフバランス',
        '時間管理'
    ]

    # 1. キーワードトレンド分析
    print("\n🔍 STEP 1: Keyword Trend Analysis")
    trend_df = analyzer.analyze_keyword_trends(keywords, days=7)
    trend_df.to_csv('threads_keyword_trends.csv', index=False, encoding='utf-8-sig')

    # 2. 人気投稿の発見
    print("\n🔥 STEP 2: Popular Posts Discovery")
    for keyword in keywords[:2]:  # 最初の2つだけ（レート制限対策）
        popular_df = analyzer.discover_popular_posts(keyword)
        if not popular_df.empty:
            popular_df.to_csv(f'threads_popular_{keyword}.csv', index=False, encoding='utf-8-sig')
        time.sleep(3)

    # 3. 投稿戦略の生成
    print("\n🎯 STEP 3: Posting Strategy Generation")
    strategies = analyzer.generate_posting_strategy(keywords[:3], days=14)

    # 戦略をCSVに保存
    pd.DataFrame(strategies).to_csv('threads_posting_strategy.csv', index=False, encoding='utf-8-sig')

    print("\n✅ Analysis complete! Check the generated CSV files.")
    print(f"📊 Rate limit remaining: {analyzer.rate_limit_remaining}/500 (7-day window)")


if __name__ == '__main__':
    main()
