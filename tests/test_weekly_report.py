"""
週次レポート機能のテスト

要件: なし（アドオン機能）
"""
import pytest
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import boto3

# Lambda関数のインポートパスを設定
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "common"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "weekly_report"))

from common import DynamoDBHelper
from common.bedrock_helper import BedrockHelper
from common.line_helper import LINEHelper


class TestWeeklyReportFunctions:
    """週次レポート関数のテストクラス"""

    def test_calculate_weekly_statistics_no_meals(self, setup_dynamodb):
        """食事記録がない場合の統計計算"""
        import weekly_report

        user_id = "test-user-1"
        user_data = {"user_id": user_id, "tdee": 2000}

        stats = weekly_report.calculate_weekly_statistics(user_id, user_data)

        # 食事記録がない場合、統計はすべて0
        assert stats["avg_daily_calories"] == 0
        assert stats["goal_achieved_days"] == 0
        assert stats["meal_count"] == 0

    def test_calculate_weekly_statistics_with_meals(self, setup_dynamodb):
        """食事記録がある場合の統計計算"""
        import weekly_report

        user_id = "test-user-1"
        user_data = {"user_id": user_id, "tdee": 2000}

        # テスト用の食事記録を作成
        meals_table = setup_dynamodb["meals"]
        now = datetime.utcnow()

        # 今日の食事
        meals_table.put_item(
            Item={
                "meal_id": "meal-1",
                "user_id": user_id,
                "timestamp": now.isoformat(),
                "total_calories": 2000,
                "total_protein": 50,
                "total_fat": 70,
                "total_carbs": 250,
            }
        )

        # 昨日の食事
        yesterday = now - timedelta(days=1)
        meals_table.put_item(
            Item={
                "meal_id": "meal-2",
                "user_id": user_id,
                "timestamp": yesterday.isoformat(),
                "total_calories": 1800,
                "total_protein": 45,
                "total_fat": 65,
                "total_carbs": 230,
            }
        )

        stats = weekly_report.calculate_weekly_statistics(user_id, user_data)

        # 統計が計算されていることを確認
        assert stats["meal_count"] == 2
        assert stats["avg_daily_calories"] == pytest.approx(1900, rel=0.01)
        assert stats["avg_daily_protein"] == pytest.approx(47.5, rel=0.01)
        assert len(stats["daily_summaries"]) == 2

    def test_generate_ai_advice_success(self):
        """AIアドバイス生成の成功ケース"""
        import weekly_report

        statistics = {
            "avg_daily_calories": 2000,
            "goal_achieved_days": 6,
            "meal_count": 7,
        }
        user_data = {"tdee": 2000}

        with patch.object(
            weekly_report.bedrock,
            "generate_advice",
            return_value="良い進捗です。この調子を続けましょう。",
        ):
            advice = weekly_report.generate_ai_advice(statistics, user_data)

            assert len(advice) <= 300
            assert "進捗" in advice or "調子" in advice

    def test_generate_ai_advice_fallback(self):
        """AIアドバイス生成の失敗時フォールバック"""
        import weekly_report

        statistics = {
            "avg_daily_calories": 1500,
            "goal_achieved_days": 6,
            "meal_count": 7,
        }
        user_data = {"tdee": 2000}

        with patch.object(weekly_report.bedrock, "generate_advice", side_effect=Exception("API Error")):
            advice = weekly_report.generate_ai_advice(statistics, user_data)

            # フォールバック応答が返される
            assert len(advice) > 0
            assert isinstance(advice, str)

    def test_distribute_weekly_report_success(self):
        """週次レポート配信の成功ケース"""
        import weekly_report

        user_id = "test-user-1"
        user_data = {
            "user_id": user_id,
            "line_user_id": "line-user-123",
            "name": "テストユーザー",
        }
        statistics = {
            "avg_daily_calories": 2000,
            "goal_achieved_days": 6,
            "meal_count": 7,
        }
        advice = "良い進捗です。"

        with patch.object(weekly_report.line, "push_weekly_report", return_value=True):
            success = weekly_report.distribute_weekly_report(user_id, user_data, statistics, advice)

            assert success is True

    def test_distribute_weekly_report_no_line_id(self):
        """LINE User IDがない場合の配信"""
        import weekly_report

        user_id = "test-user-1"
        user_data = {
            "user_id": user_id,
            "line_user_id": None,  # LINE User IDがない
            "name": "テストユーザー",
        }
        statistics = {"avg_daily_calories": 2000}
        advice = "アドバイス"

        success = weekly_report.distribute_weekly_report(user_id, user_data, statistics, advice)

        assert success is False


class TestBedrockHelper:
    """BedrockHelper のテストクラス"""

    def test_bedrock_helper_initialization(self):
        """BedrockHelper の初期化"""
        helper = BedrockHelper(region_name="ap-northeast-1")

        assert helper.region_name == "ap-northeast-1"
        assert "claude" in helper.model_id.lower()

    def test_prompt_building(self):
        """プロンプト構築テスト"""
        helper = BedrockHelper()

        statistics = {
            "avg_daily_calories": 2000,
            "avg_daily_protein": 50,
            "goal_achieved_days": 5,
            "meal_count": 7,
            "daily_summaries": []
        }
        user_data = {"tdee": 2000}

        prompt = helper._build_advice_prompt(statistics, user_data, 300)

        assert "2000" in prompt  # TDEE値
        assert "5" in prompt  # 目標達成日数
        assert "300" in prompt  # 文字数制限


