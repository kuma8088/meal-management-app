"""
Post Confirmation Lambda Trigger

ユーザー確認後に DynamoDB Users テーブルを更新
LINE ユーザーID と Cognito ユーザーID を紐付け
"""

import json
import logging
import os
import time
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ロギング設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "")

# AWS クライアント
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Post Confirmation Lambda Handler

    Args:
        event: Cognito Trigger イベント
        context: Lambda コンテキスト

    Returns:
        更新されたイベント
    """
    logger.info(f"PostConfirmation event: {json.dumps(event)}")

    request = event.get("request", {})
    user_attributes = request.get("userAttributes", {})

    # Cognito ユーザー情報
    cognito_user_id = user_attributes.get("sub", "")
    email = user_attributes.get("email", "")

    # カスタム属性から LINE User ID を取得
    line_user_id = user_attributes.get("custom:line_user_id", "")

    if not cognito_user_id:
        logger.error("Missing Cognito user ID")
        return event

    try:
        # ユーザーが既に存在するか確認
        existing_user = get_user_by_line_id(line_user_id) if line_user_id else None

        if existing_user:
            # 既存ユーザーに Cognito ID を追加
            update_user_cognito_id(existing_user["user_id"], cognito_user_id, email)
            logger.info(f"Updated existing user: {existing_user['user_id']}")
        else:
            # 新規ユーザーを作成
            user_id = str(uuid.uuid4())
            create_user(user_id, cognito_user_id, line_user_id, email)
            logger.info(f"Created new user: {user_id}")

    except Exception as e:
        logger.error(f"Post confirmation error: {str(e)}")
        # エラーが発生してもユーザー作成は継続
        # （DynamoDB への書き込み失敗でも Cognito ユーザーは作成される）

    return event


def get_user_by_line_id(line_user_id: str) -> dict | None:
    """
    LINE User ID でユーザーを取得

    Args:
        line_user_id: LINE ユーザーID

    Returns:
        ユーザーデータ（存在する場合）または None
    """
    if not USERS_TABLE_NAME or not line_user_id:
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

        return None

    except ClientError as e:
        logger.error(f"DynamoDB query error: {str(e)}")
        return None


def update_user_cognito_id(user_id: str, cognito_user_id: str, email: str) -> None:
    """
    既存ユーザーに Cognito ID を追加

    Args:
        user_id: ユーザーID
        cognito_user_id: Cognito ユーザーID
        email: メールアドレス

    Raises:
        ClientError: DynamoDB エラー
    """
    if not USERS_TABLE_NAME:
        logger.warning("USERS_TABLE_NAME not configured")
        return

    table = dynamodb.Table(USERS_TABLE_NAME)

    update_expr = "SET cognito_user_id = :cid, updated_at = :updated"
    expr_values = {
        ":cid": cognito_user_id,
        ":updated": int(time.time()),
    }

    # メールアドレスがある場合は追加
    if email:
        update_expr += ", email = :email"
        expr_values[":email"] = email

    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values,
    )

    logger.info(f"Updated user {user_id} with Cognito ID: {cognito_user_id}")


def create_user(user_id: str, cognito_user_id: str, line_user_id: str, email: str) -> None:
    """
    新規ユーザーを作成

    Args:
        user_id: ユーザーID
        cognito_user_id: Cognito ユーザーID
        line_user_id: LINE ユーザーID（オプション）
        email: メールアドレス（オプション）

    Raises:
        ClientError: DynamoDB エラー
    """
    if not USERS_TABLE_NAME:
        logger.warning("USERS_TABLE_NAME not configured")
        return

    table = dynamodb.Table(USERS_TABLE_NAME)

    item = {
        "user_id": user_id,
        "cognito_user_id": cognito_user_id,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }

    # オプション属性
    if line_user_id:
        item["line_user_id"] = line_user_id

    if email:
        item["email"] = email

    table.put_item(Item=item)

    logger.info(f"Created new user: {user_id}")
