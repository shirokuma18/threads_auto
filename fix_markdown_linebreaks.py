#!/usr/bin/env python3
"""
マークダウンファイルの改行を調整するスクリプト

修正内容:
1. 通常の改行: 空行（連続する改行）を削除して、シンプルな改行のみにする
2. --- の前後: 必ず1行ずつ空行を入れる
"""

import os
import re
from pathlib import Path


def fix_markdown_linebreaks(content: str) -> str:
    """
    マークダウンの改行を調整する

    Args:
        content: 元のマークダウンテキスト

    Returns:
        修正後のマークダウンテキスト
    """
    # 1. 複数の連続する空行を1つの改行に置き換え（ただし --- の前後は除外）
    # まず --- を一時的にマーカーに置き換える
    content = re.sub(r'\n---\n', '\n__HORIZONTAL_RULE__\n', content)

    # 複数の連続する改行を1つの改行に
    content = re.sub(r'\n\n+', '\n', content)

    # --- を復元し、前後に1行ずつ空行を追加
    content = re.sub(r'\n?__HORIZONTAL_RULE__\n?', '\n\n---\n\n', content)

    # ファイル先頭の余分な空行を削除
    content = content.lstrip('\n')

    # ファイル末尾は1つの改行で終わるようにする
    content = content.rstrip('\n') + '\n'

    return content


def process_directory(directory: str):
    """
    ディレクトリ内の全 .md ファイルを処理

    Args:
        directory: 処理対象のディレクトリパス
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"エラー: ディレクトリが存在しません: {directory}")
        return

    md_files = list(dir_path.glob("*.md"))

    if not md_files:
        print(f"警告: .md ファイルが見つかりません: {directory}")
        return

    print(f"処理開始: {len(md_files)} 個のファイルを処理します\n")

    processed_count = 0

    for md_file in sorted(md_files):
        try:
            # ファイルを読み込み
            with open(md_file, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 改行を修正
            fixed_content = fix_markdown_linebreaks(original_content)

            # 変更があった場合のみ書き込み
            if original_content != fixed_content:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"✓ 修正: {md_file.name}")
                processed_count += 1
            else:
                print(f"- スキップ: {md_file.name} (変更なし)")

        except Exception as e:
            print(f"✗ エラー: {md_file.name} - {e}")

    print(f"\n処理完了: {processed_count} 個のファイルを修正しました")


if __name__ == "__main__":
    # note_articles ディレクトリを処理
    note_articles_dir = "note_articles"

    print("=" * 60)
    print("マークダウン改行修正スクリプト")
    print("=" * 60)
    print()

    process_directory(note_articles_dir)
