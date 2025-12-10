"""
Lambda Authorizer for API Gateway

Cognito トークンまたは LINE User ID による認証をサポート
"""

import json
import logging
import os
import re
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ロギング設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "meal-management-app-users-dev")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# AWSクライアント
dynamodb = boto3.resource("dynamodb")
cognito_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)


def lambda_handler(event: dict, context: Any) -> dict:
    """
    API Gateway Lambda Authorizer

    認証方式:
    1. Authorization ヘッダー: Cognito JWT トークン
    2. X-Line-User-Id ヘッダー: LINE User ID（DynamoDB で検証）
    """
    logger.info(f"Authorizer event: {json.dumps(event)}")

    try:
        # ヘッダーを取得（大文字小文字を考慮）
        headers = event.get("headers", {}) or {}
        headers_lower = {k.lower(): v for k, v in headers.items()}

        authorization = headers_lower.get("authorization", "")
        line_user_id = headers_lower.get("x-line-user-id", "")

        method_arn = event.get("methodArn", "")

        # 1. Cognito トークンで認証を試行
        if authorization.startswith("Bearer "):
            token = authorization[7:]  # "Bearer " を除去
            user_info = verify_cognito_token(token)
            if user_info:
                logger.info(f"Cognito auth successful: {user_info.get('sub')}")
                return generate_policy(
                    user_info.get("sub"),
                    "Allow",
                    method_arn,
                    context={
                        "userId": user_info.get("sub"),
                        "email": user_info.get("email", ""),
                        "authType": "cognito",
                    },
                )

        # 2. LINE User ID で認証を試行
        if line_user_id:
            user_data = verify_line_user_id(line_user_id)
            if user_data:
                logger.info(f"LINE auth successful: {user_data.get('user_id')}")
                return generate_policy(
                    line_user_id,
                    "Allow",
                    method_arn,
                    context={
                        "userId": user_data.get("user_id"),
                        "lineUserId": line_user_id,
                        "authType": "line",
                    },
                )

        # 認証失敗
        logger.warning("Authentication failed: no valid credentials")
        return generate_policy("unauthorized", "Deny", method_arn)

    except Exception as e:
        logger.error(f"Authorizer error: {str(e)}")
        return generate_policy("error", "Deny", event.get("methodArn", ""))


def verify_cognito_token(token: str) -> dict | None:
    """
    Cognito トークンを検証

    Args:
        token: JWT トークン

    Returns:
        ユーザー情報（検証成功時）または None
    """
    try:
        # Cognito API でトークンを検証
        response = cognito_client.get_user(AccessToken=token)

        # ユーザー属性を辞書に変換
        user_attrs = {attr["Name"]: attr["Value"] for attr in response.get("UserAttributes", [])}

        return {
            "sub": user_attrs.get("sub"),
            "email": user_attrs.get("email"),
            "username": response.get("Username"),
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
        ユーザーデータ（検証成功時）または None
    """
    # LINE User ID の形式チェック（U + 32文字の16進数）
    if not re.match(r"^U[a-f0-9]{32}$", line_user_id):
        logger.warning(f"Invalid LINE User ID format: {line_user_id}")
        return None

    try:
        table = dynamodb.Table(USERS_TABLE_NAME)

        # GSI を使用して line_user_id で検索
        response = table.query(
            IndexName="LineUserIdIndex",
            KeyConditionExpression="line_user_id = :lid",
            ExpressionAttributeValues={":lid": line_user_id},
        )

        items = response.get("Items", [])
        if items:
            return items[0]

        logger.warning(f"LINE User ID not found in database: {line_user_id}")
        return None

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"LINE User ID verification error: {str(e)}")
        return None


def generate_policy(principal_id: str, effect: str, resource: str, context: dict = None) -> dict:
    """
    IAM ポリシードキュメントを生成

    Args:
        principal_id: プリンシパルID
        effect: Allow または Deny
        resource: リソースARN
        context: 追加コンテキスト（Lambda 関数に渡される）

    Returns:
        API Gateway Authorizer レスポンス
    """
    # リソースからワイルドカードパターンを生成
    # arn:aws:execute-api:region:account-id:api-id/stage/method/resource-path
    # → arn:aws:execute-api:region:account-id:api-id/stage/*
    resource_parts = resource.split("/")
    if len(resource_parts) >= 2:
        # stage までを取得し、残りを * に
        resource_base = "/".join(resource_parts[:2]) + "/*"
    else:
        resource_base = resource

    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource_base,
                }
            ],
        },
    }

    if context:
        policy["context"] = context

    return policy
