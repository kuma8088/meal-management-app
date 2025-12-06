#!/usr/bin/env python3
"""
Open Food Facts から栄養情報が完全な商品をCSVに抽出

大規模ファイル（4.2M行）から、必要なカラムと栄養情報が完全な商品のみを抽出
"""

import sys
import gzip
import csv
from pathlib import Path
from typing import List, Tuple


def extract_nutrition_complete_products(
    input_file: str,
    output_file: str,
    max_rows: int = 50000  # デフォルト: 最初の50,000行をサンプル
) -> Tuple[int, int]:
    """
    Open Food Facts CSVから栄養情報が完全な商品を抽出

    Args:
        input_file: 入力GZIPファイルパス
        output_file: 出力CSVファイルパス
        max_rows: 処理する最大行数（メモリ節約用）

    Returns:
        (処理行数, 抽出行数)
    """
    # 必須カラム（栄養情報）
    required_columns = {
        'product_name': None,
        'brands': None,
        'code': None,
        'energy-kcal_100g': None,
        'proteins_100g': None,
        'fat_100g': None,
        'carbohydrates_100g': None,
        'fiber_100g': None,
        'salt_100g': None,
        'categories': None,
    }

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"エラー: {input_file} が見つかりません")
        return 0, 0

    print(f"処理開始: {input_file}")
    print(f"最大処理行数: {max_rows:,}")

    processed_count = 0
    extracted_count = 0

    try:
        # GZIPファイルを読み込み
        with gzip.open(input_path, 'rt', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)

            # ヘッダーを確認
            if not reader.fieldnames:
                print("エラー: ヘッダーが見つかりません")
                return 0, 0

            # 利用可能なカラムを確認
            available_columns = set(reader.fieldnames) if reader.fieldnames else set()
            print(f"利用可能なカラム数: {len(available_columns)}")

            # 必須カラムのマッピング
            column_indices = {}
            for col in required_columns:
                if col in available_columns:
                    column_indices[col] = col
                else:
                    print(f"警告: カラム '{col}' が見つかりません")

            # 出力ファイルを作成
            output_columns = list(column_indices.keys())

            with open(output_path, 'w', newline='', encoding='utf-8-sig') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=output_columns)
                writer.writeheader()

                # データを処理
                for row in reader:
                    processed_count += 1

                    # 進捗表示
                    if processed_count % 100000 == 0:
                        print(f"  処理中: {processed_count:,}行 (抽出: {extracted_count:,}行)")

                    # 最大行数に達したら終了
                    if processed_count > max_rows:
                        break

                    # 栄養情報が完全かチェック
                    is_complete = True
                    for col in output_columns:
                        value = row.get(col, '').strip()
                        # 栄養値カラムが空またはnullの場合はスキップ
                        if col != 'product_name' and col != 'brands' and col != 'code' and col != 'categories':
                            if not value:
                                is_complete = False
                                break

                    # 必須フィールド（product_name, code）のチェック
                    if not row.get('product_name', '').strip() or not row.get('code', '').strip():
                        is_complete = False

                    # 栄養情報が完全な場合のみ抽出
                    if is_complete:
                        # 出力行を準備
                        output_row = {}
                        for col in output_columns:
                            output_row[col] = row.get(col, '').strip()

                        writer.writerow(output_row)
                        extracted_count += 1

    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return processed_count, extracted_count

    print(f"\n✓ 完了")
    print(f"  処理行数: {processed_count:,}行")
    print(f"  抽出行数: {extracted_count:,}行")
    print(f"  抽出率: {extracted_count / processed_count * 100:.2f}%")
    print(f"  出力ファイル: {output_path}")

    return processed_count, extracted_count


def main():
    """メイン処理"""
    input_file = "/Users/naoya/Develop/mealmgtsystem/data/en.openfoodfacts.org.products.csv.gz"
    output_file = "/Users/naoya/Develop/mealmgtsystem/data/openfoodfacts_sample.csv"
    max_rows = 50000  # サンプル: 最初の50,000行

    # コマンドライン引数で上書き可能
    if len(sys.argv) > 1:
        max_rows = int(sys.argv[1])

    print(f"Open Food Facts 抽出ツール")
    print(f"=".ljust(50, "="))
    extract_nutrition_complete_products(input_file, output_file, max_rows)


if __name__ == "__main__":
    main()
