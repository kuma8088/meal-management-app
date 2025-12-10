"""
共通認証モジュール

Cognito トークンまたは LINE User ID による認証をサポート
"""

import json
import logging
import os
import re
from functools import wraps
from typing import Any, Callable

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "meal-management-app-users-dev")
COGNITO_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# AWSクライアント（遅延初期化）
_dynamodb = None
_cognito_client = None


def get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def get_cognito_client():
    global _cognito_client
    if _cognito_client is None:
        _cognito_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    return _cognito_client


def get_headers_dict(event: dict) -> dict:
    """
    イベントからヘッダーを取得（大文字小文字を正規化）
    """
    headers = event.get("headers") or {}
    return {k.lower(): v for k, v in headers.items()}


def verify_cognito_token(token: str) -> dict | None:
    """
    Cognito アクセストークンを検証

    Args:
        token: JWT アクセストークン

    Returns:
        ユーザー情報（検証成功時）または None
    """
    try:
        cognito = get_cognito_client()
        response = cognito.get_user(AccessToken=token)

        # ユーザー属性を辞書に変換
        user_attrs = {attr["Name"]: attr["Value"] for attr in response.get("UserAttributes", [])}

        return {
            "user_id": user_attrs.get("sub"),
            "email": user_attrs.get("email"),
            "username": response.get("Username"),
            "auth_type": "cognito",
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ["NotAuthorizedException", "UserNotFoundException"]:
            logger.warning(f"Cognito token validation failed: {error_code}")
        else:
            logger.error(f"Cognito API error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return None


def verify_line_user_id(line_user_id: str) -> dict | None:
    """
    LINE User ID を DynamoDB で検証

    Args:
        line_user_id: LINE ユーザーID

    Returns:
        ユーザー情報（検証成功時）または None
    """
    # LINE User ID の形式チェック（U + 32文字の16進数）
    if not re.match(r"^U[a-f0-9]{32}$", line_user_id):
        logger.warning(f"Invalid LINE User ID format: {line_user_id}")
        return None

    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(USERS_TABLE_NAME)

        # GSI を使用して line_user_id で検索
        response = table.query(
            IndexName="LineUserIdIndex",
            KeyConditionExpression="line_user_id = :lid",
            ExpressionAttributeValues={":lid": line_user_id},
        )

        items = response.get("Items", [])
        if items:
            user = items[0]
            return {
                "user_id": user.get("user_id"),
                "line_user_id": line_user_id,
                "auth_type": "line",
            }

        logger.warning(f"LINE User ID not found in database: {line_user_id}")
        return None

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"LINE User ID verification error: {str(e)}")
        return None


def authenticate(event: dict) -> dict | None:
    """
    リクエストを認証

    Args:
        event: API Gateway イベント

    Returns:
        認証情報（成功時）または None
    """
    headers = get_headers_dict(event)

    # 1. Cognito トークンで認証を試行
    authorization = headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        user_info = verify_cognito_token(token)
        if user_info:
            logger.info(f"Cognito auth successful: {user_info.get('user_id')}")
            return user_info

    # 2. LINE User ID で認証を試行
    line_user_id = headers.get("x-line-user-id", "")
    if line_user_id:
        user_info = verify_line_user_id(line_user_id)
        if user_info:
            logger.info(f"LINE auth successful: {user_info.get('user_id')}")
            return user_info

    logger.warning("Authentication failed: no valid credentials")
    return None


def unauthorized_response() -> dict:
    """
    401 Unauthorized レスポンスを生成
    """
    return {
        "statusCode": 401,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Line-User-Id",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps({
            "error": {
                "code": "UNAUTHORIZED",
                "message": "認証が必要です",
            }
        }),
    }


def is_internal_invocation(event: dict) -> bool:
    """
    Lambda-to-Lambda の内部呼び出しかどうかを判定

    API Gateway 経由の場合は requestContext が存在する
    内部呼び出しの場合は requestContext が存在しない
    """
    # API Gateway からの呼び出しには requestContext がある
    if event.get("requestContext"):
        return False

    # headers がない、または空の場合は内部呼び出し
    headers = event.get("headers")
    if not headers:
        return True

    return False


def require_auth(handler: Callable) -> Callable:
    """
    認証を必須にするデコレータ

    使用例:
        @require_auth
        def lambda_handler(event, context):
            # event["auth_user"] に認証ユーザー情報が入る
            user = event["auth_user"]
            ...

    注意:
        - API Gateway 経由: Cognito トークンまたは LINE User ID で認証
        - Lambda-to-Lambda 内部呼び出し: 認証をスキップ（呼び出し元で認証済み）
    """
    @wraps(handler)
    def wrapper(event: dict, context: Any) -> dict:
        # OPTIONS リクエストは認証不要（CORS プリフライト）
        if event.get("httpMethod") == "OPTIONS":
            return handler(event, context)

        # Lambda-to-Lambda 内部呼び出しは認証スキップ
        if is_internal_invocation(event):
            logger.info("Internal Lambda invocation detected, skipping auth")
            # 内部呼び出しでも auth_user を設定（空の辞書）
            event["auth_user"] = {"auth_type": "internal"}
            return handler(event, context)

        # API Gateway 経由は通常の認証
        auth_user = authenticate(event)
        if not auth_user:
            return unauthorized_response()

        # 認証情報をイベントに追加
        event["auth_user"] = auth_user

        return handler(event, context)

    return wrapper
