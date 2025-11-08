#!/usr/bin/env python3
"""
Threads投稿データからnote用Markdown記事を生成

使い方:
    python3 generate_note_markdown.py 001  # Story 001の完全版を生成
    python3 generate_note_markdown.py all  # 全ストーリーを生成
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def generate_note_article(story_id, posts, output_dir='note_articles'):
    """note用のMarkdown記事を生成"""

    # 出力ディレクトリを作成
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # 投稿をソート（時系列順）
    posts.sort(key=lambda x: x['datetime'])

    # メタデータを取得
    first_post = posts[0]
    category = first_post.get('category', '教室短編')
    subcategory = first_post.get('subcategory', '')

    # 本文を結合
    full_text = '\n\n---\n\n'.join(post['text'] for post in posts)

    # note用Markdown生成
    markdown = f"""# {subcategory}

{full_text}

---

## あとがき

この作品は、教室で起きる小さな出来事を通じて、子どもたちの背景にある家庭事情や心の問題に向き合う教師の物語です。

完璧な解決を描くのではなく、教師の葛藤、迷い、無力感を率直に描くことを心がけています。

---

**カテゴリ**: {category}
**投稿数**: {len(posts)}投稿
**初回投稿**: {posts[0]['datetime']}

---

この物語が気に入ったら、サポートやフォローをお願いします。
毎日、教室を舞台にした短編小説をThreadsで連載しています。

Threadsアカウント: [@あなたのアカウント名]
"""

    # ファイルに保存
    output_file = output_path / f"{story_id}_{subcategory}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"✓ 生成完了: {output_file}")
    print(f"  タイトル: {subcategory}")
    print(f"  投稿数: {len(posts)}投稿")
    print(f"  文字数: {len(full_text):,}文字")
    print()

    return output_file


def load_posts_by_story(csv_file='data/posts_schedule.csv'):
    """CSVから投稿をストーリーごとにグループ化"""
    stories = defaultdict(list)

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            post_id = row.get('id', '').strip()
            if not post_id:
                continue

            # ストーリーIDを抽出（例: 001_01 → 001）
            story_id = post_id.split('_')[0]

            stories[story_id].append({
                'id': post_id,
                'datetime': row.get('datetime', '').strip(),
                'text': row.get('text', '').strip(),
                'category': row.get('category', '').strip(),
                'subcategory': row.get('subcategory', '').strip(),
            })

    return stories


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 generate_note_markdown.py <story_id|all>")
        print("例:")
        print("  python3 generate_note_markdown.py 001  # Story 001のみ")
        print("  python3 generate_note_markdown.py all  # 全ストーリー")
        sys.exit(1)

    target = sys.argv[1]

    print("=" * 70)
    print("📝 note用Markdown記事生成")
    print("=" * 70)
    print()

    # 投稿データを読み込み
    stories = load_posts_by_story()

    if target == 'all':
        print(f"全{len(stories)}ストーリーを生成します...\n")
        for story_id in sorted(stories.keys()):
            generate_note_article(story_id, stories[story_id])
    else:
        if target not in stories:
            print(f"✗ ストーリーID '{target}' が見つかりません")
            print(f"利用可能なストーリー: {', '.join(sorted(stories.keys()))}")
            sys.exit(1)

        generate_note_article(target, stories[target])

    print("=" * 70)
    print("✅ 生成完了")
    print("=" * 70)
    print()
    print("📌 次のステップ:")
    print("  1. note_articles/ フォルダ内のMarkdownファイルを確認")
    print("  2. noteにログイン")
    print("  3. 新規記事作成でMarkdown内容をコピペ")
    print("  4. 公開設定（無料/有料、公開範囲など）を選択")
    print("  5. 投稿！")


if __name__ == '__main__':
    main()
