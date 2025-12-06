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

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            if not reader.fieldnames:
                error_msg = "ヘッダーが見つかりません"
                print(f"エラー: {error_msg}")
                return 0, 0, [error_msg]

            print(f"カラム数: {len(reader.fieldnames)}")
            print(f"ヘッダー: {', '.join(list(reader.fieldnames)[:10])}...")

            row_count = 0

            for row in reader:
                row_count += 1

                if row_count > max_rows:
                    break

                # 進捗表示
                if row_count % 10 == 0:
                    print(f"  処理中: {row_count}行 (成功: {imported_count}行)")

                try:
                    # 食品データを構築
                    food_item = {
                        'food_id': str(uuid.uuid4()),  # ユニークID
                        'food_group': str(row.get('食\u3000品\u3000群', '')).strip() or 'unknown',
                        'food_number': str(row.get('食\u3000品\u3000番\u3000号', '')).strip() or '',
                        'food_name': str(row.get('食\u3000品\u3000名', '')).strip() or 'unknown',
                        'source': 'japanese_standard',
                        'calories': 0,  # デフォルト値
                        'protein': 0,
                        'fat': 0,
                        'carbs': 0,
                        'created_at': int(__import__('time').time()),
                    }

                    # 栄養情報を抽出（カラム名が複雑なため、対応するカラムを探す）
                    for key, value in row.items():
                        try:
                            val = float(str(value).strip()) if value and str(value).strip() else None
                        except (ValueError, TypeError):
                            val = None

                        # カロリーを探す
                        if 'エネルギー' in key or 'kcal' in key.lower():
                            if val is not None:
                                food_item['calories'] = val

                        # タンパク質を探す
                        if 'たんぱく質' in key or 'protein' in key.lower():
                            if val is not None and 'アミノ酸' not in key:
                                food_item['protein'] = val

                        # 脂質を探す
                        if '脂質' in key or 'fat' in key.lower():
                            if val is not None and 'トリアシル' not in key:
                                food_item['fat'] = val

                        # 炭水化物を探す
                        if '炭水化物' in key or 'carb' in key.lower():
                            if val is not None and '利用可能' not in key:
                                food_item['carbs'] = val

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
    table_name = "Foods"
    max_rows = 100  # テスト: 最初の100行

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
