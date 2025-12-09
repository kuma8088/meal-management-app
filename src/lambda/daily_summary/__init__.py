"""
1日の総評とAIアドバイス生成Lambda関数

要件: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9
プロパティ: 20, 21, 22
"""
import json
import os
from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import sys
from pathlib import Path

# AWS SDK
import boto3
from botocore.exceptions import ClientError

# 共通ライブラリをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

from common import (
    DynamoDBHelper,
    ValidationError,
    ResourceNotFoundError,
    validate_required,
    validate_date_format,
    get_logger,
    success_response,
    error_response
)

logger = get_logger(__name__)

# 環境変数
MEALS_TABLE_NAME = os.environ.get("MEALS_TABLE_NAME", "Meals")
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "Users")
GOALS_TABLE_NAME = os.environ.get("GOALS_TABLE_NAME", "Goals")
ADVICE_USAGE_TABLE_NAME = os.environ.get("ADVICE_USAGE_TABLE_NAME", "AdviceUsage")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# DynamoDB helpers
meals_db = DynamoDBHelper(MEALS_TABLE_NAME)
users_db = DynamoDBHelper(USERS_TABLE_NAME)
goals_db = DynamoDBHelper(GOALS_TABLE_NAME)
advice_usage_db = DynamoDBHelper(ADVICE_USAGE_TABLE_NAME)

# Bedrock client
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# 制限
MAX_ADVICE_PER_DAY = 2  # 要件: 10.2
MAX_ADVICE_LENGTH = 300  # 要件: 10.7
ADVICE_USAGE_TTL_DAYS = 30  # 要件: 10.9


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda関数のメインハンドラー

    Args:
        event: API Gatewayイベント
        context: Lambda context

    Returns:
        API Gatewayレスポンス

    要件: 10.1
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # HTTPメソッドとパスを取得
        http_method = event.get("httpMethod", "")
        path = event.get("path", "")

        # ルーティング
        if http_method == "POST" and path == "/advice/daily":
            return generate_daily_advice(event)
        else:
            return error_response(
                ValidationError(f"Unsupported route: {http_method} {path}")
            )

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return error_response(e)
    except ResourceNotFoundError as e:
        logger.warning(f"Resource not found: {e.message}")
        return error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return error_response(e)


