#!/usr/bin/env python3
"""
Analyze experiment metrics for a given date range from posts_schedule.csv.

Usage:
  python3 analyze_experiments.py 2025-11-09 2025-11-15

Outputs:
  experiments_results_YYYYMMDD_YYYYMMDD.csv with per-post metrics and factors.

Notes:
  - Requires THREADS_ACCESS_TOKEN and THREADS_USER_ID in environment (.env ok).
  - Maps schedule rows to posted items by comparing the first 100 chars of `text`.
  - Fetches insights: views, likes, replies, reposts, quotes (where available for own posts).
"""

import csv
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

API_BASE_URL = 'https://graph.threads.net/v1.0'
ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
USER_ID = os.getenv('THREADS_USER_ID')

JST = timezone(timedelta(hours=9))


def get_user_posts(limit=200):
    url = f'{API_BASE_URL}/{USER_ID}/threads'
    params = {
        'fields': 'id,text,timestamp',
        'limit': limit,
        'access_token': ACCESS_TOKEN
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json().get('data', [])


def get_insights(thread_id: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/{thread_id}/insights"
    params = {
        'metric': 'views,likes,replies,reposts,quotes',
        'access_token': ACCESS_TOKEN
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json().get('data', [])
        out = {}
        for item in data:
            name = item.get('name')
            values = item.get('values', [{}])
            out[name] = values[0].get('value', 0)
        return out
    except requests.exceptions.RequestException:
        return {}


def parse_tags(tag_str: str) -> Dict[str, str]:
    out = {}
    if not tag_str:
        return out
    for part in tag_str.split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            out[k.replace('exp:','')] = v
    return out


def main():
    if len(sys.argv) != 3:
        print('Usage: python3 analyze_experiments.py YYYY-MM-DD YYYY-MM-DD')
        sys.exit(1)
    start = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    end = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()

    # Load schedule rows in range
    rows = []
    with open('posts_schedule.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get('datetime'):
                continue
            dt = datetime.strptime(r['datetime'], '%Y-%m-%d %H:%M').date()
            if start <= dt <= end:
                rows.append(r)

    # compute posts-per-day (ppd) per date in the selected window
    from collections import Counter
    day_counts = Counter()
    for r in rows:
        d = r['datetime'].split(' ')[0]
        day_counts[d] += 1

    # Build lookup for posted items by preview
    posts = get_user_posts(limit=500)
    preview_to_id = {}
    for p in posts:
        t = (p.get('text') or '').strip()
        preview_to_id[t[:100]] = p.get('id')

    outpath = f"experiments_results_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
    with open(outpath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'id','datetime','theme','len','op','end','br','concept','tense','thread',
            'views','likes','replies','reposts','quotes','like_rate','reply_rate','ppd','hour','tod'
        ])

        for r in rows:
            text = (r.get('text') or '').strip()
            preview = text[:100]
            th_id = preview_to_id.get(preview)
            insights = {'views':0,'likes':0,'replies':0,'reposts':0,'quotes':0}
            if th_id:
                insights.update(get_insights(th_id))
            views = max(1, int(insights.get('views') or 0))
            likes = int(insights.get('likes') or 0)
            replies = int(insights.get('replies') or 0)
            like_rate = likes / views
            reply_rate = replies / views

            tags = parse_tags(r.get('hashtags') or '')
            dkey = r.get('datetime','').split(' ')[0]
            ppd = day_counts.get(dkey, 0)
            # time-of-day bucket
            dt_full = datetime.strptime(r.get('datetime'), '%Y-%m-%d %H:%M')
            hh = dt_full.hour
            if 20 <= hh <= 23:
                tod = 'night'
            elif 17 <= hh <= 19:
                tod = 'evening'
            elif 12 <= hh <= 16:
                tod = 'afternoon'
            else:
                tod = 'morning'
            writer.writerow([
                r.get('id'), r.get('datetime'), r.get('subcategory'),
                tags.get('len',''), tags.get('op',''), tags.get('end',''), tags.get('br',''),
                tags.get('concept',''), tags.get('tense',''), tags.get('thread','no'),
                views, likes, replies, int(insights.get('reposts') or 0), int(insights.get('quotes') or 0),
                f"{like_rate:.4f}", f"{reply_rate:.4f}",
                ppd, hh, tod
            ])

    print(f"✅ Wrote {outpath}")


if __name__ == '__main__':
    main()
