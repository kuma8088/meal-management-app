"""
Verify Auth Challenge Lambda Trigger

LINE 認証チャレンジを検証:
1. Access Token 方式: 既に liff_login API で検証済み → パススルー
2. ID Token 方式: LINE ID Token を JWKS で検証（後方互換性）
"""

import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ロギング設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数
LINE_CHANNEL_ID = os.environ.get("LINE_CHANNEL_ID", "")
NONCE_TABLE_NAME = os.environ.get("NONCE_TABLE_NAME", "")
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "")

# LINE JWKS エンドポイント（ID Token 方式用）
LINE_JWKS_URL = "https://api.line.me/oauth2/v2.1/certs"

# AWS クライアント
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Verify Auth Challenge Lambda Handler

    Args:
        event: Cognito Trigger イベント
        context: Lambda コンテキスト

    Returns:
        検証結果レスポンス
    """
    logger.info(f"VerifyAuthChallenge event: {json.dumps(event)}")

    request = event.get("request", {})
    response = event.get("response", {})

    # チャレンジの回答
    challenge_answer = request.get("challengeAnswer", "")

    # プライベートチャレンジパラメータから nonce を取得
    private_params = request.get("privateChallengeParameters", {})
    expected_nonce = private_params.get("nonce", "")

    # クライアントメタデータから認証方式を取得
    client_metadata = request.get("clientMetadata", {})
    auth_method = client_metadata.get("auth_method", "")

    # デフォルトは失敗
    response["answerCorrect"] = False

    try:
        # Access Token 方式: "ACCESS_TOKEN_VERIFIED:{line_user_id}:{nonce}"
        if challenge_answer.startswith("ACCESS_TOKEN_VERIFIED:"):
            result = verify_access_token_answer(challenge_answer, expected_nonce, client_metadata)
            response["answerCorrect"] = result

        # ID Token 方式（後方互換性）: "{line_id_token}:{nonce}"
        else:
            result = verify_id_token_answer(challenge_answer, expected_nonce)
            response["answerCorrect"] = result

    except Exception as e:
        logger.error(f"Challenge verification error: {str(e)}")
        response["answerCorrect"] = False

    event["response"] = response
    logger.info(f"VerifyAuthChallenge response: {json.dumps(response)}")

    return event


def verify_access_token_answer(answer: str, expected_nonce: str, client_metadata: dict) -> bool:
    """
    Access Token 方式のチャレンジ回答を検証

    liff_login API で既に LINE API による検証が完了しているため、
    ここでは nonce と line_user_id の一致のみ確認

    Args:
        answer: "ACCESS_TOKEN_VERIFIED:{line_user_id}:{nonce}"
        expected_nonce: 期待される nonce
        client_metadata: クライアントメタデータ

    Returns:
        検証結果
    """
    try:
        parts = answer.split(":")
        if len(parts) != 3:
            logger.warning(f"Invalid answer format: expected 3 parts, got {len(parts)}")
            return False

        prefix, line_user_id, nonce = parts

        if prefix != "ACCESS_TOKEN_VERIFIED":
            logger.warning(f"Invalid prefix: {prefix}")
            return False

        # nonce の検証
        if nonce != expected_nonce:
            logger.warning(f"Nonce mismatch: expected {expected_nonce}, got {nonce}")
            return False

        # line_user_id の検証（クライアントメタデータと一致するか）
        expected_line_user_id = client_metadata.get("line_user_id", "")
        if line_user_id != expected_line_user_id:
            logger.warning(f"Line user ID mismatch")
            return False

        # nonce を使用済みにマーク
        try:
            mark_nonce_used(expected_nonce)
        except Exception as e:
            logger.warning(f"Failed to mark nonce as used: {str(e)}")

        logger.info(f"Access Token verification passed for user: {line_user_id[:10]}...")
        return True

    except Exception as e:
        logger.error(f"Access token answer verification error: {str(e)}")
        return False


def verify_id_token_answer(answer: str, expected_nonce: str) -> bool:
    """
    ID Token 方式のチャレンジ回答を検証（後方互換性）

    Args:
        answer: "{line_id_token}:{nonce}"
        expected_nonce: 期待される nonce

    Returns:
        検証結果
    """
    try:
        # JWT ライブラリをインポート（ID Token 方式のみ使用）
        import jwt
        from jwt import PyJWKClient

        # 回答をパース: "{id_token}:{nonce}"
        parts = answer.rsplit(":", 1)
        if len(parts) != 2:
            logger.warning("Invalid ID token answer format")
            return False

        id_token, nonce = parts

        # nonce の検証
        if nonce != expected_nonce:
            logger.warning("Nonce mismatch in ID token answer")
            return False

        # LINE ID Token を検証
        payload = verify_line_id_token(id_token, expected_nonce)
        if not payload:
            return False

        # nonce を使用済みにマーク
        try:
            mark_nonce_used(expected_nonce)
        except Exception as e:
            logger.warning(f"Failed to mark nonce as used: {str(e)}")

        logger.info(f"ID Token verification passed for user: {payload.get('sub')}")
        return True

    except ImportError:
        logger.error("jwt library not available for ID token verification")
        return False
    except Exception as e:
        logger.error(f"ID token answer verification error: {str(e)}")
        return False


def verify_line_id_token(id_token: str, expected_nonce: str) -> dict | None:
    """
    LINE ID Token を検証（後方互換性用）

    Args:
        id_token: LINE ID Token
        expected_nonce: 期待される nonce

    Returns:
        ペイロード（検証成功時）または None
    """
    try:
        import jwt
        from jwt import PyJWKClient

        # JWKS クライアントを初期化
        jwks_client = PyJWKClient(LINE_JWKS_URL)

        # 署名キーを取得
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)

        # ID Token をデコード・検証
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=LINE_CHANNEL_ID,
            options={
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )

        # issuer の検証
        if payload.get("iss") != "https://access.line.me":
            logger.warning(f"Invalid issuer: {payload.get('iss')}")
            return None

        # nonce の検証
        if payload.get("nonce") != expected_nonce:
            logger.warning("Nonce mismatch in ID token")
            return None

        # 有効期限の検証（追加チェック）
        exp = payload.get("exp", 0)
        if exp < time.time():
            logger.warning("Token expired")
            return None

        logger.info(f"ID Token verified: sub={payload.get('sub')}")
        return payload

    except Exception as e:
        logger.error(f"ID Token verification error: {str(e)}")
        return None


def mark_nonce_used(nonce: str) -> None:
    """
    nonce を使用済みとしてマーク

    Args:
        nonce: 使用済みの nonce

    Raises:
        ClientError: DynamoDB エラー
    """
    if not NONCE_TABLE_NAME:
        logger.warning("NONCE_TABLE_NAME not configured - skipping nonce mark")
        return

    table = dynamodb.Table(NONCE_TABLE_NAME)

    # used フラグを追加
    table.update_item(
        Key={"nonce": nonce},
        UpdateExpression="SET used = :used, used_at = :used_at",
        ExpressionAttributeValues={
            ":used": True,
            ":used_at": int(time.time()),
        },
    )

    logger.info(f"Nonce marked as used: {nonce}")