def generate_daily_advice(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    1日の食事記録の総評とアドバイスを生成する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9
    プロパティ: 20, 21, 22
    """
    # リクエストボディを解析
    body = json.loads(event.get("body", "{}"))

    # バリデーション
    user_id = body.get("user_id")
    advice_date_str = body.get("date")

    validate_required(user_id, "user_id")
    validate_required(advice_date_str, "date")

    # 日付フォーマットのバリデーション
    validate_date_format(advice_date_str, "date")
    advice_date = date.fromisoformat(advice_date_str)

    # 要件: 10.2 - アドバイス生成回数の制限チェック (プロパティ: 20)
    usage_limit_reached, usage_count = check_usage_limit(user_id, advice_date)
    if usage_limit_reached:
        return success_response({
            "message": f"本日のアドバイス生成は{MAX_ADVICE_PER_DAY}回までです",
            "usage_count": usage_count,
            "usage_limit_reached": True,
            "max_usage": MAX_ADVICE_PER_DAY
        }, status_code=200)

    # 要件: 10.3, 10.4 - 1日の食事記録を集計 (プロパティ: 21)
    daily_summary = aggregate_daily_meals(user_id, advice_date)

    # 目標カロリーを取得 (要件: 10.5)
    target_calories = get_user_target_calories(user_id)

    # カロリー差を計算
    calorie_difference = daily_summary["total_calories"] - target_calories

    # 要件: 10.6 - Bedrock Claude APIでアドバイス生成
    advice = generate_advice_with_bedrock(
        user_id=user_id,
        daily_summary=daily_summary,
        target_calories=target_calories,
        calorie_difference=calorie_difference
    )

    # 要件: 10.7 - 300文字制限 (プロパティ: 22)
    advice = truncate_advice(advice, MAX_ADVICE_LENGTH)

    # 要件: 10.8, 10.9 - アドバイス生成回数をカウント
    increment_usage_count(user_id, advice_date)

    # レスポンスを作成
    response_data = {
        "user_id": user_id,
        "date": advice_date_str,
        "total_calories": daily_summary["total_calories"],
        "total_protein": daily_summary["total_protein"],
        "total_fat": daily_summary["total_fat"],
        "total_carbs": daily_summary["total_carbs"],
        "target_calories": target_calories,
        "calorie_difference": calorie_difference,
        "advice": advice,
        "usage_count": usage_count + 1,
        "usage_limit_reached": (usage_count + 1) >= MAX_ADVICE_PER_DAY
    }

    logger.info(f"Daily advice generated for user {user_id} on {advice_date_str}")

    return success_response(response_data, status_code=200)


def check_usage_limit(user_id: str, advice_date: date) -> tuple[bool, int]:
    """
    アドバイス生成の利用制限をチェックする

    Args:
        user_id: ユーザーID
        advice_date: アドバイス生成日

    Returns:
        (usage_limit_reached, usage_count): 制限に達したか、現在の利用回数

    要件: 10.2
    プロパティ: 20
    """
    user_id_date = f"{user_id}#{advice_date.isoformat()}"

    try:
        usage_item = advice_usage_db.get_item({"user_id_date": user_id_date})
        usage_count = int(usage_item.get("usage_count", 0))

        # 制限チェック
        if usage_count >= MAX_ADVICE_PER_DAY:
            return True, usage_count

        return False, usage_count

    except (ResourceNotFoundError, Exception):
        # まだ記録がない場合は0回として扱う
        return False, 0


def aggregate_daily_meals(user_id: str, advice_date: date) -> Dict[str, float]:
    """
    1日の食事記録を集計する

    Args:
        user_id: ユーザーID
        advice_date: 集計対象日

    Returns:
        集計結果の辞書 (total_calories, total_protein, total_fat, total_carbs)

    要件: 10.3, 10.4
    プロパティ: 21
    """
    # 指定日の0:00から23:59までのタイムスタンプ範囲を計算
    start_datetime = datetime.combine(advice_date, datetime.min.time())
    end_datetime = datetime.combine(advice_date, datetime.max.time())

    start_timestamp = start_datetime.isoformat()
    end_timestamp = end_datetime.isoformat()

    # UserIdTimestampIndex GSIでユーザーの食事記録をクエリ
    try:
        # DynamoDBのquery操作
        response = meals_db.table.query(
            IndexName="UserIdTimestampIndex",
            KeyConditionExpression="user_id = :user_id AND #ts BETWEEN :start AND :end",
            ExpressionAttributeNames={
                "#ts": "timestamp"
            },
            ExpressionAttributeValues={
                ":user_id": user_id,
                ":start": start_timestamp,
                ":end": end_timestamp
            }
        )

        meals = response.get("Items", [])
    except ClientError as e:
        logger.error(f"Error querying meals: {str(e)}")
        meals = []

    # 栄養情報を集計
    total_calories = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0

    for meal in meals:
        total_calories += float(meal.get("total_calories", 0))
        total_protein += float(meal.get("total_protein", 0))
        total_fat += float(meal.get("total_fat", 0))
        total_carbs += float(meal.get("total_carbs", 0))

    return {
        "total_calories": round(total_calories, 2),
        "total_protein": round(total_protein, 2),
        "total_fat": round(total_fat, 2),
        "total_carbs": round(total_carbs, 2)
    }


def get_user_target_calories(user_id: str) -> float:
    """
    ユーザーの目標カロリーを取得する

    Args:
        user_id: ユーザーID

    Returns:
        目標カロリー (kcal/日)

    要件: 10.5
    """
    try:
        # UserIdCreatedAtIndex GSIでユーザーの最新の目標を取得
        response = goals_db.table.query(
            IndexName="UserIdCreatedAtIndex",
            KeyConditionExpression="user_id = :user_id",
            ExpressionAttributeValues={
                ":user_id": user_id
            },
            ScanIndexForward=False,  # 降順 (最新が先)
            Limit=1
        )

        goals = response.get("Items", [])

        if goals:
            return float(goals[0].get("target_calories", 0))
        else:
            # 目標が設定されていない場合は、ユーザーのTDEEを返す
            user_data = users_db.get_item({"user_id": user_id})
            return float(user_data.get("tdee", 2000.0))

    except (ResourceNotFoundError, ClientError) as e:
        logger.warning(f"Could not get target calories for user {user_id}: {str(e)}")
        # デフォルト値として2000kcalを返す
        return 2000.0


def generate_advice_with_bedrock(
    user_id: str,
    daily_summary: Dict[str, float],
    target_calories: float,
    calorie_difference: float
) -> str:
    """
    Bedrock Claude APIでアドバイスを生成する

    Args:
        user_id: ユーザーID
        daily_summary: 1日の栄養集計
        target_calories: 目標カロリー
        calorie_difference: カロリー差 (実際 - 目標)

    Returns:
        生成されたアドバイス

    要件: 10.6
    """
    # プロンプトを作成
    prompt = f"""あなたは栄養管理の専門家です。以下の1日の食事記録に基づいて、簡潔なアドバイスを日本語で提供してください。

【1日の食事記録】
- 総カロリー: {daily_summary['total_calories']:.0f} kcal
- タンパク質: {daily_summary['total_protein']:.1f} g
- 脂質: {daily_summary['total_fat']:.1f} g
- 炭水化物: {daily_summary['total_carbs']:.1f} g

【目標カロリー】
- {target_calories:.0f} kcal

【カロリー差】
- {calorie_difference:+.0f} kcal ({'目標超過' if calorie_difference > 0 else '目標未達' if calorie_difference < 0 else '目標達成'})

以下の点に注意してアドバイスを作成してください:
1. 簡潔で具体的なアドバイスにする (300文字以内)
2. カロリーとPFCバランスの両方を考慮する
3. ポジティブで実践的な提案をする
4. 過度な制限は避け、健康的な改善を提案する

アドバイス:"""

    try:
        # Bedrock APIを呼び出し
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }

        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )

        # レスポンスを解析
        response_body = json.loads(response["body"].read())
        advice = response_body["content"][0]["text"].strip()

        logger.info(f"Bedrock advice generated for user {user_id}")

        return advice

    except Exception as e:
        logger.error(f"Error calling Bedrock API: {str(e)}", exc_info=True)

        # エラー時はフォールバックメッセージを返す
        if calorie_difference > 200:
            return "本日は目標カロリーを超過しています。明日は野菜を多めに取り入れ、油分を控えめにすることをおすすめします。"
        elif calorie_difference < -200:
            return "本日は目標カロリーに達していません。栄養バランスを保ちながら、適度に食事量を増やすことを検討してください。"
        else:
            return "本日のカロリー摂取は目標に近い良い結果です。この調子で栄養バランスにも注意を払いながら続けましょう。"


def truncate_advice(advice: str, max_length: int) -> str:
    """
    アドバイスを指定文字数に切り詰める

    Args:
        advice: アドバイス文字列
        max_length: 最大文字数

    Returns:
        切り詰められたアドバイス

    要件: 10.7
    プロパティ: 22
    """
    if len(advice) <= max_length:
        return advice

    # max_length文字で切り詰め、末尾に省略記号を追加
    truncated = advice[:max_length - 3] + "..."

    logger.info(f"Advice truncated from {len(advice)} to {len(truncated)} characters")

    return truncated


def increment_usage_count(user_id: str, advice_date: date) -> None:
    """
    アドバイス生成回数をカウントする

    Args:
        user_id: ユーザーID
        advice_date: アドバイス生成日

    要件: 10.8, 10.9
    """
    user_id_date = f"{user_id}#{advice_date.isoformat()}"

    # TTLを計算 (30日後)
    ttl_timestamp = int((datetime.now() + timedelta(days=ADVICE_USAGE_TTL_DAYS)).timestamp())

    try:
        # カウンターをインクリメント
        advice_usage_db.table.update_item(
            Key={"user_id_date": user_id_date},
            UpdateExpression="SET usage_count = if_not_exists(usage_count, :zero) + :inc, #ttl = :ttl, user_id = :user_id, #date = :date",
            ExpressionAttributeNames={
                "#ttl": "ttl",
                "#date": "date"
            },
            ExpressionAttributeValues={
                ":zero": 0,
                ":inc": 1,
                ":ttl": ttl_timestamp,
                ":user_id": user_id,
                ":date": advice_date.isoformat()
            }
        )

        logger.info(f"Usage count incremented for {user_id_date}")

    except ClientError as e:
        logger.error(f"Error incrementing usage count: {str(e)}")
        raise
