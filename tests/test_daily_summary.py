"""
1日の総評とAIアドバイス生成Lambda関数のテスト

要件: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9
プロパティ: 20, 21, 22
"""
import json
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, ANY
from hypothesis import given, strategies as st

# テスト対象
import sys
import os
from pathlib import Path

# src/lambda/commonとdaily_summaryをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "daily_summary"))

from daily_summary import lambda_handler


class TestDailySummary:
    """Daily summary Lambda function tests"""

    @pytest.fixture
    def mock_meals_db(self):
        """Meals DynamoDB helper mock"""
        with patch('daily_summary.meals_db') as mock:
            mock.table = MagicMock()
            yield mock

    @pytest.fixture
    def mock_users_db(self):
        """Users DynamoDB helper mock"""
        with patch('daily_summary.users_db') as mock:
            yield mock

    @pytest.fixture
    def mock_goals_db(self):
        """Goals DynamoDB helper mock"""
        with patch('daily_summary.goals_db') as mock:
            mock.table = MagicMock()
            yield mock

    @pytest.fixture
    def mock_advice_usage_db(self):
        """AdviceUsage DynamoDB helper mock"""
        with patch('daily_summary.advice_usage_db') as mock:
            mock.table = MagicMock()
            yield mock

    @pytest.fixture
    def mock_bedrock_runtime(self):
        """Bedrock runtime client mock"""
        with patch('daily_summary.bedrock_runtime') as mock:
            yield mock

    @pytest.mark.integration
    def test_generate_daily_advice_success(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime
    ):
        """
        Feature: meal-management-app
        正常系: 1日の食事記録の総評とアドバイスを取得できる
        要件: 10.1, 10.4, 10.5, 10.6, 10.7
        """
        # アドバイス生成回数はまだ0回
        mock_advice_usage_db.get_item.side_effect = Exception("Not found")

        # 1日の食事記録
        today = date.today()
        mock_meals_db.table.query.return_value = {
            "Items": [
                {
                    "meal_id": "meal_1",
                    "user_id": "user_123",
                    "timestamp": datetime.combine(today, datetime.min.time()).isoformat(),
                    "total_calories": Decimal("500.0"),
                    "total_protein": Decimal("20.0"),
                    "total_fat": Decimal("15.0"),
                    "total_carbs": Decimal("60.0")
                },
                {
                    "meal_id": "meal_2",
                    "user_id": "user_123",
                    "timestamp": datetime.combine(today, datetime.max.time()).isoformat(),
                    "total_calories": Decimal("700.0"),
                    "total_protein": Decimal("30.0"),
                    "total_fat": Decimal("20.0"),
                    "total_carbs": Decimal("80.0")
                }
            ]
        }

        # ユーザーの目標カロリー
        mock_goals_db.table.query.return_value = {
            "Items": [
                {
                    "goal_id": "goal_1",
                    "user_id": "user_123",
                    "target_calories": Decimal("2000.0")
                }
            ]
        }

        # Bedrock APIのレスポンス
        mock_bedrock_runtime.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"text": "良いバランスの食事です。この調子で続けましょう。"}]
            }).encode())
        }

        # アドバイス生成
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_123",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # 要件: 10.4 - 栄養情報の集計
        assert body["total_calories"] == 1200.0  # 500 + 700
        assert body["total_protein"] == 50.0      # 20 + 30
        assert body["total_fat"] == 35.0          # 15 + 20
        assert body["total_carbs"] == 140.0       # 60 + 80

        # 要件: 10.5 - 目標カロリーとの比較
        assert body["target_calories"] == 2000.0
        assert body["calorie_difference"] == -800.0  # 1200 - 2000

        # 要件: 10.6, 10.7 - AIアドバイス生成
        assert "advice" in body
        assert len(body["advice"]) > 0
        assert len(body["advice"]) <= 300  # 要件: 10.7

        # 要件: 10.8 - 利用回数のカウント
        assert body["usage_count"] == 1
        assert body["usage_limit_reached"] is False

        # Bedrock APIが呼ばれたことを確認
        mock_bedrock_runtime.invoke_model.assert_called_once()

    @pytest.mark.integration
    def test_usage_limit_reached(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime
    ):
        """
        Feature: meal-management-app
        利用制限: 1日2回までアドバイス生成できる
        要件: 10.2
        プロパティ: 20
        """
        # すでに2回アドバイス生成済み
        today = date.today()
        usage_key = f"user_123#{today.isoformat()}"
        mock_advice_usage_db.get_item.return_value = {
            "usage_key": usage_key,
            "user_id": "user_123",
            "date": today.isoformat(),
            "usage_count": 2
        }

        # アドバイス生成を試みる
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_123",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # 利用制限に達していることを確認
        assert body["usage_limit_reached"] is True
        assert body["usage_count"] == 2
        assert "本日のアドバイス生成は2回までです" in body["message"]

        # Bedrock APIは呼ばれない
        mock_bedrock_runtime.invoke_model.assert_not_called()

    @pytest.mark.integration
    def test_missing_required_fields(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime
    ):
        """
        Feature: meal-management-app
        エラー系: 必須フィールドがない場合はエラー
        """
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_123"
                # "date" が欠落
            })
        }

        response = lambda_handler(event, None)

        # バリデーションエラー
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    @pytest.mark.integration
    def test_invalid_date_format(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime
    ):
        """
        Feature: meal-management-app
        エラー系: 無効な日付フォーマット
        """
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_123",
                "date": "2024/03/15"  # 無効なフォーマット
            })
        }

        response = lambda_handler(event, None)

        # バリデーションエラー
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    @pytest.mark.integration
    def test_empty_meals_for_day(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime
    ):
        """
        Feature: meal-management-app
        正常系: 食事記録がない日でもアドバイス生成できる
        要件: 10.3, 10.4
        """
        # アドバイス生成回数は0回
        mock_advice_usage_db.get_item.side_effect = Exception("Not found")

        # 食事記録なし
        today = date.today()
        mock_meals_db.table.query.return_value = {"Items": []}

        # 目標カロリー
        mock_goals_db.table.query.return_value = {
            "Items": [
                {
                    "goal_id": "goal_1",
                    "user_id": "user_123",
                    "target_calories": Decimal("2000.0")
                }
            ]
        }

        # Bedrock APIのレスポンス
        mock_bedrock_runtime.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"text": "本日はまだ食事記録がありません。"}]
            }).encode())
        }

        # アドバイス生成
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_123",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # すべて0
        assert body["total_calories"] == 0.0
        assert body["total_protein"] == 0.0
        assert body["total_fat"] == 0.0
        assert body["total_carbs"] == 0.0

        # カロリー差は目標の負数
        assert body["target_calories"] == 2000.0
        assert body["calorie_difference"] == -2000.0

    @pytest.mark.integration
    def test_no_goal_falls_back_to_tdee(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime
    ):
        """
        Feature: meal-management-app
        正常系: 目標が設定されていない場合はTDEEを使用
        要件: 10.5
        """
        # アドバイス生成回数は0回
        mock_advice_usage_db.get_item.side_effect = Exception("Not found")

        # 食事記録
        today = date.today()
        mock_meals_db.table.query.return_value = {
            "Items": [
                {
                    "meal_id": "meal_1",
                    "user_id": "user_123",
                    "timestamp": datetime.combine(today, datetime.min.time()).isoformat(),
                    "total_calories": Decimal("1800.0"),
                    "total_protein": Decimal("70.0"),
                    "total_fat": Decimal("60.0"),
                    "total_carbs": Decimal("200.0")
                }
            ]
        }

        # 目標なし
        mock_goals_db.table.query.return_value = {"Items": []}

        # ユーザーのTDEE
        mock_users_db.get_item.return_value = {
            "user_id": "user_123",
            "tdee": Decimal("2400.0")
        }

        # Bedrock APIのレスポンス
        mock_bedrock_runtime.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"text": "目標に近い良い食事です。"}]
            }).encode())
        }

        # アドバイス生成
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_123",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # TDEEが使用されている
        assert body["target_calories"] == 2400.0
        assert body["calorie_difference"] == -600.0  # 1800 - 2400

    @pytest.mark.integration
    def test_bedrock_error_fallback(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime
    ):
        """
        Feature: meal-management-app
        正常系: Bedrock APIエラー時はフォールバックメッセージを返す
        要件: 10.6
        """
        # アドバイス生成回数は0回
        mock_advice_usage_db.get_item.side_effect = Exception("Not found")

        # 食事記録
        today = date.today()
        mock_meals_db.table.query.return_value = {
            "Items": [
                {
                    "meal_id": "meal_1",
                    "user_id": "user_123",
                    "timestamp": datetime.combine(today, datetime.min.time()).isoformat(),
                    "total_calories": Decimal("2300.0"),
                    "total_protein": Decimal("80.0"),
                    "total_fat": Decimal("70.0"),
                    "total_carbs": Decimal("250.0")
                }
            ]
        }

        # 目標カロリー
        mock_goals_db.table.query.return_value = {
            "Items": [
                {
                    "goal_id": "goal_1",
                    "user_id": "user_123",
                    "target_calories": Decimal("2000.0")
                }
            ]
        }

        # Bedrock APIエラー
        mock_bedrock_runtime.invoke_model.side_effect = Exception("API Error")

        # アドバイス生成
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_123",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # フォールバックメッセージが返される
        assert "advice" in body
        assert len(body["advice"]) > 0
        # カロリー超過のメッセージ
        assert "目標カロリーを超過" in body["advice"] or "超過" in body["advice"]

    # ========================================
    # Property-based tests
    # ========================================

    @pytest.mark.property
    @given(usage_count=st.integers(min_value=0, max_value=10))
    @patch('daily_summary.bedrock_runtime')
    @patch('daily_summary.advice_usage_db')
    @patch('daily_summary.goals_db')
    @patch('daily_summary.users_db')
    @patch('daily_summary.meals_db')
    def test_usage_limit_property(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime,
        usage_count
    ):
        """
        Feature: meal-management-app, Property 20: アドバイス生成の利用制限
        任意の利用回数において、2回以上の場合はアドバイス生成が制限される
        要件: 10.2
        """
        # モックテーブルの設定
        mock_meals_db.table = MagicMock()
        mock_goals_db.table = MagicMock()
        mock_advice_usage_db.table = MagicMock()
        today = date.today()
        usage_key = f"user_test#{today.isoformat()}"

        if usage_count >= 2:
            # すでに2回以上使用済み
            mock_advice_usage_db.get_item.return_value = {
                "usage_key": usage_key,
                "user_id": "user_test",
                "date": today.isoformat(),
                "usage_count": usage_count
            }
        else:
            # まだ制限に達していない
            mock_advice_usage_db.get_item.return_value = {
                "usage_key": usage_key,
                "user_id": "user_test",
                "date": today.isoformat(),
                "usage_count": usage_count
            }

            # 食事記録
            mock_meals_db.table.query.return_value = {"Items": []}

            # 目標カロリー
            mock_goals_db.table.query.return_value = {
                "Items": [{"target_calories": Decimal("2000.0")}]
            }

            # Bedrock APIのレスポンス
            mock_bedrock_runtime.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps({
                    "content": [{"text": "アドバイスです。"}]
                }).encode())
            }

        # アドバイス生成
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_test",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Property 20: 2回以上の場合は制限される
        if usage_count >= 2:
            assert body["usage_limit_reached"] is True
            assert "本日のアドバイス生成は2回までです" in body.get("message", "")
        else:
            # まだ制限に達していない
            assert body["usage_limit_reached"] is False or body["usage_limit_reached"] == (usage_count + 1 >= 2)

    @pytest.mark.property
    @given(
        meals=st.lists(
            st.fixed_dictionaries({
                "calories": st.floats(min_value=0, max_value=1000),
                "protein": st.floats(min_value=0, max_value=100),
                "fat": st.floats(min_value=0, max_value=100),
                "carbs": st.floats(min_value=0, max_value=200)
            }),
            min_size=0,
            max_size=10
        )
    )
    @patch('daily_summary.bedrock_runtime')
    @patch('daily_summary.advice_usage_db')
    @patch('daily_summary.goals_db')
    @patch('daily_summary.users_db')
    @patch('daily_summary.meals_db')
    def test_daily_aggregation_property(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime,
        meals
    ):
        """
        Feature: meal-management-app, Property 21: 1日の食事集計
        任意の食事記録リストにおいて、集計結果は各食事の栄養情報の合計と一致する
        要件: 10.3, 10.4
        """
        # モックテーブルの設定
        mock_meals_db.table = MagicMock()
        mock_goals_db.table = MagicMock()
        mock_advice_usage_db.table = MagicMock()
        # アドバイス生成回数は0回
        mock_advice_usage_db.get_item.side_effect = Exception("Not found")

        # 食事記録を作成
        today = date.today()
        meal_items = []
        expected_total_calories = 0.0
        expected_total_protein = 0.0
        expected_total_fat = 0.0
        expected_total_carbs = 0.0

        for i, meal in enumerate(meals):
            meal_items.append({
                "meal_id": f"meal_{i}",
                "user_id": "user_test",
                "timestamp": datetime.combine(today, datetime.min.time()).isoformat(),
                "total_calories": Decimal(str(meal["calories"])),
                "total_protein": Decimal(str(meal["protein"])),
                "total_fat": Decimal(str(meal["fat"])),
                "total_carbs": Decimal(str(meal["carbs"]))
            })
            expected_total_calories += meal["calories"]
            expected_total_protein += meal["protein"]
            expected_total_fat += meal["fat"]
            expected_total_carbs += meal["carbs"]

        mock_meals_db.table.query.return_value = {"Items": meal_items}

        # 目標カロリー
        mock_goals_db.table.query.return_value = {
            "Items": [{"target_calories": Decimal("2000.0")}]
        }

        # Bedrock APIのレスポンス
        mock_bedrock_runtime.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"text": "アドバイスです。"}]
            }).encode())
        }

        # アドバイス生成
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_test",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Property 21: 集計結果は合計と一致する
        assert body["total_calories"] == pytest.approx(expected_total_calories, abs=0.1)
        assert body["total_protein"] == pytest.approx(expected_total_protein, abs=0.1)
        assert body["total_fat"] == pytest.approx(expected_total_fat, abs=0.1)
        assert body["total_carbs"] == pytest.approx(expected_total_carbs, abs=0.1)

    @pytest.mark.property
    @given(advice_text=st.text(min_size=0, max_size=1000))
    def test_advice_length_limit_property(self, advice_text):
        """
        Feature: meal-management-app, Property 22: アドバイスの文字数制限
        任意のアドバイス文字列において、最終的なアドバイスは300文字以内である
        要件: 10.7
        """
        from daily_summary import truncate_advice

        # アドバイスを切り詰める
        truncated = truncate_advice(advice_text, 300)

        # Property 22: 300文字以内
        assert len(truncated) <= 300

        # 元の文字列が300文字以下の場合は変更されない
        if len(advice_text) <= 300:
            assert truncated == advice_text
        else:
            # 300文字に切り詰められている
            assert len(truncated) == 300
            assert truncated.endswith("...")

    @pytest.mark.property
    @given(initial_count=st.integers(min_value=0, max_value=1))
    @patch('daily_summary.bedrock_runtime')
    @patch('daily_summary.advice_usage_db')
    @patch('daily_summary.goals_db')
    @patch('daily_summary.users_db')
    @patch('daily_summary.meals_db')
    def test_usage_counter_increment_property(
        self,
        mock_meals_db,
        mock_users_db,
        mock_goals_db,
        mock_advice_usage_db,
        mock_bedrock_runtime,
        initial_count
    ):
        """
        Feature: meal-management-app, Property 23: アドバイス生成回数のカウンター更新
        任意のアドバイスが正常に生成される場合、ユーザーの1日のアドバイス生成回数が1増加する
        要件: 10.8
        """
        # モックテーブルの設定
        mock_meals_db.table = MagicMock()
        mock_goals_db.table = MagicMock()
        mock_advice_usage_db.table = MagicMock()

        today = date.today()
        usage_key = f"user_test#{today.isoformat()}"

        # 初期カウント
        if initial_count > 0:
            mock_advice_usage_db.get_item.return_value = {
                "usage_key": usage_key,
                "user_id": "user_test",
                "date": today.isoformat(),
                "usage_count": initial_count
            }
        else:
            mock_advice_usage_db.get_item.side_effect = Exception("Not found")

        # 食事記録
        mock_meals_db.table.query.return_value = {"Items": []}

        # 目標カロリー
        mock_goals_db.table.query.return_value = {
            "Items": [{"target_calories": Decimal("2000.0")}]
        }

        # Bedrock APIのレスポンス
        mock_bedrock_runtime.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"text": "アドバイスです。"}]
            }).encode())
        }

        # アドバイス生成
        event = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": "user_test",
                "date": today.isoformat()
            })
        }

        response = lambda_handler(event, None)

        # レスポンスの検証
        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Property 23: カウンターが1増加している
        assert body["usage_count"] == initial_count + 1

        # update_itemが呼ばれたことを確認
        mock_advice_usage_db.table.update_item.assert_called_once()


