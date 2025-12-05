"""
AI食品検索ロジックのテスト

Property 5, 6のプロパティテスト、および統合テスト
"""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    AIFoodSearch,
    Food,
    FoodSource,
    ValidationError,
    ExternalServiceError,
)


class TestAIFoodSearchPropertyBased:
    """AI食品検索のプロパティベーステスト"""

    @given(
        food_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")
    )
    def test_ai_search_result_marking_property(self, food_name):
        """
        Feature: meal-management-app, Property 5: AI検索結果のマーキング

        任意のAI検索によって見つかった食品は、DynamoDBに保存される際に
        データソースフィールドが「AI_GENERATED」に設定される必要があります。

        検証: 要件 3.4, 3.5
        """
        # モックのBedrock応答
        mock_bedrock_response = {
            "name": food_name,
            "calories_per_100g": 100.0,
            "protein_per_100g": 10.0,
            "fat_per_100g": 5.0,
            "carbs_per_100g": 15.0,
            "jan_code": None
        }

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュなし）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = []
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            saved_item = None

            def capture_put_item(item):
                nonlocal saved_item
                saved_item = item
                return item

            mock_db_helper.put_item.side_effect = capture_put_item
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper.get_object.return_value = f"name,calories,protein,fat,carbs\n{food_name},100,10,5,15"
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック
            mock_bedrock_runtime = Mock()
            mock_response_body = {
                "content": [
                    {
                        "text": json.dumps(mock_bedrock_response)
                    }
                ]
            }
            mock_bedrock_runtime.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode())
            }
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行
            result = ai_search.search_with_ai(food_name)

            # Property 5 の検証: 結果のsourceがAI_GENERATEDである
            assert result is not None
            assert result.source == FoodSource.AI_GENERATED, \
                f"AI検索結果のsourceが{result.source}ですが、AI_GENERATEDである必要があります"

            # DynamoDBに保存されたアイテムも確認
            assert saved_item is not None
            assert saved_item["source"] == "AI_GENERATED", \
                f"DynamoDBに保存されたsourceが{saved_item['source']}ですが、AI_GENERATEDである必要があります"

    @given(
        food_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")
    )
    def test_food_search_caching_property(self, food_name):
        """
        Feature: meal-management-app, Property 6: 食品検索のキャッシング

        任意の食品が一度AI検索で見つかった場合、同じ食品の2回目の検索では
        DynamoDBのキャッシュから結果が返され、Bedrock APIは呼び出されない
        必要があります。

        検証: 要件 3.6
        """
        # クエリをstrip()後の値にする（AIFoodSearchと同じ処理）
        query = food_name.strip()

        # モックのキャッシュされた食品
        cached_food = Food(
            food_id="cached_food_1",
            name=query,
            calories_per_100g=100.0,
            protein_per_100g=10.0,
            fat_per_100g=5.0,
            carbs_per_100g=15.0,
            jan_code=None,
            source=FoodSource.AI_GENERATED,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュあり）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = [cached_food]
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック
            mock_bedrock_runtime = Mock()
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行
            result = ai_search.search_with_ai(food_name)

            # Property 6 の検証: キャッシュから結果が返される
            assert result is not None
            assert result.food_id == cached_food.food_id
            assert result.name == cached_food.name
            assert result.source == FoodSource.AI_GENERATED

            # Bedrock APIが呼び出されていないことを確認
            mock_bedrock_runtime.invoke_model.assert_not_called()

            # S3アクセスもされていないことを確認
            mock_s3_helper.get_object.assert_not_called()


class TestAIFoodSearch:
    """AI食品検索クラスの統合テスト"""

    def test_search_with_ai_success(self):
        """AI検索が成功する場合"""
        query = "鶏むね肉"

        mock_bedrock_response = {
            "name": "鶏むね肉",
            "calories_per_100g": 108.0,
            "protein_per_100g": 22.3,
            "fat_per_100g": 1.5,
            "carbs_per_100g": 0.0,
            "jan_code": None
        }

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュなし）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = []
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper.put_item.return_value = {}
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper.get_object.return_value = "name,calories,protein,fat,carbs\n鶏むね肉,108,22.3,1.5,0"
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック
            mock_bedrock_runtime = Mock()
            mock_response_body = {
                "content": [
                    {
                        "text": json.dumps(mock_bedrock_response)
                    }
                ]
            }
            mock_bedrock_runtime.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode())
            }
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行
            result = ai_search.search_with_ai(query)

            # 検証
            assert result is not None
            assert result.name == "鶏むね肉"
            assert result.calories_per_100g == 108.0
            assert result.source == FoodSource.AI_GENERATED

            # DynamoDBに保存されたことを確認
            mock_db_helper.put_item.assert_called_once()

    def test_search_with_ai_not_found(self):
        """AI検索で食品が見つからない場合"""
        query = "存在しない食品XYZ"

        mock_bedrock_response = {
            "found": False
        }

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュなし）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = []
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper.get_object.return_value = "name,calories,protein,fat,carbs\n"
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック
            mock_bedrock_runtime = Mock()
            mock_response_body = {
                "content": [
                    {
                        "text": json.dumps(mock_bedrock_response)
                    }
                ]
            }
            mock_bedrock_runtime.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode())
            }
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行
            result = ai_search.search_with_ai(query)

            # 検証
            assert result is None

            # DynamoDBには保存されていないことを確認
            mock_db_helper.put_item.assert_not_called()

    def test_search_with_ai_cached(self):
        """キャッシュから結果が返される場合"""
        query = "白米"

        cached_food = Food(
            food_id="cached_food_1",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            jan_code=None,
            source=FoodSource.AI_GENERATED,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュあり）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = [cached_food]
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック
            mock_bedrock_runtime = Mock()
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行
            result = ai_search.search_with_ai(query)

            # 検証
            assert result is not None
            assert result.food_id == cached_food.food_id
            assert result.name == "白米"
            assert result.source == FoodSource.AI_GENERATED

            # Bedrock APIが呼び出されていないことを確認
            mock_bedrock_runtime.invoke_model.assert_not_called()

            # S3アクセスもされていないことを確認
            mock_s3_helper.get_object.assert_not_called()

    def test_search_with_ai_empty_query(self):
        """空のクエリでのバリデーション"""
        ai_search = AIFoodSearch()

        with pytest.raises(ValidationError):
            ai_search.search_with_ai("")

    def test_search_with_ai_whitespace_query(self):
        """空白のみのクエリでのバリデーション"""
        ai_search = AIFoodSearch()

        with pytest.raises(ValidationError):
            ai_search.search_with_ai("   ")

    def test_search_with_ai_without_caching(self):
        """キャッシュせずにAI検索を実行する場合"""
        query = "鶏もも肉"

        mock_bedrock_response = {
            "name": "鶏もも肉",
            "calories_per_100g": 200.0,
            "protein_per_100g": 16.2,
            "fat_per_100g": 14.0,
            "carbs_per_100g": 0.0,
            "jan_code": None
        }

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュなし）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = []
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper.get_object.return_value = "name,calories,protein,fat,carbs\n鶏もも肉,200,16.2,14,0"
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック
            mock_bedrock_runtime = Mock()
            mock_response_body = {
                "content": [
                    {
                        "text": json.dumps(mock_bedrock_response)
                    }
                ]
            }
            mock_bedrock_runtime.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode())
            }
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行（キャッシュなし）
            result = ai_search.search_with_ai(query, save_to_cache=False)

            # 検証
            assert result is not None
            assert result.name == "鶏もも肉"
            assert result.source == FoodSource.AI_GENERATED

            # DynamoDBには保存されていないことを確認
            mock_db_helper.put_item.assert_not_called()

    def test_search_with_ai_bedrock_error(self):
        """Bedrock APIエラーの場合"""
        query = "鶏ささみ"

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュなし）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = []
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper.get_object.return_value = "name,calories,protein,fat,carbs\n"
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック（エラー）
            mock_bedrock_runtime = Mock()
            mock_bedrock_runtime.invoke_model.side_effect = Exception("Bedrock API error")
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行してエラーが発生することを確認
            with pytest.raises(ExternalServiceError):
                ai_search.search_with_ai(query)

    def test_search_with_ai_invalid_bedrock_response(self):
        """Bedrock APIが無効なJSONを返す場合"""
        query = "豆腐"

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュなし）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = []
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper.get_object.return_value = "name,calories,protein,fat,carbs\n"
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック（無効なJSON）
            mock_bedrock_runtime = Mock()
            mock_response_body = {
                "content": [
                    {
                        "text": "This is not valid JSON"
                    }
                ]
            }
            mock_bedrock_runtime.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode())
            }
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行してエラーが発生することを確認
            with pytest.raises(ExternalServiceError):
                ai_search.search_with_ai(query)

    def test_search_with_ai_missing_required_fields(self):
        """Bedrock APIが必須フィールドを欠いた応答を返す場合"""
        query = "納豆"

        mock_bedrock_response = {
            "name": "納豆",
            "calories_per_100g": 200.0
            # protein, fat, carbsが欠けている
        }

        with patch("common.ai_food_search.boto3") as mock_boto3, \
             patch("common.ai_food_search.FoodSearch") as mock_food_search_class, \
             patch("common.ai_food_search.DynamoDBHelper") as mock_db_helper_class, \
             patch("common.ai_food_search.S3Helper") as mock_s3_helper_class:

            # FoodSearchモック（キャッシュなし）
            mock_food_search = Mock()
            mock_food_search.search_by_name.return_value = []
            mock_food_search_class.return_value = mock_food_search

            # DynamoDBHelperモック
            mock_db_helper = Mock()
            mock_db_helper_class.return_value = mock_db_helper

            # S3Helperモック
            mock_s3_helper = Mock()
            mock_s3_helper.get_object.return_value = "name,calories,protein,fat,carbs\n"
            mock_s3_helper_class.return_value = mock_s3_helper

            # Bedrockモック
            mock_bedrock_runtime = Mock()
            mock_response_body = {
                "content": [
                    {
                        "text": json.dumps(mock_bedrock_response)
                    }
                ]
            }
            mock_bedrock_runtime.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode())
            }
            mock_boto3.client.return_value = mock_bedrock_runtime

            # AIFoodSearchインスタンスを作成
            ai_search = AIFoodSearch()

            # AI検索を実行
            result = ai_search.search_with_ai(query)

            # 必須フィールドが欠けている場合はNoneが返される
            assert result is None
