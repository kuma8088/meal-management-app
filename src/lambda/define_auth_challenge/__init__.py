"""
Define Auth Challenge Lambda Trigger

Cognito が最初に呼び出す Lambda 関数
認証フローの進行状況を判定し、次のチャレンジを決定
"""

import json
import logging
from typing import Any

# ロギング設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Define Auth Challenge Lambda Handler

    Args:
        event: Cognito Trigger イベント
        context: Lambda コンテキスト

    Returns:
        チャレンジ定義レスポンス
    """
    logger.info(f"DefineAuthChallenge event: {json.dumps(event)}")

    request = event.get("request", {})
    response = event.get("response", {})
    session = request.get("session", [])

    # session が空 = 初回認証
    if not session:
        logger.info("Initial authentication attempt - issuing CUSTOM_CHALLENGE")
        response["issueTokens"] = False
        response["failAuthentication"] = False
        response["challengeName"] = "CUSTOM_CHALLENGE"

    # 前回のチャレンジが成功した場合
    elif len(session) > 0 and session[-1].get("challengeResult") is True:
        logger.info("Challenge verified successfully - authentication complete")
        response["issueTokens"] = True
        response["failAuthentication"] = False

    # チャレンジが失敗した場合
    else:
        logger.warning("Challenge verification failed")
        response["issueTokens"] = False
        response["failAuthentication"] = True

    event["response"] = response
    logger.info(f"DefineAuthChallenge response: {json.dumps(response)}")

    return event
