"""
体重目標管理Lambda関数

要件: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""
import json
import os
import uuid
from datetime import datetime, date
from typing import Dict, Any
import sys
from pathlib import Path

# 共通ライブラリをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

from common import (
    DynamoDBHelper,
    Goal,
    GoalType,
    GoalCalculator,
    BMRCalculator,
    ProfileManager,
    User,
    Gender,
    ActivityLevel,
    ValidationError,
    ResourceNotFoundError,
    get_logger,
    success_response,
    error_response,
    require_auth,
)

logger = get_logger(__name__)

# 環境変数
GOALS_TABLE_NAME = os.environ.get("GOALS_TABLE_NAME", "Goals")
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "Users")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# DynamoDB Helper
goals_db = DynamoDBHelper(GOALS_TABLE_NAME, AWS_REGION)
users_db = DynamoDBHelper(USERS_TABLE_NAME, AWS_REGION)


@require_auth
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    API Gatewayからのリクエストを処理する

    認証: Cognito トークンまたは LINE User ID が必要
    認証成功時、event["auth_user"] に認証ユーザー情報が追加される

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
        # ユーザープロフィール管理
        if http_method == "GET" and path == "/users/me":
            # 認証ユーザー自身のプロフィールを取得
            return get_current_user_profile(event)
        elif http_method == "POST" and path == "/users":
            return create_user_profile(event)
        elif http_method == "GET" and path_parameters.get("user_id") and "goals" not in path:
            return get_user_profile(event)
        elif http_method == "PUT" and path_parameters.get("user_id") and "goals" not in path:
            return update_user_profile(event)
        # 目標管理
        elif http_method == "POST" and path == "/goals":
            return create_goal(event)
        elif http_method == "GET" and path == "/goals":
            return list_goals(event)
        elif http_method == "GET" and "goal_id" in path_parameters:
            return get_goal(event)
        elif http_method == "GET" and "goals" in path:
            # GET /users/{user_id}/goals
            return list_user_goals(event)
        elif http_method == "PUT" and "goal_id" in path_parameters:
            return update_goal(event)
        else:
            return error_response(
                ValidationError(
                    "Not Found",
                    details={"method": http_method, "path": path}
                )
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


def create_goal(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    体重目標を作成する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    """
    # 認証ユーザーからuser_idを取得
    auth_user = event.get("auth_user", {})
    user_id = auth_user.get("user_id")
    if not user_id:
        raise ValidationError("認証が必要です", details={"field": "user_id"})

    # リクエストボディを解析
    body = json.loads(event.get("body", "{}"))

    target_weight = body.get("target_weight")
    if target_weight is None:
        raise ValidationError("target_weightは必須です", details={"field": "target_weight"})

    target_date_str = body.get("target_date")
    if not target_date_str:
        raise ValidationError("target_dateは必須です", details={"field": "target_date"})

    goal_type_str = body.get("goal_type")
    if not goal_type_str:
        raise ValidationError("goal_typeは必須です", details={"field": "goal_type"})

    # 日付の変換
    try:
        target_date = date.fromisoformat(target_date_str)
    except ValueError as e:
        raise ValidationError(
            "target_dateの形式が無効です（YYYY-MM-DD形式で指定してください）",
            details={"target_date": target_date_str, "error": str(e)}
        )

    # goal_typeの変換
    try:
        goal_type = GoalType(goal_type_str)
    except ValueError:
        raise ValidationError(
            f"無効なgoal_type: {goal_type_str}（gain, maintain, loseのいずれかを指定してください）",
            details={"goal_type": goal_type_str}
        )

    # ユーザー情報を取得してTDEEとcurrent_weightを取得
    user_data = users_db.get_item({"user_id": user_id})
    if not user_data:
        raise ResourceNotFoundError(
            f"ユーザーID {user_id} が見つかりません",
            details={"user_id": user_id}
        )

    # current_weightはオプション（指定がなければプロフィールから取得）
    current_weight = body.get("current_weight")
    if current_weight is None:
        current_weight = user_data.get("weight")
        if current_weight is None:
            raise ValidationError(
                "current_weightが指定されておらず、プロフィールにも体重が設定されていません",
                details={"user_id": user_id}
            )
        logger.info(f"current_weightをプロフィールから取得: {current_weight}kg")

    tdee = user_data.get("tdee", 0.0)
    if tdee <= 0:
        raise ValidationError(
            "ユーザーのTDEEが設定されていません。プロフィールを更新してください",
            details={"user_id": user_id, "tdee": tdee}
        )

    # 目標計算を実行
    goal_calculation = GoalCalculator.calculate_goal(
        current_weight=float(current_weight),
        target_weight=float(target_weight),
        target_date=target_date,
        tdee=float(tdee),
        goal_type=goal_type
    )

    # Goalオブジェクトを作成
    goal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    goal = Goal(
        goal_id=goal_id,
        user_id=user_id,
        current_weight=float(current_weight),
        target_weight=float(target_weight),
        target_date=target_date,
        goal_type=goal_type,
        daily_calorie_adjustment=goal_calculation["daily_calorie_adjustment"],
        target_calories=goal_calculation["target_calories"],
        recommended_protein=goal_calculation["recommended_protein"],
        recommended_fat=goal_calculation["recommended_fat"],
        recommended_carbs=goal_calculation["recommended_carbs"],
        recommended_exercise_minutes=goal_calculation["recommended_exercise_minutes"],
        created_at=now,
        updated_at=now
    )

    # DynamoDBに保存
    goals_db.put_item(goal.to_dict())

    logger.info(
        f"体重目標を作成しました: {goal_id}",
        extra={
            "extra_data": {
                "goal_id": goal_id,
                "user_id": user_id,
                "goal_type": goal_type.value,
                "target_calories": goal_calculation["target_calories"]
            }
        }
    )

    # レスポンスを作成
    response_data = {
        "goal_id": goal_id,
        "goal_type": goal_type.value,
        "current_weight": float(current_weight),
        "target_weight": float(target_weight),
        "target_date": target_date.isoformat(),
        "daily_calorie_adjustment": goal_calculation["daily_calorie_adjustment"],
        "target_calories": goal_calculation["target_calories"],
        "recommended_protein": goal_calculation["recommended_protein"],
        "recommended_fat": goal_calculation["recommended_fat"],
        "recommended_carbs": goal_calculation["recommended_carbs"],
        "recommended_exercise_minutes": goal_calculation["recommended_exercise_minutes"],
        "created_at": now.isoformat()
    }

    # 警告メッセージがある場合は追加
    if goal_calculation["warning"]:
        response_data["warning"] = goal_calculation["warning"]

    return success_response(response_data, status_code=201)


