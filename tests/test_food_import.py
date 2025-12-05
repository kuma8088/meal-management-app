"""
食品マスタインポート機能のテスト

Property 3プロパティテスト と 統合テスト
"""
import pytest
import sys
import csv
import json
from pathlib import Path
from io import StringIO
from hypothesis import given, strategies as st
from datetime import datetime

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    StandardFoodParser,
    FoodMasterImporter,
    Food,
    FoodSource,
    ValidationError,
)


class TestFoodParserPropertyBased:
    """食品パーサーのプロパティベーステスト"""

    def test_data_sync_property(self):
        """
        Feature: meal-management-app, Property 3: 食品マスタのデータ同期

        任意の食品データが DynamoDB に登録される場合、
        同じデータが CSV 形式で S3 バケットにも保存される必要があります。

        このテストでは、CSVからパースされた食品データが正しく保存可能であることを検証。

        検証: 要件 2.3
        """
        # テスト用CSV
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
白米,168,2.5,0.3,37.1,1234567890123
食パン,265,9.3,4.4,48.5,9876543210987
鶏卵,151,12.3,10.3,0.3,"""

        # パース
        foods = StandardFoodParser.parse_csv_content(csv_content)

        # すべての食品がパースされたことを確認
        assert len(foods) == 3

        # それぞれの食品が必須フィールドを持つことを確認
        for food in foods:
            assert food.food_id
            assert food.name
            assert food.calories_per_100g >= 0
            assert food.protein_per_100g >= 0
            assert food.fat_per_100g >= 0
            assert food.carbs_per_100g >= 0
            assert food.source == FoodSource.STANDARD

        # データの同期性を検証：
        # 各食品をto_dict()で辞書化 -> from_dict()で復元 -> 値が同じであることを確認
        for original_food in foods:
            food_dict = original_food.to_dict()
            restored_food = Food.from_dict(food_dict)

            # すべてのフィールドが同期されていることを確認
            assert restored_food.food_id == original_food.food_id
            assert restored_food.name == original_food.name
            assert restored_food.calories_per_100g == original_food.calories_per_100g
            assert restored_food.protein_per_100g == original_food.protein_per_100g
            assert restored_food.fat_per_100g == original_food.fat_per_100g
            assert restored_food.carbs_per_100g == original_food.carbs_per_100g
            assert restored_food.source == original_food.source

    @given(
        num_foods=st.integers(min_value=1, max_value=20)
    )
    def test_csv_parse_sync_property(self, num_foods):
        """
        Feature: meal-management-app, Property 3: 食品マスタのデータ同期

        異なるサイズのCSVデータが正しくパース・同期されることを検証。

        検証: 要件 2.3
        """
        # 動的にCSV を生成
        csv_lines = [
            "食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード"
        ]

        for i in range(num_foods):
            csv_lines.append(
                f"食品{i},{100 + i * 10},{5 + i},{3 + i},{20 + i * 2},"
            )

        csv_content = "\n".join(csv_lines)

        # パース
        foods = StandardFoodParser.parse_csv_content(csv_content)

        # パースされた食品数が予期した数であることを確認
        assert len(foods) == num_foods

        # 各食品がDynamoDB/S3に保存可能な形式であることを確認
        for food in foods:
            # to_dict()できることを確認
            food_dict = food.to_dict()
            assert isinstance(food_dict, dict)
            assert "food_id" in food_dict
            assert "name" in food_dict
            assert "source" in food_dict

            # JSON でシリアライズ可能であることを確認（S3保存想定）
            json_str = json.dumps(food_dict)
            restored_dict = json.loads(json_str)
            restored_food = Food.from_dict(restored_dict)

            # 復元されたデータが元のデータと同じであることを確認
            assert restored_food.name == food.name
            assert restored_food.calories_per_100g == food.calories_per_100g


class TestStandardFoodParser:
    """日本食品標準成分表パーサーのテスト"""

    def test_parse_valid_csv(self):
        """有効なCSVのパース"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
