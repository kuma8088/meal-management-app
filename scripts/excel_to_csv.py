#!/usr/bin/env python3
"""
日本食品標準成分表（Excel）をCSVに変換するスクリプト

使用方法:
    python3 scripts/excel_to_csv.py input.xlsx output.csv [シート名]

例:
    # 基本食品成分表を変換
    python3 scripts/excel_to_csv.py data/20230428-mxt_kagsei-mext_00001_012.xlsx food_master.csv "表全体"

    # 特定のシート名を指定
    python3 scripts/excel_to_csv.py data/20230428-mxt_kagsei-mext_00001_012.xlsx food_master.csv
"""

import sys
import csv
from pathlib import Path
from typing import Optional


def convert_japanese_food_table_to_csv(
    excel_file: str,
    csv_file: str,
    sheet_name: Optional[str] = None
) -> None:
    """
    日本食品標準成分表（八訂）をCSVに変換

    複雑なマルチレベルヘッダー構造に対応

    Args:
        excel_file: 入力Excelファイルパス
        csv_file: 出力CSVファイルパス
        sheet_name: 変換するシート名（Noneの場合は「表全体」を使用）
    """
    try:
        # openpyxlをインポート
        try:
            from openpyxl import load_workbook
        except ImportError:
            print("エラー: openpyxlがインストールされていません")
            print("インストール: pip install openpyxl")
            sys.exit(1)

        excel_path = Path(excel_file)
        csv_path = Path(csv_file)

        # ファイルの存在確認
        if not excel_path.exists():
            print(f"エラー: ファイルが見つかりません: {excel_file}")
            sys.exit(1)

        # Excelファイルを開く
        print(f"読み込み中: {excel_file}")
        workbook = load_workbook(excel_path, data_only=True)

        # シートを選択（デフォルトは「表全体」）
        if sheet_name is None:
            sheet_name = "表全体"

        if sheet_name not in workbook.sheetnames:
            print(f"エラー: シート '{sheet_name}' が見つかりません")
            print(f"利用可能なシート: {', '.join(workbook.sheetnames)}")
            sys.exit(1)

        worksheet = workbook[sheet_name]
        print(f"使用するシート: {worksheet.title}")

        # CSVに書き込み
        print(f"変換中...")
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # 日本食品標準成分表の構造：
            # - 行1：更新日
            # - 行2-7：マルチレベルヘッダー（複数行に分散）
            # - 行13以降：実データ

            row_count = 0

            # マルチレベルヘッダーを統合
            # 日本食品標準成分表の特殊な構造に対応：
            # - 列1-3: Row 2から取得（食品群、食品番号、索引番号）
            # - 列4以降: Row 3から取得（食品名、栄養値など）
            header_candidates = []
            for col_idx in range(1, 66):  # 65カラム
                header_value = ""

                if col_idx <= 3:
                    # 最初の3列はRow 2から取得
                    cell = worksheet.cell(row=2, column=col_idx)
                    if cell.value:
                        header_value = str(cell.value).strip()
                else:
                    # 4列目以降はRow 3から取得
                    cell = worksheet.cell(row=3, column=col_idx)
                    if cell.value:
                        header_value = str(cell.value).strip()
                    else:
                        # Row 3に値がなければRow 2を確認
                        cell = worksheet.cell(row=2, column=col_idx)
                        if cell.value:
                            header_value = str(cell.value).strip()

                header_candidates.append(header_value)

            writer.writerow(header_candidates)
            row_count += 1
            print(f"  ヘッダー: {len(header_candidates)}カラム")

            # データ行（行13以降）を書き込み
            data_start_row = 13
            for row in worksheet.iter_rows(min_row=data_start_row, values_only=True):
                # 空行をスキップ
                if not any(row):
                    continue

                # セル値をクリーンアップ
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append('')
                    elif isinstance(cell, (int, float)):
                        cleaned_row.append(str(cell))
                    else:
                        cell_str = str(cell).strip()
                        # 複数行にわたったセル値を1行に
                        cell_str = cell_str.replace('\n', ' ')
                        cleaned_row.append(cell_str)

                writer.writerow(cleaned_row)
                row_count += 1

        print(f"✓ 完了: {csv_path}")
        print(f"  ヘッダー行: 1行")
        print(f"  データ行: {row_count - 1}行")
        print(f"  合計: {row_count}行")
        print(f"\n次のステップ:")
        print(f"  1. CSVをLambda関数にアップロード")
        print(f"  2. DynamoDBに食品データが保存されます")
        print(f"  3. AI検索時にS3のCSVを参照")

    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """メイン処理"""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    excel_file = sys.argv[1]
    csv_file = sys.argv[2]
    sheet_name = sys.argv[3] if len(sys.argv) > 3 else None

    convert_japanese_food_table_to_csv(excel_file, csv_file, sheet_name)


if __name__ == "__main__":
    main()
