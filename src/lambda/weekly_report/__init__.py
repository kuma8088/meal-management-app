"""
週次レポート生成Lambda関数

毎週日曜20:00 JST に実行され、ユーザーの週次統計とAIアドバイスをLINEで配信する。
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

# 共通ライブラリをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

from common import (
    DynamoDBHelper,
    get_logger,
)
from common.bedrock_helper import BedrockHelper
from common.line_helper import LINEHelper

logger = get_logger(__name__)

# 環境変数
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "Users")
MEALS_TABLE_NAME = os.environ.get("MEALS_TABLE_NAME", "Meals")
AWS_REGION = "ap-northeast-1"  # Lambda環境で自動設定される
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# DynamoDB Helper
users_db = DynamoDBHelper(USERS_TABLE_NAME, AWS_REGION)
meals_db = DynamoDBHelper(MEALS_TABLE_NAME, AWS_REGION)

# Bedrock Helper
bedrock = BedrockHelper(region_name=AWS_REGION)

# LINE Helper
line = LINEHelper(channel_access_token=LINE_CHANNEL_ACCESS_TOKEN)


def get_active_users() -> List[Dict[str, Any]]:
    """
    週次レポートが有効になっているユーザーを取得する

    Returns:
        weekly_report_enabled=true のユーザーリスト

    プロパティ: 1 (ユーザーデータ分離)
    """
    # DynamoDBから全ユーザーを取得し、weekly_report_enabled=true でフィルタリング
    try:
        users = users_db.scan(
            filter_expression="attribute_exists(weekly_report_enabled) AND weekly_report_enabled = :enabled",
            expression_attribute_values={":enabled": True}
        )

        logger.info(
            f"アクティブユーザーを取得しました: {len(users)}名",
            extra={"extra_data": {"user_count": len(users)}}
        )

        return users
    except Exception as e:
        logger.error(f"ユーザー取得に失敗しました: {str(e)}", exc_info=True)
        raise


def distribute_weekly_report(
    user_id: str,
    user_data: Dict[str, Any],
    statistics: Dict[str, Any],
    advice: str
) -> bool:
    """
    ユーザーに週次レポートをLINE Push Messageで配信

    Args:
        user_id: ユーザーID
        user_data: ユーザーデータ
        statistics: 週次統計
        advice: AIアドバイス

    Returns:
        配信成功時True
    """
    try:
        line_user_id = user_data.get("line_user_id")
        user_name = user_data.get("name")

        if not line_user_id:
            logger.warning(
                f"ユーザー {user_id} の LINE User ID が設定されていません",
                extra={"extra_data": {"user_id": user_id}}
            )
            return False

        # LINE Push Message を送信
        success = line.push_weekly_report(
            user_id=line_user_id,
            user_name=user_name,
            statistics=statistics,
            advice=advice
        )

        return success

    except Exception as e:
        logger.error(
            f"週次レポート配信に失敗しました: {str(e)}",
            exc_info=True,
            extra={"extra_data": {"user_id": user_id}}
        )
        return False


def generate_ai_advice(
    statistics: Dict[str, Any],
    user_data: Dict[str, Any]
) -> str:
    """
    BedrockのClaude 3を使用してAIアドバイスを生成する

    Args:
        statistics: 週次統計辞書
        user_data: ユーザーデータ

    Returns:
        生成されたアドバイス（300文字以内）

    プロパティ: なし（アドオン機能）
    """
    try:
        advice = bedrock.generate_advice(statistics, user_data, max_chars=300)
        return advice
    except Exception as e:
        logger.error(
            f"AIアドバイス生成に失敗しました: {str(e)}",
            exc_info=True,
            extra={"extra_data": {"error_type": type(e).__name__}}
        )
        # フォールバック: 事前定義されたアドバイスを返す
        goal_achieved_days = statistics.get("goal_achieved_days", 0)
        if goal_achieved_days >= 5:
            return "素晴らしい一週間でした！目標の達成日数が多いです。この調子を続けましょう。"
        elif goal_achieved_days >= 3:
            return "良い進捗です。目標に向けてバランスの取れた食事を心がけましょう。"
        else:
            return "今週の記録をベースに、来週はさらに目標に近づけるよう頑張りましょう。"


def calculate_weekly_statistics(user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザーの過去7日間の食事データを集計し、週次統計を計算する

    Args:
        user_id: ユーザーID
        user_data: ユーザーデータ（TDEE等を含む）

    Returns:
        週次統計辞書：
        - avg_daily_calories: 平均日次カロリー
        - avg_daily_protein: 平均日次タンパク質
        - avg_daily_fat: 平均日次脂肪
        - avg_daily_carbs: 平均日次炭水化物
        - goal_achieved_days: 目標達成日数（カロリー）
        - meal_count: 食事記録数

    プロパティ: 12 (複数食品の栄養情報合計), 25 (期間フィルタリング)
    """
    try:
        # 過去7日間の開始日時と終了日時を計算
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # ISO 8601フォーマット（文字列）で時間範囲を指定
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        # ユーザーの食事記録を GSI1で クエリ
        key_condition = "user_id = :user_id AND #ts BETWEEN :start AND :end"
        expression_values = {
            ":user_id": user_id,
            ":start": start_iso,
            ":end": end_iso
        }

        # DynamoDB query 操作
        meals = meals_db.table.query(
            IndexName="GSI1",
            KeyConditionExpression=key_condition,
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues=expression_values,
            ScanIndexForward=False
        ).get("Items", [])

        if not meals:
            logger.warning(
                f"ユーザー {user_id} の過去7日間の食事記録がありません",
                extra={"extra_data": {"user_id": user_id}}
            )
            return {
                "avg_daily_calories": 0,
                "avg_daily_protein": 0,
                "avg_daily_fat": 0,
                "avg_daily_carbs": 0,
                "goal_achieved_days": 0,
                "meal_count": 0,
                "daily_summaries": []
            }

        # 日単位で食事データを集計
        daily_aggregates = {}  # {date: {calories, protein, fat, carbs}}

        for meal in meals:
            # タイムスタンプから日付を抽出
            timestamp_str = meal.get("timestamp", "")
            if isinstance(timestamp_str, str):
                date = timestamp_str.split("T")[0]
            else:
                continue

            if date not in daily_aggregates:
                daily_aggregates[date] = {
                    "calories": 0,
                    "protein": 0,
                    "fat": 0,
                    "carbs": 0
                }

            # 栄養情報を集計
            daily_aggregates[date]["calories"] += meal.get("total_calories", 0)
            daily_aggregates[date]["protein"] += meal.get("total_protein", 0)
            daily_aggregates[date]["fat"] += meal.get("total_fat", 0)
            daily_aggregates[date]["carbs"] += meal.get("total_carbs", 0)

        # 統計を計算
        total_calories = sum(d["calories"] for d in daily_aggregates.values())
        total_protein = sum(d["protein"] for d in daily_aggregates.values())
        total_fat = sum(d["fat"] for d in daily_aggregates.values())
        total_carbs = sum(d["carbs"] for d in daily_aggregates.values())

        daily_count = len(daily_aggregates)
        avg_daily_calories = total_calories / daily_count if daily_count > 0 else 0
        avg_daily_protein = total_protein / daily_count if daily_count > 0 else 0
        avg_daily_fat = total_fat / daily_count if daily_count > 0 else 0
        avg_daily_carbs = total_carbs / daily_count if daily_count > 0 else 0

        # 目標達成日数（カロリー）: TDEE ± 10% の範囲
        tdee = user_data.get("tdee", 2000)
        lower_bound = tdee * 0.9
        upper_bound = tdee * 1.1

        goal_achieved_days = sum(
            1 for daily in daily_aggregates.values()
            if lower_bound <= daily["calories"] <= upper_bound
        )

        logger.info(
            f"ユーザー {user_id} の週次統計を計算しました",
            extra={
                "extra_data": {
                    "user_id": user_id,
                    "daily_count": daily_count,
                    "avg_daily_calories": round(avg_daily_calories, 2),
                    "goal_achieved_days": goal_achieved_days
                }
            }
        )

        return {
            "avg_daily_calories": round(avg_daily_calories, 2),
            "avg_daily_protein": round(avg_daily_protein, 2),
            "avg_daily_fat": round(avg_daily_fat, 2),
            "avg_daily_carbs": round(avg_daily_carbs, 2),
            "goal_achieved_days": goal_achieved_days,
            "meal_count": len(meals),
            "daily_summaries": [
                {
                    "date": date,
                    "calories": round(daily["calories"], 2),
                    "protein": round(daily["protein"], 2),
                    "fat": round(daily["fat"], 2),
                    "carbs": round(daily["carbs"], 2)
                }
                for date, daily in sorted(daily_aggregates.items(), reverse=True)
            ]
        }

    except Exception as e:
        logger.error(
            f"週次統計の計算に失敗しました: {str(e)}",
            exc_info=True,
            extra={"extra_data": {"user_id": user_id}}
        )
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    EventBridgeスケジューラーから実行されるハンドラー

    Args:
        event: EventBridgeイベント
        context: Lambda実行コンテキスト

    Returns:
        実行結果
    """
    try:
        logger.info(
            "週次レポート生成を開始しました",
            extra={"extra_data": {"timestamp": datetime.utcnow().isoformat()}}
        )

        # ステップ1: アクティブユーザーを取得（Task 1.2）
        active_users = get_active_users()

        # ステップ2: 各ユーザーの週次統計を集計（Task 1.3）
        # ステップ3: Bedrockでアドバイス生成（Task 1.4）
        # ステップ4: LINEで配信（Task 1.5）
        distribution_results = []
        for user in active_users:
            user_id = user.get("user_id")
            try:
                # 統計を計算
                stats = calculate_weekly_statistics(user_id, user)

                # AIアドバイスを生成
                advice = generate_ai_advice(stats, user)

                # LINEで配信
                success = distribute_weekly_report(user_id, user, stats, advice)

                distribution_results.append({
                    "user_id": user_id,
                    "success": success,
                    "avg_calories": stats.get("avg_daily_calories", 0)
                })

                logger.info(
                    f"ユーザー {user_id} への配信完了",
                    extra={
                        "extra_data": {
                            "user_id": user_id,
                            "success": success
                        }
                    }
                )

            except Exception as e:
                logger.warning(
                    f"ユーザー {user_id} の週次レポート処理に失敗しました: {str(e)}",
                    exc_info=True
                )
                distribution_results.append({
                    "user_id": user_id,
                    "success": False,
                    "error": str(e)
                })

        # 成功数をカウント
        success_count = sum(1 for r in distribution_results if r.get("success"))

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Weekly report generation completed",
                "user_count": len(active_users),
                "success_count": success_count,
                "failure_count": len(active_users) - success_count,
                "timestamp": datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Weekly report generation failed",
                "message": str(e)
            })
        }
