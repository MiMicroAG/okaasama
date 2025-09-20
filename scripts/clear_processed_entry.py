#!/usr/bin/env python3
"""
processed_files.json のエントリを削除するユーティリティ

使い方:
  - すべてクリア: python scripts/clear_processed_entry.py --all
  - ファイル名で削除: python scripts/clear_processed_entry.py --file IMG_1799.jpg --file IMG_1921.jpeg
"""

import argparse
import json
from pathlib import Path
from typing import List


def clear_entries(processed_path: Path, target_files: List[str], clear_all: bool) -> int:
	if not processed_path.exists():
		print(f"ファイルが存在しません: {processed_path}")
		return 0

	with open(processed_path, 'r', encoding='utf-8') as f:
		data = json.load(f)

	before = len(data)

	if clear_all:
		data = {}
	else:
		targets = set(target_files)
		data = {k: v for k, v in data.items() if v.get('file_name') not in targets}

	removed = before - len(data)

	with open(processed_path, 'w', encoding='utf-8') as f:
		json.dump(data, f, ensure_ascii=False, indent=2)

	return removed


def main():
	parser = argparse.ArgumentParser(description='processed_files.json のエントリ削除')
	parser.add_argument('--path', default=str(Path('お母様カレンダー') / 'processed_files.json'), help='processed_files.json のパス')
	parser.add_argument('--file', dest='files', action='append', help='削除するファイル名（複数可）')
	parser.add_argument('--all', action='store_true', help='全エントリを削除')
	args = parser.parse_args()

	processed_path = Path(args.path)

	if not args.all and not args.files:
		print('--all か --file を指定してください')
		return

	removed = clear_entries(processed_path, args.files or [], args.all)
	print(f"削除件数: {removed}")


if __name__ == '__main__':
	main()