class TestDailySummaryUnitTests:
    """Daily summary unit tests"""

    @pytest.mark.unit
    def test_aggregate_daily_meals_empty(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 食事記録がない場合の集計
        """
        from daily_summary import aggregate_daily_meals

        with patch('daily_summary.meals_db') as mock_meals_db:
            mock_meals_db.table = MagicMock()
            mock_meals_db.table.query.return_value = {"Items": []}

            result = aggregate_daily_meals("user_123", date.today())

            assert result["total_calories"] == 0.0
            assert result["total_protein"] == 0.0
            assert result["total_fat"] == 0.0
            assert result["total_carbs"] == 0.0

    @pytest.mark.unit
    def test_aggregate_daily_meals_single(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 1つの食事記録の集計
        """
        from daily_summary import aggregate_daily_meals

        with patch('daily_summary.meals_db') as mock_meals_db:
            mock_meals_db.table = MagicMock()
            mock_meals_db.table.query.return_value = {
                "Items": [
                    {
                        "meal_id": "meal_1",
                        "total_calories": Decimal("500.0"),
                        "total_protein": Decimal("20.0"),
                        "total_fat": Decimal("15.0"),
                        "total_carbs": Decimal("60.0")
                    }
                ]
            }

            result = aggregate_daily_meals("user_123", date.today())

            assert result["total_calories"] == 500.0
            assert result["total_protein"] == 20.0
            assert result["total_fat"] == 15.0
            assert result["total_carbs"] == 60.0

    @pytest.mark.unit
    def test_aggregate_daily_meals_multiple(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 複数の食事記録の集計
        """
        from daily_summary import aggregate_daily_meals

        with patch('daily_summary.meals_db') as mock_meals_db:
            mock_meals_db.table = MagicMock()
            mock_meals_db.table.query.return_value = {
                "Items": [
                    {
                        "meal_id": "meal_1",
                        "total_calories": Decimal("500.0"),
                        "total_protein": Decimal("20.0"),
                        "total_fat": Decimal("15.0"),
                        "total_carbs": Decimal("60.0")
                    },
                    {
                        "meal_id": "meal_2",
                        "total_calories": Decimal("700.0"),
                        "total_protein": Decimal("30.0"),
                        "total_fat": Decimal("20.0"),
                        "total_carbs": Decimal("80.0")
                    }
                ]
            }

            result = aggregate_daily_meals("user_123", date.today())

            assert result["total_calories"] == 1200.0
            assert result["total_protein"] == 50.0
            assert result["total_fat"] == 35.0
            assert result["total_carbs"] == 140.0

    @pytest.mark.unit
    def test_check_usage_limit_no_record(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 利用記録がない場合
        """
        from daily_summary import check_usage_limit

        with patch('daily_summary.advice_usage_db') as mock_advice_usage_db:
            mock_advice_usage_db.get_item.side_effect = Exception("Not found")

            limit_reached, count = check_usage_limit("user_123", date.today())

            assert limit_reached is False
            assert count == 0

    @pytest.mark.unit
    def test_check_usage_limit_below_limit(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 利用制限以下の場合
        """
        from daily_summary import check_usage_limit

        with patch('daily_summary.advice_usage_db') as mock_advice_usage_db:
            today = date.today()
            usage_key = f"user_123#{today.isoformat()}"
            mock_advice_usage_db.get_item.return_value = {
                "usage_key": usage_key,
                "usage_count": 1
            }

            limit_reached, count = check_usage_limit("user_123", today)

            assert limit_reached is False
            assert count == 1

    @pytest.mark.unit
    def test_check_usage_limit_at_limit(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 利用制限に達した場合
        """
        from daily_summary import check_usage_limit

        with patch('daily_summary.advice_usage_db') as mock_advice_usage_db:
            today = date.today()
            usage_key = f"user_123#{today.isoformat()}"
            mock_advice_usage_db.get_item.return_value = {
                "usage_key": usage_key,
                "usage_count": 2
            }

            limit_reached, count = check_usage_limit("user_123", today)

            assert limit_reached is True
            assert count == 2

    @pytest.mark.unit
    def test_check_usage_limit_over_limit(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 利用制限を超えた場合
        """
        from daily_summary import check_usage_limit

        with patch('daily_summary.advice_usage_db') as mock_advice_usage_db:
            today = date.today()
            usage_key = f"user_123#{today.isoformat()}"
            mock_advice_usage_db.get_item.return_value = {
                "usage_key": usage_key,
                "usage_count": 5
            }

            limit_reached, count = check_usage_limit("user_123", today)

            assert limit_reached is True
            assert count == 5

    @pytest.mark.unit
    def test_truncate_advice_short_text(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 短いテキストの切り詰め
        """
        from daily_summary import truncate_advice

        text = "これは短いアドバイスです。"
        result = truncate_advice(text, 300)

        assert result == text
        assert len(result) <= 300

    @pytest.mark.unit
    def test_truncate_advice_exact_length(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: ちょうど300文字のテキスト
        """
        from daily_summary import truncate_advice

        text = "あ" * 300
        result = truncate_advice(text, 300)

        assert result == text
        assert len(result) == 300

    @pytest.mark.unit
    def test_truncate_advice_long_text(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 長いテキストの切り詰め
        """
        from daily_summary import truncate_advice

        text = "あ" * 500
        result = truncate_advice(text, 300)

        assert len(result) == 300
        assert result.endswith("...")
        # 297文字 + "..." = 300文字
        assert result == ("あ" * 297) + "..."

    @pytest.mark.unit
    def test_truncate_advice_empty_text(self):
        """
        Feature: meal-management-app, Task 15.5
        ユニットテスト: 空のテキスト
        """
        from daily_summary import truncate_advice

        text = ""
        result = truncate_advice(text, 300)

        assert result == ""
        assert len(result) == 0
