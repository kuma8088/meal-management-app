"""
食事登録Lambda関数のテスト

統合テストとプロパティベーステスト
"""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from hypothesis import given, strategies as st
from hypothesis import assume

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "meal_registration"))

from meal_registration import (
    lambda_handler,
    create_meal,
    list_meals,
    get_meal,
    update_meal,
    delete_meal
)

from common import (
    Meal,
    MealFood,
    Food,
    MealType,
    FoodSource,
    ValidationError,
    ResourceNotFoundError
)


class TestMealRegistrationIntegration:
    """食事登録Lambda関数の統合テスト"""

    @patch("meal_registration.meals_db")
    @patch("meal_registration.foods_db")
    def test_create_meal_success(self, mock_foods_db, mock_meals_db):
        """食事記録の作成が成功する場合"""
        # モック食品データ
        food_1 = Food(
            food_id="food_1",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            jan_code=None,
            source=FoodSource.STANDARD,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        food_2 = Food(
            food_id="food_2",
            name="鶏むね肉",
            calories_per_100g=108.0,
            protein_per_100g=22.3,
            fat_per_100g=1.5,
            carbs_per_100g=0.0,
            jan_code=None,
            source=FoodSource.STANDARD,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        # モックDB設定
        mock_foods_db.get_item.side_effect = lambda key: {
            "food_1": food_1.to_dict(),
            "food_2": food_2.to_dict()
        }.get(key["food_id"])

        mock_meals_db.put_item.return_value = None

        # イベントデータ
        event = {
            "httpMethod": "POST",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": "user_123",
                "foods": [
                    {"food_id": "food_1", "amount": 150.0},  # 白米 150g
                    {"food_id": "food_2", "amount": 100.0}   # 鶏むね肉 100g
                ],
                "meal_type": "lunch",
                "timestamp": "2024-01-15T12:00:00"
            })
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "meal_id" in body
        assert body["total_calories"] == pytest.approx(168.0 * 1.5 + 108.0, abs=0.1)
        assert body["total_protein"] == pytest.approx(2.5 * 1.5 + 22.3, abs=0.1)
        assert body["total_fat"] == pytest.approx(0.3 * 1.5 + 1.5, abs=0.1)
        assert body["total_carbs"] == pytest.approx(37.1 * 1.5, abs=0.1)

        # DynamoDB put_itemが呼び出されたことを確認
        mock_meals_db.put_item.assert_called_once()
        saved_meal = mock_meals_db.put_item.call_args[0][0]
        assert saved_meal["user_id"] == "user_123"
        assert saved_meal["meal_type"] == "lunch"

    @patch("meal_registration.meals_db")
    @patch("meal_registration.foods_db")
    def test_create_meal_missing_user_id(self, mock_foods_db, mock_meals_db):
        """user_idが欠落している場合"""
        event = {
            "httpMethod": "POST",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "foods": [{"food_id": "food_1", "amount": 150.0}],
                "meal_type": "lunch"
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "user_id" in body["error"]["message"]

    @patch("meal_registration.meals_db")
    @patch("meal_registration.foods_db")
    def test_create_meal_food_not_found(self, mock_foods_db, mock_meals_db):
        """食品が見つからない場合"""
        mock_foods_db.get_item.return_value = None

        event = {
            "httpMethod": "POST",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": "user_123",
                "foods": [{"food_id": "invalid_food", "amount": 150.0}],
                "meal_type": "lunch"
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "invalid_food" in body["error"]["message"]

    @patch("meal_registration.meals_db")
    def test_list_meals_success(self, mock_meals_db):
        """食事記録リストの取得が成功する場合"""
        # モックデータ
        mock_meals = [
            {
                "meal_id": "meal_1",
                "user_id": "user_123",
                "meal_type": "breakfast",
                "total_calories": 500.0,
                "timestamp": "2024-01-15T08:00:00"
            },
            {
                "meal_id": "meal_2",
                "user_id": "user_123",
                "meal_type": "lunch",
                "total_calories": 700.0,
                "timestamp": "2024-01-15T12:00:00"
            }
        ]

        # GSI1のqueryを使用するように変更
        mock_meals_db.table.query.return_value = {
            "Items": mock_meals,
            "LastEvaluatedKey": None
        }

        event = {
            "httpMethod": "GET",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": {"user_id": "user_123"}
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        assert len(body["meals"]) == 2
        assert body["has_more"] is False

    @patch("meal_registration.meals_db")
    def test_get_meal_success(self, mock_meals_db):
        """特定の食事記録の取得が成功する場合"""
        mock_meal = {
            "meal_id": "meal_123",
            "user_id": "user_123",
            "meal_type": "dinner",
            "total_calories": 800.0
        }

        mock_meals_db.get_item.return_value = mock_meal

        event = {
            "httpMethod": "GET",
            "path": "/meals/meal_123",
            "pathParameters": {"meal_id": "meal_123"},
            "queryStringParameters": {"user_id": "user_123"}
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["meal_id"] == "meal_123"
        assert body["user_id"] == "user_123"

    @patch("meal_registration.meals_db")
    def test_get_meal_not_found(self, mock_meals_db):
        """食事記録が見つからない場合"""
        mock_meals_db.get_item.return_value = None

        event = {
            "httpMethod": "GET",
            "path": "/meals/invalid_meal",
            "pathParameters": {"meal_id": "invalid_meal"},
            "queryStringParameters": {}
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    @patch("meal_registration.meals_db")
    @patch("meal_registration.foods_db")
    def test_update_meal_success(self, mock_foods_db, mock_meals_db):
        """食事記録の更新が成功する場合"""
        # 既存の食事記録
        existing_meal = {
            "meal_id": "meal_123",
            "user_id": "user_123",
            "meal_type": "lunch",
            "foods": [{"food_id": "food_1", "amount": 150.0}],
            "total_calories": 252.0,
            "total_protein": 3.75,
            "total_fat": 0.45,
            "total_carbs": 55.65,
            "timestamp": "2024-01-15T12:00:00"
        }

        # 新しい食品データ
        food_2 = Food(
            food_id="food_2",
            name="鶏むね肉",
            calories_per_100g=108.0,
            protein_per_100g=22.3,
            fat_per_100g=1.5,
            carbs_per_100g=0.0,
            jan_code=None,
            source=FoodSource.STANDARD,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        mock_meals_db.get_item.return_value = existing_meal
        mock_foods_db.get_item.return_value = food_2.to_dict()
        mock_meals_db.put_item.return_value = None

        event = {
            "httpMethod": "PUT",
            "path": "/meals/meal_123",
            "pathParameters": {"meal_id": "meal_123"},
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": "user_123",
                "foods": [{"food_id": "food_2", "amount": 100.0}]
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["total_calories"] == pytest.approx(108.0, abs=0.1)
        assert body["total_protein"] == pytest.approx(22.3, abs=0.1)

    @patch("meal_registration.meals_db")
    def test_delete_meal_success(self, mock_meals_db):
        """食事記録の削除が成功する場合"""
        existing_meal = {
            "meal_id": "meal_123",
            "user_id": "user_123",
            "meal_type": "snack",
            "total_calories": 200.0
        }

        mock_meals_db.get_item.return_value = existing_meal
        mock_meals_db.delete_item.return_value = None

        event = {
            "httpMethod": "DELETE",
            "path": "/meals/meal_123",
            "pathParameters": {"meal_id": "meal_123"},
            "queryStringParameters": {"user_id": "user_123"}
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["meal_id"] == "meal_123"

        # delete_itemが呼び出されたことを確認
        mock_meals_db.delete_item.assert_called_once_with({"meal_id": "meal_123"})


class TestPropertyBasedTests:
    """プロパティベーステスト"""

    @given(user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""))
    @patch("meal_registration.meals_db")
    @patch("meal_registration.foods_db")
    def test_meal_user_association_property(self, mock_foods_db, mock_meals_db, user_id):
        """
        Feature: meal-management-app, Property 2: 食事記録とユーザーの関連付け

        任意の食事記録が作成される場合、その記録は認証されたユーザーIDと
        関連付けられて保存される必要があります。

        検証: 要件 1.3
        """
        # モック食品データ
        food = Food(
            food_id="food_1",
            name="テスト食品",
            calories_per_100g=100.0,
            protein_per_100g=10.0,
            fat_per_100g=5.0,
            carbs_per_100g=15.0,
            jan_code=None,
            source=FoodSource.STANDARD,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        mock_foods_db.get_item.return_value = food.to_dict()
        mock_meals_db.put_item.return_value = None

        # イベントデータ
        event = {
            "httpMethod": "POST",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": user_id,
                "foods": [{"food_id": "food_1", "amount": 100.0}],
                "meal_type": "lunch",
                "timestamp": "2024-01-15T12:00:00"
            })
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証: レスポンスが成功している
        assert response["statusCode"] == 201

        # 検証: 保存された食事記録がuser_idと関連付けられている
        mock_meals_db.put_item.assert_called_once()
        saved_meal = mock_meals_db.put_item.call_args[0][0]
        assert saved_meal["user_id"] == user_id

    @given(
        user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        meal_type=st.sampled_from(["breakfast", "lunch", "dinner", "snack"]),
        amount=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @patch("meal_registration.meals_db")
    @patch("meal_registration.foods_db")
    def test_meal_storage_property(self, mock_foods_db, mock_meals_db, user_id, meal_type, amount):
        """
        Feature: meal-management-app, Property 10: 食事記録の保存

        任意の有効な食事情報が送信される場合、システムは食事記録を作成して
        データベースに保存する必要があります。

        検証: 要件 6.1
        """
        # モック食品データ
        food = Food(
            food_id="food_1",
            name="テスト食品",
            calories_per_100g=100.0,
            protein_per_100g=10.0,
            fat_per_100g=5.0,
            carbs_per_100g=15.0,
            jan_code=None,
            source=FoodSource.STANDARD,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        mock_foods_db.get_item.return_value = food.to_dict()
        mock_meals_db.put_item.return_value = None

        # イベントデータ
        event = {
            "httpMethod": "POST",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": user_id,
                "foods": [{"food_id": "food_1", "amount": amount}],
                "meal_type": meal_type,
                "timestamp": "2024-01-15T12:00:00"
            })
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証: レスポンスが成功している
        assert response["statusCode"] == 201

        # 検証: DynamoDBに保存された
        mock_meals_db.put_item.assert_called_once()

        # 検証: 保存されたデータが正しい
        saved_meal = mock_meals_db.put_item.call_args[0][0]
        assert saved_meal["user_id"] == user_id
        assert saved_meal["meal_type"] == meal_type
        assert len(saved_meal["foods"]) == 1
        assert saved_meal["foods"][0]["food_id"] == "food_1"
        assert saved_meal["foods"][0]["amount"] == amount

    @given(
        user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        other_user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")
    )
    @patch("meal_registration.meals_db")
    def test_user_data_isolation_property(self, mock_meals_db, user_id, other_user_id):
        """
        Feature: meal-management-app, Property 1: ユーザーデータ分離

        任意のユーザーが食事記録を取得する場合、返される記録はすべて
        そのユーザーのuser_idと関連付けられている必要があります。
        他のユーザーの記録が含まれてはいけません。

        検証: 要件 1.4
        """
        # 異なるユーザーIDの場合のみテスト
        assume(user_id != other_user_id)

        # モックデータ: user_idの食事記録と、other_user_idの食事記録を混在させる
        mock_meals = [
            {
                "meal_id": "meal_1",
                "user_id": user_id,
                "meal_type": "breakfast",
                "total_calories": 500.0
            },
            {
                "meal_id": "meal_2",
                "user_id": user_id,
                "meal_type": "lunch",
                "total_calories": 700.0
            },
            {
                "meal_id": "meal_3",
                "user_id": other_user_id,  # 他のユーザーの記録
                "meal_type": "dinner",
                "total_calories": 800.0
            }
        ]

        mock_meals_db.table.query.return_value = {
            "Items": mock_meals,
            "LastEvaluatedKey": None
        }

        # イベントデータ
        event = {
            "httpMethod": "GET",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": {"user_id": user_id}
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証: レスポンスが成功している
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # 検証: すべての返される記録がuser_idと関連付けられている
        for meal in body["meals"]:
            assert meal["user_id"] == user_id

        # 検証: other_user_idの記録が含まれていない
        meal_ids = [meal["meal_id"] for meal in body["meals"]]
        assert "meal_3" not in meal_ids

    @given(
        user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        other_user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")
    )
    @patch("meal_registration.meals_db")
    def test_user_data_isolation_get_meal_property(self, mock_meals_db, user_id, other_user_id):
        """
        Feature: meal-management-app, Property 1: ユーザーデータ分離 (get_meal)

        任意のユーザーが特定の食事記録を取得する場合、その記録が他のユーザーの
        ものである場合は、エラーを返す必要があります。

        検証: 要件 1.4
        """
        # 異なるユーザーIDの場合のみテスト
        assume(user_id != other_user_id)

        # モックデータ: other_user_idの食事記録
        mock_meal = {
            "meal_id": "meal_123",
            "user_id": other_user_id,
            "meal_type": "dinner",
            "total_calories": 800.0
        }

        mock_meals_db.get_item.return_value = mock_meal

        # イベントデータ: user_idが他のユーザーの記録を取得しようとする
        event = {
            "httpMethod": "GET",
            "path": "/meals/meal_123",
            "pathParameters": {"meal_id": "meal_123"},
            "queryStringParameters": {"user_id": user_id}
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証: 404エラーが返される（他のユーザーの記録はアクセスできない）
        assert response["statusCode"] == 404


class TestPeriodFilteringAndPagination:
    """期間フィルタリングとページネーションのテスト (Task 16)"""

    @pytest.mark.property
    @given(
        days_offset=st.integers(min_value=1, max_value=30),
        num_meals=st.integers(min_value=1, max_value=10)
    )
    @patch("meal_registration.meals_db")
    def test_period_filtering_property(self, mock_meals_db, days_offset, num_meals):
        """
        Feature: meal-management-app, Property 25: 期間フィルタリング
        任意の期間指定において、返される食事記録はすべて指定された期間内のタイムスタンプを持つ
        要件: 12.3
        """
        from datetime import datetime, timedelta

        # 期間を設定
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_offset)

        # 期間内の食事記録を生成
        meals_in_period = []
        for i in range(num_meals):
            timestamp = start_date + timedelta(hours=i * 2)
            meals_in_period.append({
                "meal_id": f"meal_{i}",
                "user_id": "user_test",
                "timestamp": timestamp.isoformat(),
                "total_calories": 500.0 + i * 100
            })

        # モック設定
        mock_meals_db.table = MagicMock()
        mock_meals_db.table.query.return_value = {
            "Items": meals_in_period,
            "LastEvaluatedKey": None
        }

        # イベントデータ
        event = {
            "httpMethod": "GET",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": {
                "user_id": "user_test",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Property 25: すべての記録が期間内
        for meal in body["meals"]:
            meal_timestamp = datetime.fromisoformat(meal["timestamp"])
            assert start_date <= meal_timestamp <= end_date

    @pytest.mark.unit
    @patch("meal_registration.meals_db")
    def test_list_meals_with_period_filter(self, mock_meals_db):
        """
        Feature: meal-management-app, Task 16.2
        ユニットテスト: 期間フィルタリングが正しく動作する
        """
        from datetime import datetime, timedelta

        # 期間を設定
        start_date = datetime(2024, 1, 1, 0, 0, 0)
        end_date = datetime(2024, 1, 31, 23, 59, 59)

        # モックデータ
        mock_meals = [
            {
                "meal_id": "meal_1",
                "user_id": "user_123",
                "timestamp": "2024-01-15T08:00:00",
                "total_calories": 500.0
            },
            {
                "meal_id": "meal_2",
                "user_id": "user_123",
                "timestamp": "2024-01-20T12:00:00",
                "total_calories": 700.0
            }
        ]

        mock_meals_db.table = MagicMock()
        mock_meals_db.table.query.return_value = {
            "Items": mock_meals,
            "LastEvaluatedKey": None
        }

        # イベントデータ
        event = {
            "httpMethod": "GET",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": {
                "user_id": "user_123",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        assert body["has_more"] is False

        # queryが正しいパラメータで呼ばれたことを確認
        mock_meals_db.table.query.assert_called_once()
        call_kwargs = mock_meals_db.table.query.call_args[1]
        assert "BETWEEN" in call_kwargs["KeyConditionExpression"]

    @pytest.mark.unit
    @patch("meal_registration.meals_db")
    def test_list_meals_with_pagination(self, mock_meals_db):
        """
        Feature: meal-management-app, Task 16.2
        ユニットテスト: ページネーションが正しく動作する
        """
        import base64

        # モックデータ（第1ページ）
        mock_meals_page1 = [
            {"meal_id": "meal_1", "user_id": "user_123", "timestamp": "2024-01-15T08:00:00"},
            {"meal_id": "meal_2", "user_id": "user_123", "timestamp": "2024-01-15T12:00:00"}
        ]

        last_evaluated_key = {
            "meal_id": "meal_2",
            "user_id": "user_123",
            "timestamp": "2024-01-15T12:00:00"
        }

        mock_meals_db.table = MagicMock()
        mock_meals_db.table.query.return_value = {
            "Items": mock_meals_page1,
            "LastEvaluatedKey": last_evaluated_key
        }

        # イベントデータ（第1ページ）
        event = {
            "httpMethod": "GET",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": {
                "user_id": "user_123",
                "limit": "2"
            }
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        assert body["has_more"] is True
        assert "next_token" in body

        # next_tokenが正しくエンコードされている
        next_token = body["next_token"]
        decoded = json.loads(base64.b64decode(next_token).decode())
        assert decoded["meal_id"] == "meal_2"

    @pytest.mark.unit
    @patch("meal_registration.meals_db")
    def test_list_meals_with_next_token(self, mock_meals_db):
        """
        Feature: meal-management-app, Task 16.2
        ユニットテスト: next_tokenを使った次ページ取得が正しく動作する
        """
        import base64

        # next_tokenを作成
        last_evaluated_key = {
            "meal_id": "meal_2",
            "user_id": "user_123",
            "timestamp": "2024-01-15T12:00:00"
        }
        next_token = base64.b64encode(json.dumps(last_evaluated_key).encode()).decode()

        # モックデータ（第2ページ）
        mock_meals_page2 = [
            {"meal_id": "meal_3", "user_id": "user_123", "timestamp": "2024-01-15T18:00:00"},
            {"meal_id": "meal_4", "user_id": "user_123", "timestamp": "2024-01-16T08:00:00"}
        ]

        mock_meals_db.table = MagicMock()
        mock_meals_db.table.query.return_value = {
            "Items": mock_meals_page2,
            "LastEvaluatedKey": None  # 最後のページ
        }

        # イベントデータ（第2ページ）
        event = {
            "httpMethod": "GET",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": {
                "user_id": "user_123",
                "limit": "2",
                "next_token": next_token
            }
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        assert body["has_more"] is False
        assert "next_token" not in body

        # ExclusiveStartKeyが正しく設定されたことを確認
        mock_meals_db.table.query.assert_called_once()
        call_kwargs = mock_meals_db.table.query.call_args[1]
        assert "ExclusiveStartKey" in call_kwargs
        assert call_kwargs["ExclusiveStartKey"]["meal_id"] == "meal_2"

    @pytest.mark.unit
    @patch("meal_registration.meals_db")
    def test_list_meals_invalid_next_token(self, mock_meals_db):
        """
        Feature: meal-management-app, Task 16.2
        ユニットテスト: 無効なnext_tokenの処理
        """
        # イベントデータ
        event = {
            "httpMethod": "GET",
            "path": "/meals",
            "pathParameters": None,
            "queryStringParameters": {
                "user_id": "user_123",
                "next_token": "invalid_token_123"
            }
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証: バリデーションエラー
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "next_token" in body["error"]["message"]
