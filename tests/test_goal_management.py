"""
体重目標管理Lambda関数のテスト

統合テスト
"""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, date

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "goal_management"))

from goal_management import (
    lambda_handler,
    create_goal,
    list_goals,
    get_goal,
    update_goal
)

from common import (
    Goal,
    GoalType,
    ValidationError,
    ResourceNotFoundError
)


class TestGoalManagementIntegration:
    """体重目標管理Lambda関数の統合テスト"""

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_create_goal_success(self, mock_users_db, mock_goals_db):
        """体重目標の作成が成功する場合"""
        # モックユーザーデータ
        mock_user = {
            "user_id": "user_123",
            "age": 30,
            "height": 170.0,
            "weight": 70.0,
            "gender": "male",
            "activity_level": "moderate",
            "bmr": 1680.0,
            "tdee": 2604.0
        }

        mock_users_db.get_item.return_value = mock_user
        mock_goals_db.put_item.return_value = None

        # イベントデータ
        future_date = date.today() + __import__('datetime').timedelta(days=90)
        event = {
            "httpMethod": "POST",
            "path": "/goals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": "user_123",
                "current_weight": 70.0,
                "target_weight": 65.0,
                "target_date": future_date.isoformat(),  # 約3ヶ月後
                "goal_type": "lose"
            })
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "goal_id" in body
        assert body["daily_calorie_adjustment"] < 0  # 減量なのでマイナス
        assert body["target_calories"] < mock_user["tdee"]  # TDEEより低い
        assert body["recommended_protein"] > 0
        assert body["recommended_fat"] > 0
        assert body["recommended_carbs"] > 0
        assert body["recommended_exercise_minutes"] >= 0

        # DynamoDB put_itemが呼び出されたことを確認
        mock_goals_db.put_item.assert_called_once()
        saved_goal = mock_goals_db.put_item.call_args[0][0]
        assert saved_goal["user_id"] == "user_123"
        assert saved_goal["goal_type"] == "lose"

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_create_goal_missing_user_id(self, mock_users_db, mock_goals_db):
        """user_idが欠落している場合"""
        event = {
            "httpMethod": "POST",
            "path": "/goals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "current_weight": 70.0,
                "target_weight": 65.0,
                "target_date": "2024-04-15",
                "goal_type": "lose"
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "user_id" in body["error"]["message"]

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_create_goal_user_not_found(self, mock_users_db, mock_goals_db):
        """ユーザーが見つからない場合"""
        mock_users_db.get_item.return_value = None

        event = {
            "httpMethod": "POST",
            "path": "/goals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": "invalid_user",
                "current_weight": 70.0,
                "target_weight": 65.0,
                "target_date": "2024-04-15",
                "goal_type": "lose"
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "invalid_user" in body["error"]["message"]

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_create_goal_unrealistic_warning(self, mock_users_db, mock_goals_db):
        """非現実的な目標の場合に警告が返される"""
        # モックユーザーデータ
        mock_user = {
            "user_id": "user_123",
            "tdee": 2604.0
        }

        mock_users_db.get_item.return_value = mock_user
        mock_goals_db.put_item.return_value = None

        # 1ヶ月で5kg減量（週あたり1.25kg、非現実的）
        future_date = date.today() + __import__('datetime').timedelta(days=28)
        event = {
            "httpMethod": "POST",
            "path": "/goals",
            "pathParameters": None,
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": "user_123",
                "current_weight": 75.0,
                "target_weight": 70.0,
                "target_date": future_date.isoformat(),
                "goal_type": "lose"
            })
        }

        # 実行
        response = lambda_handler(event, None)

        # 検証
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "warning" in body
        assert "週あたり" in body["warning"]

    @patch("goal_management.goals_db")
    def test_list_goals_success(self, mock_goals_db):
        """体重目標リストの取得が成功する場合"""
        # モックデータ
        mock_goals = [
            {
                "goal_id": "goal_1",
                "user_id": "user_123",
                "goal_type": "lose",
                "target_weight": 65.0
            },
            {
                "goal_id": "goal_2",
                "user_id": "user_123",
                "goal_type": "maintain",
                "target_weight": 65.0
            }
        ]

        mock_goals_db.scan.return_value = mock_goals

        event = {
            "httpMethod": "GET",
            "path": "/goals",
            "pathParameters": None,
            "queryStringParameters": {"user_id": "user_123"}
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        assert len(body["goals"]) == 2

    @patch("goal_management.goals_db")
    def test_get_goal_success(self, mock_goals_db):
        """特定の体重目標の取得が成功する場合"""
        mock_goal = {
            "goal_id": "goal_123",
            "user_id": "user_123",
            "goal_type": "lose",
            "target_calories": 2000.0
        }

        mock_goals_db.get_item.return_value = mock_goal

        event = {
            "httpMethod": "GET",
            "path": "/goals/goal_123",
            "pathParameters": {"goal_id": "goal_123"},
            "queryStringParameters": {"user_id": "user_123"}
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["goal_id"] == "goal_123"
        assert body["user_id"] == "user_123"

    @patch("goal_management.goals_db")
    def test_get_goal_not_found(self, mock_goals_db):
        """体重目標が見つからない場合"""
        mock_goals_db.get_item.return_value = None

        event = {
            "httpMethod": "GET",
            "path": "/goals/invalid_goal",
            "pathParameters": {"goal_id": "invalid_goal"},
            "queryStringParameters": {}
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_update_goal_success(self, mock_users_db, mock_goals_db):
        """体重目標の更新が成功する場合"""
        # 既存の体重目標
        future_date = date.today() + __import__('datetime').timedelta(days=90)
        existing_goal = {
            "goal_id": "goal_123",
            "user_id": "user_123",
            "current_weight": 70.0,
            "target_weight": 65.0,
            "target_date": future_date.isoformat(),
            "goal_type": "lose",
            "daily_calorie_adjustment": -500.0,
            "target_calories": 2104.0,
            "recommended_protein": 150.0,
            "recommended_fat": 50.0,
            "recommended_carbs": 250.0,
            "recommended_exercise_minutes": 30
        }

        # ユーザーデータ
        mock_user = {
            "user_id": "user_123",
            "tdee": 2604.0
        }

        mock_goals_db.get_item.return_value = existing_goal
        mock_users_db.get_item.return_value = mock_user
        mock_goals_db.put_item.return_value = None

        event = {
            "httpMethod": "PUT",
            "path": "/goals/goal_123",
            "pathParameters": {"goal_id": "goal_123"},
            "queryStringParameters": None,
            "body": json.dumps({
                "user_id": "user_123",
                "target_weight": 60.0  # 目標体重を変更
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["target_weight"] == 60.0
        # 目標体重が変更されたので、再計算されているはず
        assert body["daily_calorie_adjustment"] != existing_goal["daily_calorie_adjustment"]


class TestGoalCalculationIntegration:
    """目標計算の統合テスト"""

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_goal_calculation_for_weight_loss(self, mock_users_db, mock_goals_db):
        """減量目標のカロリー計算が正しい"""
        mock_user = {
            "user_id": "user_123",
            "tdee": 2500.0
        }

        mock_users_db.get_item.return_value = mock_user
        mock_goals_db.put_item.return_value = None

        # 90日で5kg減量
        event = {
            "httpMethod": "POST",
            "path": "/goals",
            "body": json.dumps({
                "user_id": "user_123",
                "current_weight": 70.0,
                "target_weight": 65.0,
                "target_date": str(date.today() + __import__('datetime').timedelta(days=90)),
                "goal_type": "lose"
            })
        }

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        # 5kg × 7700kcal/kg ÷ 90日 ≈ -427 kcal/日
        assert body["daily_calorie_adjustment"] < 0
        assert abs(body["daily_calorie_adjustment"]) > 400
        assert abs(body["daily_calorie_adjustment"]) < 500

        # 目標カロリー = TDEE + 調整量
        expected_target_calories = 2500.0 + body["daily_calorie_adjustment"]
        assert body["target_calories"] == pytest.approx(expected_target_calories, abs=1.0)

        # PFCバランスが計算されている
        assert body["recommended_protein"] > 0
        assert body["recommended_fat"] > 0
        assert body["recommended_carbs"] > 0

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_goal_calculation_for_weight_gain(self, mock_users_db, mock_goals_db):
        """増量目標のカロリー計算が正しい"""
        mock_user = {
            "user_id": "user_123",
            "tdee": 2500.0
        }

        mock_users_db.get_item.return_value = mock_user
        mock_goals_db.put_item.return_value = None

        # 90日で5kg増量
        event = {
            "httpMethod": "POST",
            "path": "/goals",
            "body": json.dumps({
                "user_id": "user_123",
                "current_weight": 65.0,
                "target_weight": 70.0,
                "target_date": str(date.today() + __import__('datetime').timedelta(days=90)),
                "goal_type": "gain"
            })
        }

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        # 5kg × 7700kcal/kg ÷ 90日 ≈ +427 kcal/日
        assert body["daily_calorie_adjustment"] > 0
        assert body["daily_calorie_adjustment"] > 400
        assert body["daily_calorie_adjustment"] < 500

        # 目標カロリーがTDEEより高い
        assert body["target_calories"] > mock_user["tdee"]

    @patch("goal_management.goals_db")
    @patch("goal_management.users_db")
    def test_goal_calculation_for_maintenance(self, mock_users_db, mock_goals_db):
        """維持目標のカロリー計算が正しい"""
        mock_user = {
            "user_id": "user_123",
            "tdee": 2500.0
        }

        mock_users_db.get_item.return_value = mock_user
        mock_goals_db.put_item.return_value = None

        # 90日で体重維持
        event = {
            "httpMethod": "POST",
            "path": "/goals",
            "body": json.dumps({
                "user_id": "user_123",
                "current_weight": 65.0,
                "target_weight": 65.0,
                "target_date": str(date.today() + __import__('datetime').timedelta(days=90)),
                "goal_type": "maintain"
            })
        }

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        # 体重差がないのでカロリー調整量は0
        assert body["daily_calorie_adjustment"] == pytest.approx(0.0, abs=0.1)

        # 目標カロリーはTDEEと同じ
        assert body["target_calories"] == pytest.approx(mock_user["tdee"], abs=1.0)
