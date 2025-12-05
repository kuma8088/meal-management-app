"""
食事登録Lambda関数

要件: 1.3, 6.1, 6.2, 6.3, 6.4, 6.5
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

# 共通ライブラリをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

from common import (
    DynamoDBHelper,
    Meal,
    MealFood,
    Food,
    MealType,
    NutritionCalculator,
    ValidationError,
    ResourceNotFoundError,
    get_logger,
    success_response,
    error_response
)

logger = get_logger(__name__)

# 環境変数
MEALS_TABLE_NAME = os.environ.get("MEALS_TABLE_NAME", "Meals")
FOODS_TABLE_NAME = os.environ.get("FOODS_TABLE_NAME", "Foods")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# DynamoDB Helper
meals_db = DynamoDBHelper(MEALS_TABLE_NAME, AWS_REGION)
foods_db = DynamoDBHelper(FOODS_TABLE_NAME, AWS_REGION)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    API Gatewayからのリクエストを処理する

    Args:
        event: API Gatewayイベント
        context: Lambda実行コンテキスト

    Returns:
        API Gatewayレスポンス
    """
    try:
        # リクエストメソッドとパスを取得
        http_method = event.get("httpMethod", "")
        path = event.get("path", "")
        path_parameters = event.get("pathParameters") or {}

        logger.info(
            f"リクエスト受信: {http_method} {path}",
            extra={
                "extra_data": {
                    "method": http_method,
                    "path": path,
                    "path_parameters": path_parameters
                }
            }
        )

        # ルーティング
        if http_method == "POST" and path == "/meals":
            return create_meal(event)
        elif http_method == "GET" and path == "/meals":
            return list_meals(event)
        elif http_method == "GET" and "meal_id" in path_parameters:
            return get_meal(event)
        elif http_method == "PUT" and "meal_id" in path_parameters:
            return update_meal(event)
        elif http_method == "DELETE" and "meal_id" in path_parameters:
            return delete_meal(event)
        else:
            return error_response(
                "Not Found",
                404,
                details={"method": http_method, "path": path}
            )

    except ValidationError as e:
        logger.warning(f"バリデーションエラー: {e.message}", extra={"extra_data": e.details})
        return error_response(e)
    except ResourceNotFoundError as e:
        logger.warning(f"リソースが見つかりません: {e.message}", extra={"extra_data": e.details})
        return error_response(e)
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}", exc_info=True)
        return error_response(e)