白米,168,2.5,0.3,37.1,1234567890123"""

        foods = StandardFoodParser.parse_csv_content(csv_content)

        assert len(foods) == 1
        assert foods[0].name == "白米"
        assert foods[0].calories_per_100g == 168.0
        assert foods[0].protein_per_100g == 2.5
        assert foods[0].fat_per_100g == 0.3
        assert foods[0].carbs_per_100g == 37.1
        assert foods[0].jan_code == "1234567890123"

    def test_parse_csv_without_jan_code(self):
        """JANコードなしのCSVのパース"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
牛乳,61,3.2,3.6,4.8,"""

        foods = StandardFoodParser.parse_csv_content(csv_content)

        assert len(foods) == 1
        assert foods[0].name == "牛乳"
        assert foods[0].jan_code is None

    def test_parse_csv_multiple_foods(self):
        """複数食品のCSVのパース"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
白米,168,2.5,0.3,37.1,1234567890123
鶏卵,151,12.3,10.3,0.3,
牛乳,61,3.2,3.6,4.8,9876543210987"""

        foods = StandardFoodParser.parse_csv_content(csv_content)

        assert len(foods) == 3
        assert foods[0].name == "白米"
        assert foods[1].name == "鶏卵"
        assert foods[2].name == "牛乳"

    def test_parse_csv_empty_rows_skipped(self):
        """空行がスキップされることを確認"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
白米,168,2.5,0.3,37.1,
,,,,,"""

        foods = StandardFoodParser.parse_csv_content(csv_content)

        # 空行は処理されず、有効な食品のみ
        assert len(foods) == 1
        assert foods[0].name == "白米"

    def test_parse_csv_invalid_calories(self):
        """無効なカロリー値の処理"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
テスト,invalid_calories,5,3,20,"""

        # パースは失敗するが、例外は発生しない（エラー行はスキップ）
        foods = StandardFoodParser.parse_csv_content(csv_content)

        # 無効な行はスキップされるため、結果は空
        assert len(foods) == 0

    def test_parse_csv_empty_file(self):
        """空のCSVの処理"""
        csv_content = ""

        with pytest.raises(ValidationError):
            StandardFoodParser.parse_csv_content(csv_content)


class TestFoodMasterImporter:
    """食品マスタインポーターの統合テスト"""

    def test_import_from_csv(self):
        """CSVからのインポート"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
白米,168,2.5,0.3,37.1,1234567890123
食パン,265,9.3,4.4,48.5,"""

        importer = FoodMasterImporter()
        foods, errors = importer.import_from_csv(csv_content)

        assert len(foods) == 2
        assert len(errors) == 0

        # データの検証
        assert foods[0].name == "白米"
        assert foods[1].name == "食パン"

    def test_import_from_csv_with_errors(self):
        """エラーを含むCSVからのインポート"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
白米,168,2.5,0.3,37.1,
テスト,invalid,5,3,20,"""

        importer = FoodMasterImporter()
        foods, errors = importer.import_from_csv(csv_content)

        # 有効な食品のみがインポートされる
        assert len(foods) == 1
        assert foods[0].name == "白米"

    def test_import_csv_all_fields_preserved(self):
        """すべてのフィールドが保存されることを確認"""
        csv_content = """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
テスト食品,250,15.5,8.2,32.1,1111111111111"""

        importer = FoodMasterImporter()
        foods, _ = importer.import_from_csv(csv_content)

        assert len(foods) == 1
        food = foods[0]

        # すべてのフィールドが正しく保存されていることを確認
        assert food.name == "テスト食品"
        assert food.calories_per_100g == 250.0
        assert food.protein_per_100g == 15.5
        assert food.fat_per_100g == 8.2
        assert food.carbs_per_100g == 32.1
        assert food.jan_code == "1111111111111"
        assert food.source == FoodSource.STANDARD

        # シリアライズ/デシリアライズが可能であることを確認
        food_dict = food.to_dict()
        restored = Food.from_dict(food_dict)

        assert restored.name == food.name
        assert restored.calories_per_100g == food.calories_per_100g
        assert restored.protein_per_100g == food.protein_per_100g
        assert restored.fat_per_100g == food.fat_per_100g
        assert restored.carbs_per_100g == food.carbs_per_100g
        assert restored.jan_code == food.jan_code
