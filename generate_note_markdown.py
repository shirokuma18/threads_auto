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

    # タイトルを強烈にする（コンセプトが伝わる形に）
    # タイトル案のマッピング
    powerful_titles = {
        '鈴の音': '「先生、うるさいです」転校生のランドセルについた鈴が教えてくれたこと',
        '居場所のない子': '「ここにいてはいけない」毎日教室で立ち尽くす子どもの本当の理由',
        '先生の正義': '「叩かなければ分からない子もいる」ベテラン教師との価値観の衝突',
        'テストの点数': '「100点取れなかったら怒られる」成績と親の期待に潰される子ども',
        '参観日の階段': '「親が来ない子」参観日、階段で待ち続けた生徒の姿',
        '消しゴムの嘘': '「盗んだでしょ」新品の消しゴムが暴いた家庭の貧困',
        '百点の孤独': '「友達いらない」いつも100点の優等生が抱える孤立',
        '世代の壁': '「最近の若い先生は」ベテラン教師との世代間ギャップ',
        '受験の呪い': '「中学受験がすべて」プレッシャーで壊れていく子ども',
        '給食の残り': '「お腹すいた」給食を何度もおかわりする子の背景',
        '白衣の匂い': '「お母さん、今日も帰ってこない」医療従事者の親を持つ子の寂しさ',
        '名前の呼び方': '「さん付けで呼ばないで」ジェンダーと教室の境界線',
        '親の背中': '「お父さんみたいになりたくない」親の仕事を恥じる子ども',
        '窓際の席': '「あの子と隣は嫌」席替えが暴く子どもたちの本音',
        '一番後ろの席': '「背が高いから」いつも最後列の生徒が見ていた景色',
        '放課後の選択': '「塾があるから」放課後、教室に残れない子どもたち',
        '診断の呪縛': '「発達障害だから仕方ない」診断名に縛られる教育現場',
        '班分け': '「あの子とは組みたくない」班分けで露呈する人間関係',
        '上履き': '「新しいの買ってもらえない」ボロボロの上履きが物語ること',
        '名札': '「名札つけたくない」個人情報と子どもの安全',
        '遅刻': '「また遅刻」毎朝遅れてくる生徒の家庭事情',
        '公園の声': '「うるさい」公園で遊べない子どもたちの現実',
        '実習の残照': '「先生になりたかった」教育実習生が見た教室の闇',
        '夢の値段': '「夢なんてない」将来の夢を語れない子どもたち',
        '夏休みの飢餓': '「給食がないと食べられない」夏休み、痩せて帰ってくる子',
        '絵の具セット': '「お金ないから買えない」図工の授業で分かる格差',
        '借りた言葉': '「親が言ってた」子どもの口から出る大人の価値観',
        '診断の呪縛': '「診断名がないと支援できない」ラベリングされる子どもたち',
        '祖父の時代': '「昔はよかった」祖父母の価値観が子育てに与える影響',
        'AIの時代': '「ChatGPTで書きました」AI時代の宿題と創造性',
        '言葉の重さ': '「死ね」軽々しく使われる言葉の暴力',
        '逃げる瞬間': '「学校行きたくない」不登校の始まりの瞬間',
        '見えない差': '「普通の家庭」という幻想、経済格差の現実',
        '遊べない公園': '「ボール禁止、走るの禁止」遊び場を失った子どもたち',
        '大人の背中': '「大人なんて信じられない」裏切られ続けた子どもの心',
        'キラキラの嘘': '「キラキラネーム恥ずかしい」名前で傷つく子どもたち',
        '虫歯の痛み': '「歯医者に連れて行ってもらえない」ネグレクトの兆候',
    }

    # 強烈なタイトルを取得（デフォルトは元のタイトル）
    powerful_title = powerful_titles.get(subcategory, f'【教室の真実】{subcategory}')

    # note用Markdown生成
    markdown = f"""# {powerful_title}

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
