#!/usr/bin/env python3
"""
日本食品標準成分表をDynamoDBにインポート

食品マスタCSVをDynamoDBの Foods テーブルに保存する
"""

import sys
import csv
import json
import boto3
from pathlib import Path
from typing import Dict, List, Tuple
from decimal import Decimal
import uuid

# DynamoDBクライアント
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')


def import_food_master_csv(
    csv_file: str,
    table_name: str = 'Foods',
    max_rows: int = 100  # デフォルト: 最初の100行をテスト
) -> Tuple[int, int, List[str]]:
    """
    食品マスタCSVをDynamoDBにインポート

    Args:
        csv_file: 入力CSVファイルパス
        table_name: DynamoDB テーブル名
        max_rows: インポートする最大行数

    Returns:
        (インポート成功数, インポート失敗数, エラーメッセージリスト)
    """
    csv_path = Path(csv_file)

    if not csv_path.exists():
        print(f"エラー: {csv_file} が見つかりません")
        return 0, 0, [f"File not found: {csv_file}"]

    print(f"DynamoDBインポート開始: {csv_file}")
    print(f"テーブル: {table_name}")
    print(f"最大行数: {max_rows}")

    try:
        table = dynamodb.Table(table_name)
    except Exception as e:
        error_msg = f"DynamoDBテーブルへの接続失敗: {str(e)}"
        print(f"エラー: {error_msg}")
        return 0, 0, [error_msg]

    imported_count = 0
    failed_count = 0
    errors = []

    # 日本食品標準成分表のカラムインデックス（0-indexed）
    # ヘッダー構造: 食品群(0), 食品番号(1), 索引番号(2), 食品名(3), 廃棄率(4),
    #              エネルギーkJ(5), エネルギーkcal(6), 水分(7), たんぱく質(8), ..., 脂質(10), ..., 炭水化物(13)
    COL_FOOD_GROUP = 0
    COL_FOOD_NUMBER = 1
    COL_FOOD_NAME = 3
    COL_ENERGY_KCAL = 6  # kJは5、kcalは6
    COL_PROTEIN = 8
    COL_FAT = 10
    COL_CARBS = 13  # 炭水化物

    def parse_decimal(value: str) -> Decimal:
        """数値をDecimalに変換（括弧付き推定値も対応）"""
        if not value or not str(value).strip():
            return Decimal('0')
        try:
            clean = str(value).strip().replace('(', '').replace(')', '').replace('Tr', '0').replace('*', '').strip()
            if clean and clean != '-':
                return Decimal(clean)
        except:
            pass
        return Decimal('0')

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)

            # ヘッダー行をスキップ
            header = next(reader, None)
            if not header:
                error_msg = "ヘッダーが見つかりません"
                print(f"エラー: {error_msg}")
                return 0, 0, [error_msg]

            print(f"カラム数: {len(header)}")
            print(f"ヘッダー: {', '.join(header[:10])}...")
            print(f"使用カラム: エネルギー(kcal)={COL_ENERGY_KCAL}, たんぱく質={COL_PROTEIN}, 脂質={COL_FAT}, 炭水化物={COL_CARBS}")

            row_count = 0

            for row in reader:
                row_count += 1

                if row_count > max_rows:
                    break

                # 進捗表示
                if row_count % 100 == 0:
                    print(f"  処理中: {row_count}行 (成功: {imported_count}行)")

                try:
                    # カラム数チェック
                    if len(row) < 20:
                        continue

                    # 食品名が空の場合はスキップ
                    food_name = str(row[COL_FOOD_NAME]).strip()
                    if not food_name:
                        continue

                    # 食品データを構築（インデックスで直接参照）
                    food_item = {
                        'food_id': str(uuid.uuid4()),
                        'food_group': str(row[COL_FOOD_GROUP]).strip() or 'unknown',
                        'food_number': str(row[COL_FOOD_NUMBER]).strip() or '',
                        'food_name': food_name,
                        'source': 'japanese_standard',
                        'calories': parse_decimal(row[COL_ENERGY_KCAL]),
                        'protein': parse_decimal(row[COL_PROTEIN]),
                        'fat': parse_decimal(row[COL_FAT]),
                        'carbs': parse_decimal(row[COL_CARBS]),
                        'created_at': int(__import__('time').time()),
                    }

                    # DynamoDBに保存
                    table.put_item(Item=food_item)
                    imported_count += 1

                except Exception as e:
                    error_msg = f"行{row_count}: {str(e)}"
                    print(f"  ✗ {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1

        print(f"\n✓ インポート完了")
        print(f"  成功: {imported_count}行")
        print(f"  失敗: {failed_count}行")

        return imported_count, failed_count, errors

    except Exception as e:
        error_msg = f"予期しないエラー: {str(e)}"
        print(f"エラー: {error_msg}")
        import traceback
        traceback.print_exc()
        return 0, 0, [error_msg]


def main():
    """メイン処理"""
    csv_file = "/Users/naoya/Develop/mealmgtsystem/data/food_master.csv"
    table_name = "meal-management-app-foods-dev"  # 実際のAWSテーブル名
    max_rows = 2538  # デフォルト: 全行

    # コマンドライン引数で上書き可能
    if len(sys.argv) > 1:
        max_rows = int(sys.argv[1])
    if len(sys.argv) > 2:
        table_name = sys.argv[2]

    print(f"日本食品標準成分表インポートツール")
    print(f"=".ljust(50, "="))

    success, failed, errors = import_food_master_csv(csv_file, table_name, max_rows)

    if errors:
        print(f"\nエラー一覧（最初の10件）:")
        for error in errors[:10]:
            print(f"  - {error}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