def list_goals(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザーの体重目標リストを取得する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 9.1
    """
    # クエリパラメータを取得
    query_params = event.get("queryStringParameters") or {}
    user_id = query_params.get("user_id")

    if not user_id:
        raise ValidationError("user_idは必須です", details={"field": "user_id"})

    limit = int(query_params.get("limit", 100))

    # スキャンでuser_idが一致するアイテムを取得
    filter_expression = "user_id = :user_id"
    expression_values = {":user_id": user_id}

    items = goals_db.scan(
        filter_expression=filter_expression,
        expression_attribute_values=expression_values,
        limit=limit
    )

    # ユーザーデータ分離の検証
    goals = []
    for item in items:
        if item.get("user_id") == user_id:  # 二重チェック
            goals.append(item)

    logger.info(
        f"体重目標リストを取得しました: {len(goals)}件",
        extra={
            "extra_data": {
                "user_id": user_id,
                "count": len(goals)
            }
        }
    )

    return success_response({
        "goals": goals,
        "count": len(goals)
    })


def get_goal(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    特定の体重目標を取得する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 9.1
    """
    # パスパラメータからgoal_idを取得
    path_parameters = event.get("pathParameters") or {}
    goal_id = path_parameters.get("goal_id")

    if not goal_id:
        raise ValidationError("goal_idは必須です", details={"field": "goal_id"})

    # クエリパラメータからuser_idを取得（認証用）
    query_params = event.get("queryStringParameters") or {}
    user_id = query_params.get("user_id")

    # DynamoDBから体重目標を取得
    goal_data = goals_db.get_item({"goal_id": goal_id})

    if not goal_data:
        raise ResourceNotFoundError(
            f"体重目標 {goal_id} が見つかりません",
            details={"goal_id": goal_id}
        )

    # ユーザーデータ分離の検証
    if user_id and goal_data.get("user_id") != user_id:
        raise ResourceNotFoundError(
            "体重目標が見つかりません",
            details={"goal_id": goal_id}
        )

    logger.info(
        f"体重目標を取得しました: {goal_id}",
        extra={
            "extra_data": {
                "goal_id": goal_id,
                "user_id": goal_data.get("user_id")
            }
        }
    )

    return success_response(goal_data)


def update_goal(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    体重目標を更新する

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス

    要件: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    """
    # パスパラメータからgoal_idを取得
    path_parameters = event.get("pathParameters") or {}
    goal_id = path_parameters.get("goal_id")

    if not goal_id:
        raise ValidationError("goal_idは必須です", details={"field": "goal_id"})

    # リクエストボディを解析
    body = json.loads(event.get("body", "{}"))

    # 既存の体重目標を取得
    existing_goal_data = goals_db.get_item({"goal_id": goal_id})

    if not existing_goal_data:
        raise ResourceNotFoundError(
            f"体重目標 {goal_id} が見つかりません",
            details={"goal_id": goal_id}
        )

    # ユーザーデータ分離の検証
    user_id = body.get("user_id")
    if user_id and existing_goal_data.get("user_id") != user_id:
        raise ResourceNotFoundError(
            "体重目標が見つかりません",
            details={"goal_id": goal_id}
        )

    # 更新可能なフィールド
    current_weight = body.get("current_weight")
    target_weight = body.get("target_weight")
    target_date_str = body.get("target_date")
    goal_type_str = body.get("goal_type")

    # 既存のデータをベースに更新
    updated_data = existing_goal_data.copy()
    updated_data["updated_at"] = datetime.utcnow().isoformat()

    # 更新があった場合は再計算
    recalculate = False

    if current_weight is not None:
        updated_data["current_weight"] = float(current_weight)
        recalculate = True

    if target_weight is not None:
        updated_data["target_weight"] = float(target_weight)
        recalculate = True

    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
            updated_data["target_date"] = target_date.isoformat()
            recalculate = True
        except ValueError as e:
            raise ValidationError(
                "target_dateの形式が無効です",
                details={"target_date": target_date_str, "error": str(e)}
            )

    if goal_type_str:
        try:
            goal_type = GoalType(goal_type_str)
            updated_data["goal_type"] = goal_type.value
            recalculate = True
        except ValueError:
            raise ValidationError(
                f"無効なgoal_type: {goal_type_str}",
                details={"goal_type": goal_type_str}
            )

    # 再計算が必要な場合
    if recalculate:
        # ユーザー情報を取得してTDEEを取得
        user_data = users_db.get_item({"user_id": existing_goal_data["user_id"]})
        if not user_data:
            raise ResourceNotFoundError(
                f"ユーザーID {existing_goal_data['user_id']} が見つかりません",
                details={"user_id": existing_goal_data["user_id"]}
            )

        tdee = user_data.get("tdee", 0.0)

        # 目標計算を実行
        goal_calculation = GoalCalculator.calculate_goal(
            current_weight=float(updated_data["current_weight"]),
            target_weight=float(updated_data["target_weight"]),
            target_date=date.fromisoformat(updated_data["target_date"]),
            tdee=float(tdee),
            goal_type=GoalType(updated_data["goal_type"])
        )

        # 計算結果を更新
        updated_data["daily_calorie_adjustment"] = goal_calculation["daily_calorie_adjustment"]
        updated_data["target_calories"] = goal_calculation["target_calories"]
        updated_data["recommended_protein"] = goal_calculation["recommended_protein"]
        updated_data["recommended_fat"] = goal_calculation["recommended_fat"]
        updated_data["recommended_carbs"] = goal_calculation["recommended_carbs"]
        updated_data["recommended_exercise_minutes"] = goal_calculation["recommended_exercise_minutes"]

        # 警告メッセージを追加
        if goal_calculation["warning"]:
            updated_data["warning"] = goal_calculation["warning"]

    # DynamoDBを更新
    goals_db.put_item(updated_data)

    logger.info(
        f"体重目標を更新しました: {goal_id}",
        extra={
            "extra_data": {
                "goal_id": goal_id,
                "user_id": existing_goal_data.get("user_id")
            }
        }
    )

    return success_response(updated_data)


def list_user_goals(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    特定ユーザーの体重目標リストを取得する (GET /users/{user_id}/goals)

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス
    """
    path_parameters = event.get("pathParameters") or {}
    user_id = path_parameters.get("user_id")

    if not user_id:
        raise ValidationError("user_idは必須です", details={"field": "user_id"})

    # スキャンでuser_idが一致するアイテムを取得
    filter_expression = "user_id = :user_id"
    expression_values = {":user_id": user_id}

    items = goals_db.scan(
        filter_expression=filter_expression,
        expression_attribute_values=expression_values,
        limit=100
    )

    # ユーザーデータ分離の検証
    goals = []
    for item in items:
        if item.get("user_id") == user_id:
            goals.append(item)

    logger.info(
        f"ユーザー{user_id}の体重目標リストを取得しました: {len(goals)}件",
        extra={"extra_data": {"user_id": user_id, "count": len(goals)}}
    )

    return success_response(goals)


def create_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザープロフィールを作成する (POST /users)

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス
    """
    # リクエストボディを解析
    body = json.loads(event.get("body", "{}"))

    # CognitoのユーザーIDを取得
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})
    cognito_user_id = claims.get("sub")

    # 必須フィールドのバリデーション
    age = body.get("age")
    if age is None:
        raise ValidationError("ageは必須です", details={"field": "age"})

    gender_str = body.get("gender")
    if not gender_str:
        raise ValidationError("genderは必須です", details={"field": "gender"})

    height = body.get("height")
    if height is None:
        raise ValidationError("heightは必須です", details={"field": "height"})

    weight = body.get("weight")
    if weight is None:
        raise ValidationError("weightは必須です", details={"field": "weight"})

    activity_level_str = body.get("activity_level")
    if not activity_level_str:
        raise ValidationError("activity_levelは必須です", details={"field": "activity_level"})

    # genderとactivity_levelの変換
    try:
        gender = Gender(gender_str)
    except ValueError:
        raise ValidationError(
            f"無効なgender: {gender_str}（male または female を指定してください）",
            details={"gender": gender_str}
        )

    try:
        activity_level = ActivityLevel(activity_level_str)
    except ValueError:
        raise ValidationError(
            f"無効なactivity_level: {activity_level_str}",
            details={"activity_level": activity_level_str}
        )

    # プロフィールを作成
    user = ProfileManager.create_profile(
        user_id=cognito_user_id,
        age=int(age),
        height=float(height),
        weight=float(weight),
        gender=gender,
        activity_level=activity_level,
        cognito_user_id=cognito_user_id
    )

    # DynamoDBに保存
    users_db.put_item(user.to_dict())

    logger.info(
        f"ユーザープロフィールを作成しました: {cognito_user_id}",
        extra={"extra_data": {"user_id": cognito_user_id}}
    )

    return success_response(user.to_dict(), status_code=201)


def get_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザープロフィールを取得する (GET /users/{user_id})

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス
    """
    path_parameters = event.get("pathParameters") or {}
    user_id = path_parameters.get("user_id")

    if not user_id:
        raise ValidationError("user_idは必須です", details={"field": "user_id"})

    # DynamoDBからユーザープロフィールを取得
    user_data = users_db.get_item({"user_id": user_id})

    if not user_data:
        raise ResourceNotFoundError(
            f"ユーザープロフィール {user_id} が見つかりません",
            details={"user_id": user_id}
        )

    logger.info(
        f"ユーザープロフィールを取得しました: {user_id}",
        extra={"extra_data": {"user_id": user_id}}
    )

    return success_response(user_data)


def get_current_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    認証ユーザー自身のプロフィールを取得する (GET /users/me)

    @require_auth デコレータにより、event["auth_user"] に認証情報が設定されている

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス
    """
    auth_user = event.get("auth_user", {})
    user_id = auth_user.get("user_id")

    if not user_id:
        raise ValidationError(
            "認証情報からユーザーIDを取得できませんでした",
            details={"auth_user": auth_user}
        )

    # DynamoDBからユーザープロフィールを取得
    user_data = users_db.get_item({"user_id": user_id})

    if not user_data:
        # ユーザーが存在しない場合、LINE User ID があれば基本情報を返す
        line_user_id = auth_user.get("line_user_id")
        if line_user_id:
            # LINEユーザーの場合、基本的なプロフィール情報を返す
            user_data = {
                "user_id": user_id,
                "line_user_id": line_user_id,
                "auth_type": "line",
                "profile_complete": False,
            }
            logger.info(
                f"LINEユーザーの基本情報を返します: {user_id}",
                extra={"extra_data": {"user_id": user_id, "line_user_id": line_user_id}}
            )
            return success_response(user_data)

        raise ResourceNotFoundError(
            f"ユーザープロフィール {user_id} が見つかりません",
            details={"user_id": user_id}
        )

    logger.info(
        f"認証ユーザーのプロフィールを取得しました: {user_id}",
        extra={"extra_data": {"user_id": user_id}}
    )

    return success_response(user_data)


def update_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    ユーザープロフィールを更新する (PUT /users/{user_id})

    Args:
        event: API Gatewayイベント

    Returns:
        API Gatewayレスポンス
    """
    path_parameters = event.get("pathParameters") or {}
    user_id = path_parameters.get("user_id")

    if not user_id:
        raise ValidationError("user_idは必須です", details={"field": "user_id"})

    # リクエストボディを解析
    body = json.loads(event.get("body", "{}"))

    # 既存のユーザープロフィールを取得
    existing_user_data = users_db.get_item({"user_id": user_id})

    # プロフィールが存在しないか、不完全な場合（LINE認証で作成された初期状態）
    # 新規プロフィール作成として処理
    is_new_profile = (
        not existing_user_data or
        not existing_user_data.get("age") or
        not existing_user_data.get("height") or
        not existing_user_data.get("weight")
    )

    if is_new_profile:
        # 新規プロフィール作成として処理
        logger.info(f"ユーザー {user_id} のプロフィールを新規作成します")

        # 必須フィールドのバリデーション
        age = body.get("age")
        if age is None:
            raise ValidationError("ageは必須です", details={"field": "age"})

        gender_str = body.get("gender")
        if not gender_str:
            raise ValidationError("genderは必須です", details={"field": "gender"})

        height = body.get("height")
        if height is None:
            raise ValidationError("heightは必須です", details={"field": "height"})

        weight = body.get("weight")
        if weight is None:
            raise ValidationError("weightは必須です", details={"field": "weight"})

        activity_level_str = body.get("activity_level")
        if not activity_level_str:
            raise ValidationError("activity_levelは必須です", details={"field": "activity_level"})

        # genderとactivity_levelの変換
        try:
            gender = Gender(gender_str)
        except ValueError:
            raise ValidationError(
                f"無効なgender: {gender_str}（male または female を指定してください）",
                details={"gender": gender_str}
            )

        try:
            activity_level = ActivityLevel(activity_level_str)
        except ValueError:
            raise ValidationError(
                f"無効なactivity_level: {activity_level_str}",
                details={"activity_level": activity_level_str}
            )

        # 既存データからLINE User IDを引き継ぐ
        line_user_id = existing_user_data.get("line_user_id") if existing_user_data else None

        # プロフィールを作成
        user = ProfileManager.create_profile(
            user_id=user_id,
            age=int(age),
            height=float(height),
            weight=float(weight),
            gender=gender,
            activity_level=activity_level,
            line_user_id=line_user_id
        )

        # DynamoDBに保存
        users_db.put_item(user.to_dict())

        logger.info(
            f"ユーザープロフィールを作成しました: {user_id}",
            extra={"extra_data": {"user_id": user_id}}
        )

        return success_response(user.to_dict(), status_code=201)

    # 既存プロフィールの更新
    # Userオブジェクトを復元
    user = User.from_dict(existing_user_data)

    # 更新可能なフィールド
    age = body.get("age")
    height = body.get("height")
    weight = body.get("weight")
    gender_str = body.get("gender")
    activity_level_str = body.get("activity_level")

    # gender と activity_level の変換
    gender = None
    if gender_str:
        try:
            gender = Gender(gender_str)
        except ValueError:
            raise ValidationError(
                f"無効なgender: {gender_str}",
                details={"gender": gender_str}
            )

    activity_level = None
    if activity_level_str:
        try:
            activity_level = ActivityLevel(activity_level_str)
        except ValueError:
            raise ValidationError(
                f"無効なactivity_level: {activity_level_str}",
                details={"activity_level": activity_level_str}
            )

    # プロフィールを更新
    updated_user = ProfileManager.update_profile(
        user=user,
        age=int(age) if age is not None else None,
        height=float(height) if height is not None else None,
        weight=float(weight) if weight is not None else None,
        gender=gender,
        activity_level=activity_level
    )

    # DynamoDBを更新
    users_db.put_item(updated_user.to_dict())

    logger.info(
        f"ユーザープロフィールを更新しました: {user_id}",
        extra={"extra_data": {"user_id": user_id}}
    )

    return success_response(updated_user.to_dict())
