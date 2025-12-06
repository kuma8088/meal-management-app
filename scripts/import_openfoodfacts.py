#!/usr/bin/env python3
"""
Open Food Facts から栄養情報が完全な商品を DynamoDB にインポート

使用方法:
    python3 scripts/import_openfoodfacts.py [max_rows]

例:
    # 全データを処理してインポート
    python3 scripts/import_openfoodfacts.py

    # 最初の100,000行のみ処理
    python3 scripts/import_openfoodfacts.py 100000
"""

import sys
import gzip
import csv
import boto3
from pathlib import Path
from typing import Dict, List, Tuple
from decimal import Decimal
import uuid
import time

# DynamoDBクライアント
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')


def safe_decimal(value: str) -> Decimal:
    """
    文字列を安全にDecimalに変換

    Args:
        value: 変換する文字列

    Returns:
        Decimal値（変換失敗時は Decimal('0')）
    """
    if not value or not str(value).strip():
        return Decimal('0')

    try:
        clean_value = str(value).strip().replace(',', '')
        if clean_value:
            return Decimal(clean_value)
    except:
        pass

    return Decimal('0')


def import_openfoodfacts_to_dynamodb(
    gzip_file: str,
    table_name: str = 'meal-management-app-foods-dev',
    max_rows: int = None
) -> Tuple[int, int, List[str]]:
    """
    Open Food Facts GZIP ファイルを DynamoDB にインポート

    Args:
        gzip_file: 入力 GZIP ファイルパス
        table_name: DynamoDB テーブル名
        max_rows: 処理する最大行数（Noneの場合は全行）

    Returns:
        (インポート成功数, 失敗数, エラーメッセージリスト)
    """
    gzip_path = Path(gzip_file)

    if not gzip_path.exists():
        print(f"エラー: {gzip_file} が見つかりません")
        return 0, 0, [f"File not found: {gzip_file}"]

    print(f"Open Food Facts インポート開始: {gzip_file}")
    print(f"テーブル: {table_name}")
    print(f"最大行数: {max_rows if max_rows else '無制限'}")

    try:
        table = dynamodb.Table(table_name)
    except Exception as e:
        error_msg = f"DynamoDBテーブルへの接続失敗: {str(e)}"
        print(f"エラー: {error_msg}")
        return 0, 0, [error_msg]

    imported_count = 0
    failed_count = 0
    skipped_count = 0
    errors = []

    # 必須カラム
    required_columns = {
        'product_name',
        'code',  # バーコード（JAN コード）
        'energy-kcal_100g',
        'proteins_100g',
        'fat_100g',
        'carbohydrates_100g',
    }

    try:
        with gzip.open(gzip_path, 'rt', encoding='utf-8', errors='replace') as infile:
            # タブ区切り（TSV）として読み込み
            reader = csv.DictReader(infile, delimiter='\t')

            if not reader.fieldnames:
                error_msg = "ヘッダーが見つかりません"
                print(f"エラー: {error_msg}")
                return 0, 0, [error_msg]

            print(f"カラム数: {len(reader.fieldnames)}")

            # 必須カラムの存在確認
            available_columns = set(reader.fieldnames)
            missing_columns = required_columns - available_columns

            if missing_columns:
                print(f"警告: 以下のカラムが見つかりません: {missing_columns}")

            row_count = 0
            batch_items = []
            batch_size = 25  # DynamoDB バッチ書き込み上限

            for row in reader:
                row_count += 1

                if max_rows and row_count > max_rows:
                    break

                # 進捗表示
                if row_count % 10000 == 0:
                    print(f"  処理中: {row_count:,}行 (インポート: {imported_count:,}, スキップ: {skipped_count:,})")

                try:
                    # 必須フィールドの確認
                    product_name = row.get('product_name', '').strip()
                    code = row.get('code', '').strip()

                    if not product_name or not code:
                        skipped_count += 1
                        continue

                    # 栄養情報の取得
                    calories = safe_decimal(row.get('energy-kcal_100g', ''))
                    protein = safe_decimal(row.get('proteins_100g', ''))
                    fat = safe_decimal(row.get('fat_100g', ''))
                    carbs = safe_decimal(row.get('carbohydrates_100g', ''))

                    # 栄養情報が不完全な場合はスキップ
                    if calories == 0 and protein == 0 and fat == 0 and carbs == 0:
                        skipped_count += 1
                        continue

                    # DynamoDB アイテムを構築
                    food_item = {
                        'food_id': str(uuid.uuid4()),
                        'food_name': product_name[:200],  # 長すぎる名前を切り詰め
                        'jan_code': code,
                        'source': 'openfoodfacts',
                        'calories': calories,
                        'protein': protein,
                        'fat': fat,
                        'carbs': carbs,
                        'created_at': int(time.time()),
                    }

                    # ブランド情報があれば追加
                    brands = row.get('brands', '').strip()
                    if brands:
                        food_item['brands'] = brands[:100]

                    # カテゴリ情報があれば追加
                    categories = row.get('categories', '').strip()
                    if categories:
                        food_item['categories'] = categories[:200]

                    batch_items.append(food_item)

                    # バッチサイズに達したら書き込み
                    if len(batch_items) >= batch_size:
                        try:
                            with table.batch_writer(overwrite_by_pkeys=['food_id']) as batch:
                                for item in batch_items:
                                    batch.put_item(Item=item)

                            imported_count += len(batch_items)
                            batch_items = []

                        except Exception as e:
                            error_msg = f"バッチ書き込み失敗（行{row_count}付近）: {str(e)}"
                            print(f"  ✗ {error_msg}")
                            errors.append(error_msg)
                            failed_count += len(batch_items)
                            batch_items = []

                except Exception as e:
                    error_msg = f"行{row_count}: {str(e)}"
                    if len(errors) < 10:  # 最初の10件のみ記録
                        errors.append(error_msg)
                    failed_count += 1

            # 残りのバッチを書き込み
            if batch_items:
                try:
                    with table.batch_writer(overwrite_by_pkeys=['food_id']) as batch:
                        for item in batch_items:
                            batch.put_item(Item=item)

                    imported_count += len(batch_items)

                except Exception as e:
                    error_msg = f"最終バッチ書き込み失敗: {str(e)}"
                    print(f"  ✗ {error_msg}")
                    errors.append(error_msg)
                    failed_count += len(batch_items)

        print(f"\n✓ インポート完了")
        print(f"  処理行数: {row_count:,}行")
        print(f"  インポート成功: {imported_count:,}行")
        print(f"  スキップ: {skipped_count:,}行（栄養情報不完全）")
        print(f"  失敗: {failed_count:,}行")

        return imported_count, failed_count, errors

    except Exception as e:
        error_msg = f"予期しないエラー: {str(e)}"
        print(f"エラー: {error_msg}")
        import traceback
        traceback.print_exc()
        return imported_count, failed_count, [error_msg]


def main():
    """メイン処理"""
    gzip_file = "/Users/naoya/Develop/mealmgtsystem/data/en.openfoodfacts.org.products.csv.gz"
    table_name = "meal-management-app-foods-dev"
    max_rows = None  # デフォルト: 全行

    # コマンドライン引数で上書き可能
    if len(sys.argv) > 1:
        max_rows = int(sys.argv[1])
    if len(sys.argv) > 2:
        table_name = sys.argv[2]

    print(f"Open Food Facts インポートツール")
    print(f"=" * 50)

    success, failed, errors = import_openfoodfacts_to_dynamodb(
        gzip_file, table_name, max_rows
    )

    if errors:
        print(f"\nエラー一覧（最初の10件）:")
        for error in errors[:10]:
            print(f"  - {error}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
