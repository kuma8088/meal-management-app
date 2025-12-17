"""
Create Auth Challenge Lambda Trigger

チャレンジのパラメータを生成
LINE ID Token 検証用のチャレンジを作成
"""

import json
import logging
import os
import secrets
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ロギング設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数
LINE_CHANNEL_ID = os.environ.get("LINE_CHANNEL_ID", "")
NONCE_TABLE_NAME = os.environ.get("NONCE_TABLE_NAME", "")

# AWS クライアント
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Create Auth Challenge Lambda Handler

    Args:
        event: Cognito Trigger イベント
        context: Lambda コンテキスト

    Returns:
        チャレンジ生成レスポンス
    """
    logger.info(f"CreateAuthChallenge event: {json.dumps(event)}")

    request = event.get("request", {})
    response = event.get("response", {})

    # チャレンジタイプの確認
    if request.get("challengeName") == "CUSTOM_CHALLENGE":
        # nonce を生成（リプレイ攻撃防止）
        nonce = secrets.token_urlsafe(32)

        # nonce を DynamoDB に保存（TTL: 5分）
        try:
            save_nonce(nonce)
        except Exception as e:
            logger.error(f"Failed to save nonce: {str(e)}")
            # nonce 保存失敗でもチャレンジは発行（検証時にエラー）

        # チャレンジパラメータを設定
        response["publicChallengeParameters"] = {
            "challengeType": "LINE_ID_TOKEN",
            "nonce": nonce,
            "channelId": LINE_CHANNEL_ID,
        }

        # 秘密のチャレンジパラメータ（検証時に使用）
        response["privateChallengeParameters"] = {
            "nonce": nonce,
        }

        # メタデータ
        response["challengeMetadata"] = "LINE_ID_TOKEN_CHALLENGE"

        logger.info(f"Challenge created with nonce: {nonce}")

    event["response"] = response
    logger.info(f"CreateAuthChallenge response: {json.dumps(response)}")

    return event


def save_nonce(nonce: str) -> None:
    """
    nonce を DynamoDB に保存

    Args:
        nonce: 生成された nonce

    Raises:
        ClientError: DynamoDB エラー
    """
    if not NONCE_TABLE_NAME:
        logger.warning("NONCE_TABLE_NAME not configured - skipping nonce save")
        return

    import time

    table = dynamodb.Table(NONCE_TABLE_NAME)

    # TTL: 5分後（300秒）
    ttl = int(time.time()) + 300

    table.put_item(
        Item={
            "nonce": nonce,
            "ttl": ttl,
            "created_at": int(time.time()),
        }
    )

    logger.info(f"Nonce saved to DynamoDB: {nonce} (TTL: {ttl})")