class TestLINEHelper:
    """LINEHelper のテストクラス"""

    def test_line_helper_initialization(self):
        """LINEHelper の初期化"""
        helper = LINEHelper(channel_access_token="test-token-123")

        assert helper.channel_access_token == "test-token-123"
        assert "line.me" in helper.PUSH_MESSAGE_URL

    @patch("requests.post")
    def test_push_message_success(self, mock_post):
        """メッセージ送信の成功"""
        mock_post.return_value = Mock(status_code=200)

        helper = LINEHelper(channel_access_token="test-token")
        success = helper.push_message(user_id="U123", text="テストメッセージ")

        assert success is True
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_push_message_failure(self, mock_post):
        """メッセージ送信の失敗"""
        mock_post.return_value = Mock(
            status_code=401,
            text="Unauthorized"
        )

        helper = LINEHelper(channel_access_token="test-token")

        with pytest.raises(Exception):  # ExternalServiceError
            helper.push_message(user_id="U123", text="テストメッセージ")

    def test_push_weekly_report_format(self):
        """週次レポートメッセージフォーマット"""
        helper = LINEHelper(channel_access_token="test-token")

        statistics = {
            "avg_daily_calories": 2000,
            "goal_achieved_days": 5,
        }

        with patch.object(helper, "push_message", return_value=True) as mock_push:
            helper.push_weekly_report(
                user_id="U123",
                user_name="テストユーザー",
                statistics=statistics,
                advice="良い進捗です。",
            )

            mock_push.assert_called_once()
            # push_message は user_id, text, quick_reply_items=None で呼ばれる
            call_args, call_kwargs = mock_push.call_args

            # 位置引数の確認
            if len(call_args) > 1:
                message = call_args[1]  # 2番目の位置引数
            else:
                message = call_kwargs.get("text", "")

            assert "2000" in message  # カロリー
            assert "5" in message  # 目標達成日数
            assert "良い進捗です。" in message  # アドバイス


class TestWeeklyReportIntegration:
    """統合テスト"""

    def test_lambda_handler_structure(self):
        """Lambda ハンドラーの構造確認"""
        import weekly_report

        # ハンドラーが存在し、呼び出し可能であることを確認
        assert callable(weekly_report.lambda_handler)

    @patch("weekly_report.get_active_users")
    @patch("weekly_report.calculate_weekly_statistics")
    @patch("weekly_report.generate_ai_advice")
    @patch("weekly_report.distribute_weekly_report")
    def test_lambda_handler_flow(
        self,
        mock_distribute,
        mock_generate,
        mock_calculate,
        mock_get_users,
    ):
        """Lambda ハンドラーの実行フロー"""
        import weekly_report

        # モック設定
        mock_get_users.return_value = [
            {
                "user_id": "user-1",
                "line_user_id": "line-123",
                "tdee": 2000,
                "name": "ユーザー1",
            }
        ]
        mock_calculate.return_value = {
            "avg_daily_calories": 2000,
            "goal_achieved_days": 5,
            "meal_count": 7,
        }
        mock_generate.return_value = "アドバイス"
        mock_distribute.return_value = True

        # ハンドラーを実行
        response = weekly_report.lambda_handler({}, {})

        # レスポンス構造を確認
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "user_count" in body
        assert "success_count" in body
        assert "timestamp" in body


# プロパティベーステスト
@pytest.mark.property
class TestWeeklyReportProperties:
    """週次レポート機能のプロパティテスト"""

    def test_property_statistics_accuracy(self, setup_dynamodb):
        """
        Feature: weekly-report, Property: 週次統計の精度

        7日間の食事記録から計算された統計が正確であること
        """
        import weekly_report

        user_id = "test-user"
        meals_table = setup_dynamodb["meals"]
        now = datetime.utcnow()

        # 7日分の食事記録を作成
        daily_calories = []
        for i in range(7):
            date = now - timedelta(days=i)
            calories = 2000 + (i * 100)  # 各日異なるカロリー
            daily_calories.append(calories)

            meals_table.put_item(
                Item={
                    "meal_id": f"meal-{i}",
                    "user_id": user_id,
                    "timestamp": date.isoformat(),
                    "total_calories": calories,
                    "total_protein": 50,
                    "total_fat": 70,
                    "total_carbs": 250,
                }
            )

        user_data = {"user_id": user_id, "tdee": 2000}
        stats = weekly_report.calculate_weekly_statistics(user_id, user_data)

        # 平均の検証
        expected_avg = sum(daily_calories) / len(daily_calories)
        assert stats["avg_daily_calories"] == pytest.approx(expected_avg, rel=0.01)

    def test_property_fallback_availability(self):
        """
        Feature: weekly-report, Property: フォールバック可用性

        Bedrock呼び出し失敗時、フォールバック応答が常に返されること
        """
        import weekly_report

        statistics = {
            "avg_daily_calories": 1500,
            "goal_achieved_days": 2,
            "meal_count": 5,
        }
        user_data = {"tdee": 2000}

        with patch.object(
            weekly_report.bedrock,
            "generate_advice",
            side_effect=Exception("Bedrock API Error"),
        ):
            advice = weekly_report.generate_ai_advice(statistics, user_data)

            # フォールバック応答が返される
            assert len(advice) > 0
            assert isinstance(advice, str)
            # 目標達成日数に応じた適切なアドバイスが返される
            assert advice in [
                "素晴らしい一週間でした！目標の達成日数が多いです。この調子を続けましょう。",
                "良い進捗です。目標に向けてバランスの取れた食事を心がけましょう。",
                "今週の記録をベースに、来週はさらに目標に近づけるよう頑張りましょう。",
            ]