def create_meal(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    食事記録を作成する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 6.1, 6.3
    プロパティ: 2, 10, 11, 12
    """
    # リクエストボディを解析
    body = json.loads(event.get("body", "{}"))

    # 必須フィールドのバリデーション
    user_id = body.get("user_id")
    if not user_id:
        raise ValidationError("user_idは必須です", details={"field": "user_id"})

    foods_data = body.get("foods")
    if not foods_data:
        raise ValidationError("foodsは必須です", details={"field": "foods"})

    meal_type = body.get("meal_type")
    if not meal_type:
        raise ValidationError("meal_typeは必須です", details={"field": "meal_type"})

    # タイムスタンプ（オプション、デフォルトは現在時刻）
    timestamp_str = body.get("timestamp")
    if timestamp_str:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    else:
        timestamp = datetime.utcnow()

    # MealFoodオブジェクトを作成
    meal_foods = [MealFood.from_dict(f) for f in foods_data]

    # 食品データベースから食品情報を取得
    food_database = {}
    for meal_food in meal_foods:
        food_item = foods_db.get_item({"food_id": meal_food.food_id})
        if not food_item:
            raise ResourceNotFoundError(
                f"食品ID {meal_food.food_id} が見つかりません",
                details={"food_id": meal_food.food_id}
            )
        food_database[meal_food.food_id] = Food.from_dict(food_item)

    # 栄養情報を自動計算（Property 11: 栄養情報の自動計算）
    nutrition = NutritionCalculator.calculate_meal_nutrition(meal_foods, food_database)

    # Mealオブジェクトを作成（Property 2: ユーザーIDとの関連付け）
    meal_id = str(uuid.uuid4())
    meal = Meal(
        meal_id=meal_id,
        user_id=user_id,
        meal_type=MealType(meal_type),
        foods=meal_foods,
        total_calories=nutrition["total_calories"],
        total_protein=nutrition["total_protein"],
        total_fat=nutrition["total_fat"],
        total_carbs=nutrition["total_carbs"],
        timestamp=timestamp,
        created_at=datetime.utcnow()
    )

    # DynamoDBに保存（Property 10: 食事記録の保存）
    # Mealsテーブル構造: PK: meal_id, SK: user_id#timestamp
    meal_data = meal.to_dict()
    meal_data["sk"] = f"{user_id}#{timestamp.isoformat()}"  # Sort Key for querying by user

    meals_db.put_item(meal_data)

    logger.info(
        f"食事記録を作成しました: {meal_id}",
        extra={
            "extra_data": {
                "meal_id": meal_id,
                "user_id": user_id,
                "total_calories": nutrition["total_calories"]
            }
        }
    )

    # レスポンスを作成
    return success_response({
        "meal_id": meal_id,
        "total_calories": nutrition["total_calories"],
        "total_protein": nutrition["total_protein"],
        "total_fat": nutrition["total_fat"],
        "total_carbs": nutrition["total_carbs"],
        "created_at": meal.created_at.isoformat()
    }, status_code=201)


def list_meals(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザーの食事記録リストを取得する（期間フィルタリング、ページネーション対応）

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 6.2, 12.3
    プロパティ: 1 (ユーザーデータ分離), 25 (期間フィルタリング)
    """
    # クエリパラメータを取得
    query_params = event.get("queryStringParameters") or {}
    user_id = query_params.get("user_id")

    if not user_id:
        raise ValidationError("user_idは必須です", details={"field": "user_id"})

    # オプション: 開始日と終了日（ISO 8601フォーマット）
    start_date = query_params.get("start_date")
    end_date = query_params.get("end_date")

    # ページネーション用パラメータ
    limit = int(query_params.get("limit", 100))
    next_token = query_params.get("next_token")

    # GSI1でユーザーIDで検索
    # GSI1: PK: user_id, SK: timestamp
    # DynamoDBのquery操作を使用してユーザーの食事記録を取得

    # KeyConditionExpressionの構築
    key_condition = "user_id = :user_id"
    expression_values = {":user_id": user_id}

    # 期間フィルタリング（Property 25）
    if start_date and end_date:
        key_condition += " AND #ts BETWEEN :start_date AND :end_date"
        expression_values[":start_date"] = start_date
        expression_values[":end_date"] = end_date
    elif start_date:
        key_condition += " AND #ts >= :start_date"
        expression_values[":start_date"] = start_date
    elif end_date:
        key_condition += " AND #ts <= :end_date"
        expression_values[":end_date"] = end_date

    # クエリパラメータの準備
    query_params_dict = {
        "IndexName": "GSI1",
        "KeyConditionExpression": key_condition,
        "ExpressionAttributeNames": {"#ts": "timestamp"},
        "ExpressionAttributeValues": expression_values,
        "Limit": limit,
        "ScanIndexForward": False  # 降順（最新が先）
    }

    # ページネーション: ExclusiveStartKeyの追加
    if next_token:
        import json
        import base64
        try:
            exclusive_start_key = json.loads(base64.b64decode(next_token).decode())
            query_params_dict["ExclusiveStartKey"] = exclusive_start_key
        except Exception as e:
            logger.warning(f"Invalid next_token: {str(e)}")
            raise ValidationError("next_tokenが無効です", details={"next_token": next_token})

    # DynamoDB query実行
    response = meals_db.table.query(**query_params_dict)

    items = response.get("Items", [])
    last_evaluated_key = response.get("LastEvaluatedKey")

    # Property 1: ユーザーデータ分離の検証
    # すべての返される記録がリクエストしたuser_idと関連付けられていることを確認
    meals = []
    for item in items:
        if item.get("user_id") == user_id:  # 二重チェック
            meals.append(item)

    logger.info(
        f"食事記録リストを取得しました: {len(meals)}件",
        extra={
            "extra_data": {
                "user_id": user_id,
                "count": len(meals),
                "has_more": bool(last_evaluated_key)
            }
        }
    )

    # レスポンスの作成
    response_data = {
        "meals": meals,
        "count": len(meals)
    }

    # ページネーション: next_tokenの生成
    if last_evaluated_key:
        import json
        import base64
        next_token_value = base64.b64encode(json.dumps(last_evaluated_key).encode()).decode()
        response_data["next_token"] = next_token_value
        response_data["has_more"] = True
    else:
        response_data["has_more"] = False

    return success_response(response_data)


def get_meal(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    特定の食事記録を取得する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 6.2
    プロパティ: 1 (ユーザーデータ分離)
    """
    # パスパラメータからmeal_idを取得
    path_parameters = event.get("pathParameters") or {}
    meal_id = path_parameters.get("meal_id")

    if not meal_id:
        raise ValidationError("meal_idは必須です", details={"field": "meal_id"})

    # クエリパラメータからuser_idを取得（認証用）
    query_params = event.get("queryStringParameters") or {}
    user_id = query_params.get("user_id")

    # DynamoDBから食事記録を取得
    meal_data = meals_db.get_item({"meal_id": meal_id})

    if not meal_data:
        raise ResourceNotFoundError(
            f"食事記録 {meal_id} が見つかりません",
            details={"meal_id": meal_id}
        )

    # Property 1: ユーザーデータ分離の検証
    # リクエストしたユーザーの記録のみを返す
    if user_id and meal_data.get("user_id") != user_id:
        raise ResourceNotFoundError(
            "食事記録が見つかりません",
            details={"meal_id": meal_id}
        )

    logger.info(
        f"食事記録を取得しました: {meal_id}",
        extra={
            "extra_data": {
                "meal_id": meal_id,
                "user_id": meal_data.get("user_id")
            }
        }
    )

    return success_response(meal_data)


def update_meal(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    食事記録を更新する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 6.4
    """
    # パスパラメータからmeal_idを取得
    path_parameters = event.get("pathParameters") or {}
    meal_id = path_parameters.get("meal_id")

    if not meal_id:
        raise ValidationError("meal_idは必須です", details={"field": "meal_id"})

    # リクエストボディを解析
    body = json.loads(event.get("body", "{}"))

    # 既存の食事記録を取得
    existing_meal_data = meals_db.get_item({"meal_id": meal_id})

    if not existing_meal_data:
        raise ResourceNotFoundError(
            f"食事記録 {meal_id} が見つかりません",
            details={"meal_id": meal_id}
        )

    # Property 1: ユーザーデータ分離の検証
    user_id = body.get("user_id")
    if user_id and existing_meal_data.get("user_id") != user_id:
        raise ResourceNotFoundError(
            "食事記録が見つかりません",
            details={"meal_id": meal_id}
        )

    # 更新可能なフィールド
    foods_data = body.get("foods")
    meal_type = body.get("meal_type")
    timestamp_str = body.get("timestamp")

    # 既存のデータをベースに更新
    updated_data = existing_meal_data.copy()

    # 食品リストが更新された場合、栄養情報を再計算
    if foods_data:
        # MealFoodオブジェクトを作成
        meal_foods = [MealFood.from_dict(f) for f in foods_data]

        # 食品データベースから食品情報を取得
        food_database = {}
        for meal_food in meal_foods:
            food_item = foods_db.get_item({"food_id": meal_food.food_id})
            if not food_item:
                raise ResourceNotFoundError(
                    f"食品ID {meal_food.food_id} が見つかりません",
                    details={"food_id": meal_food.food_id}
                )
            food_database[meal_food.food_id] = Food.from_dict(food_item)

        # 栄養情報を再計算
        nutrition = NutritionCalculator.calculate_meal_nutrition(meal_foods, food_database)

        # データを更新
        updated_data["foods"] = [f.to_dict() for f in meal_foods]
        updated_data["total_calories"] = nutrition["total_calories"]
        updated_data["total_protein"] = nutrition["total_protein"]
        updated_data["total_fat"] = nutrition["total_fat"]
        updated_data["total_carbs"] = nutrition["total_carbs"]

    if meal_type:
        updated_data["meal_type"] = meal_type

    if timestamp_str:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        updated_data["timestamp"] = timestamp.isoformat()
        # SKも更新
        updated_data["sk"] = f"{existing_meal_data['user_id']}#{timestamp.isoformat()}"

    # DynamoDBを更新
    meals_db.put_item(updated_data)

    logger.info(
        f"食事記録を更新しました: {meal_id}",
        extra={
            "extra_data": {
                "meal_id": meal_id,
                "user_id": existing_meal_data.get("user_id")
            }
        }
    )

    return success_response(updated_data)


def delete_meal(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    食事記録を削除する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 6.5
    """
    # パスパラメータからmeal_idを取得
    path_parameters = event.get("pathParameters") or {}
    meal_id = path_parameters.get("meal_id")

    if not meal_id:
        raise ValidationError("meal_idは必須です", details={"field": "meal_id"})

    # クエリパラメータからuser_idを取得（認証用）
    query_params = event.get("queryStringParameters") or {}
    user_id = query_params.get("user_id")

    # 既存の食事記録を取得
    existing_meal_data = meals_db.get_item({"meal_id": meal_id})

    if not existing_meal_data:
        raise ResourceNotFoundError(
            f"食事記録 {meal_id} が見つかりません",
            details={"meal_id": meal_id}
        )

    # Property 1: ユーザーデータ分離の検証
    if user_id and existing_meal_data.get("user_id") != user_id:
        raise ResourceNotFoundError(
            "食事記録が見つかりません",
            details={"meal_id": meal_id}
        )

    # DynamoDBから削除
    meals_db.delete_item({"meal_id": meal_id})

    logger.info(
        f"食事記録を削除しました: {meal_id}",
        extra={
            "extra_data": {
                "meal_id": meal_id,
                "user_id": existing_meal_data.get("user_id")
            }
        }
    )

    return success_response({
        "message": "食事記録を削除しました",
        "meal_id": meal_id
    })
