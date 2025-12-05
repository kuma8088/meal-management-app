"""
LINE Webhook Handler Lambda関数

要件: 1.1, 9.1, 9.2, 9.3, 9.4, 9.5, 11.1, 11.2, 11.3, 11.4, 11.5
"""
import json
import os
import hmac
import hashlib
import base64
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path
import urllib.request
import urllib.parse

# AWS SDK
import boto3
from botocore.exceptions import ClientError

# 共通ライブラリをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))

from common import (
    ValidationError,
    AuthorizationError,
    get_logger,
    success_response,
    error_response
)

logger = get_logger(__name__)

# 環境変数
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_REPLY_API_URL = "https://api.line.me/v2/bot/message/reply"

# Lambda clients (他のLambda関数を呼び出す)
lambda_client = boto3.client("lambda")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda関数のメインハンドラー

    Args:
        event: API Gatewayイベント
        context: Lambda context

    Returns:
        API Gatewayレスポンス

    要件: 11.1
    """
    try:
        logger.info(f"LINE Webhook received: {json.dumps(event)}")

        # 署名検証（要件: セキュリティ）
        if not verify_signature(event):
            logger.warning("Invalid signature")
            return error_response(
                AuthorizationError("Invalid signature")
            )

        # Webhookイベントの解析
        body = json.loads(event.get("body", "{}"))
        events = body.get("events", [])

        if not events:
            logger.info("No events to process")
            return success_response({"message": "No events"})

        # 各イベントを処理
        for line_event in events:
            process_event(line_event)

        return success_response({"message": "OK"})

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return error_response(e)


def verify_signature(event: Dict[str, Any]) -> bool:
    """
    LINE Webhookの署名を検証する

    Args:
        event: API Gatewayイベント

    Returns:
        署名が有効ならTrue、無効ならFalse

    要件: セキュリティ
    """
    # X-Line-Signatureヘッダーを取得
    headers = event.get("headers", {})
    signature = headers.get("x-line-signature") or headers.get("X-Line-Signature")

    if not signature:
        logger.warning("No signature in headers")
        return False

    # リクエストボディを取得
    body = event.get("body", "")

    # HMAC-SHA256で署名を計算
    secret = LINE_CHANNEL_SECRET.encode("utf-8")
    body_bytes = body.encode("utf-8")

    expected_signature = base64.b64encode(
        hmac.new(secret, body_bytes, hashlib.sha256).digest()
    ).decode("utf-8")

    # 署名を比較
    is_valid = hmac.compare_digest(signature, expected_signature)

    if not is_valid:
        logger.warning(f"Signature mismatch: expected={expected_signature}, actual={signature}")

    return is_valid


def process_event(line_event: Dict[str, Any]) -> None:
    """
    LINE Webhookイベントを処理する

    Args:
        line_event: LINEイベント

    要件: 11.1, 11.2, 11.3, 11.4
    """
    event_type = line_event.get("type")

    if event_type != "message":
        logger.info(f"Ignoring non-message event: {event_type}")
        return

    # メッセージイベントを処理
    message = line_event.get("message", {})
    message_type = message.get("type")

    # ユーザー情報
    source = line_event.get("source", {})
    line_user_id = source.get("userId")
    reply_token = line_event.get("replyToken")

    if not line_user_id or not reply_token:
        logger.warning("Missing user_id or reply_token")
        return

    logger.info(f"Processing message: type={message_type}, user={line_user_id}")

    try:
        if message_type == "text":
            # テキストメッセージを処理（要件: 11.2, 11.3, 11.4）
            process_text_message(line_user_id, message, reply_token)
        elif message_type == "image":
            # 画像メッセージを処理（バーコード認識）
            process_image_message(line_user_id, message, reply_token)
        else:
            # 未対応のメッセージタイプ
            logger.info(f"Unsupported message type: {message_type}")
            send_reply(reply_token, "申し訳ございません。このメッセージタイプには対応していません。")

    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        send_reply(reply_token, "エラーが発生しました。後ほど再度お試しください。")


def process_text_message(line_user_id: str, message: Dict[str, Any], reply_token: str) -> None:
    """
    テキストメッセージを処理する

    Args:
        line_user_id: LINE User ID
        message: メッセージオブジェクト
        reply_token: 返信トークン

    要件: 11.2, 11.3, 11.4
    """
    text = message.get("text", "").strip()

    logger.info(f"Processing text message: {text}")

    # メッセージの意図を判定
    if is_daily_advice_request(text):
        # 総評リクエスト（要件: 11.3）
        handle_daily_advice_request(line_user_id, reply_token)
    elif is_food_registration_request(text):
        # 食事登録リクエスト（要件: 11.2）
        handle_food_registration_request(line_user_id, text, reply_token)
    else:
        # ヘルプメッセージを送信（要件: 11.4）
        send_help_message(reply_token)


def process_image_message(line_user_id: str, message: Dict[str, Any], reply_token: str) -> None:
    """
    画像メッセージを処理する（バーコード認識）

    Args:
        line_user_id: LINE User ID
        message: メッセージオブジェクト
        reply_token: 返信トークン

    要件: バーコード認識統合
    """
    message_id = message.get("id")

    if not message_id:
        logger.warning("No message_id in image message")
        send_reply(reply_token, "画像の取得に失敗しました。")
        return

    logger.info(f"Processing image message: message_id={message_id}")

    # LINE Content APIのURLを構築
    image_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"

    # バーコード認識Lambda関数を呼び出し
    try:
        # TODO: バーコード認識Lambda関数の呼び出し
        # barcode_recognition Lambda関数にimage_urlを渡して、JANコードを取得
        # その後、food_searchでJANコードから食品を検索
        # 見つかった食品情報をユーザーに返信

        send_reply(reply_token, "バーコード認識機能は現在準備中です。")

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        send_reply(reply_token, "画像の処理中にエラーが発生しました。")


def is_daily_advice_request(text: str) -> bool:
    """
    テキストが総評リクエストかどうか判定

    Args:
        text: テキストメッセージ

    Returns:
        総評リクエストならTrue
    """
    # キーワード: "総評", "アドバイス", "今日", "まとめ", "評価"
    keywords = ["総評", "アドバイス", "今日", "まとめ", "評価"]
    text_lower = text.lower()

    return any(keyword in text_lower for keyword in keywords)


def is_food_registration_request(text: str) -> bool:
    """
    テキストが食事登録リクエストかどうか判定

    Args:
        text: テキストメッセージ

    Returns:
        食事登録リクエストならTrue
    """
    # キーワード: "食べた", "朝食", "昼食", "夕食", "おやつ", "登録"
    keywords = ["食べた", "朝食", "昼食", "夕食", "おやつ", "登録", "記録"]
    text_lower = text.lower()

    return any(keyword in text_lower for keyword in keywords)


def handle_daily_advice_request(line_user_id: str, reply_token: str) -> None:
    """
    総評リクエストを処理する

    Args:
        line_user_id: LINE User ID
        reply_token: 返信トークン

    要件: 11.3
    """
    try:
        # daily_summary Lambda関数を呼び出し
        from datetime import date

        payload = {
            "httpMethod": "POST",
            "path": "/advice/daily",
            "body": json.dumps({
                "user_id": line_user_id,
                "date": date.today().isoformat()
            })
        }

        # Lambda関数を同期的に呼び出し
        response = lambda_client.invoke(
            FunctionName="daily_summary",  # TODO: 環境変数から取得
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )

        # レスポンスを解析
        response_payload = json.loads(response["Payload"].read())

        if response_payload.get("statusCode") == 200:
            body = json.loads(response_payload.get("body", "{}"))

            if body.get("usage_limit_reached"):
                # 利用制限に達している
                message = body.get("message", "本日のアドバイス生成は上限に達しました。")
                send_reply(reply_token, message)
            else:
                # アドバイスを返信
                advice = body.get("advice", "アドバイスの生成に失敗しました。")
                total_calories = body.get("total_calories", 0)
                target_calories = body.get("target_calories", 0)

                reply_message = f"""【本日の総評】

総カロリー: {total_calories:.0f} kcal
目標カロリー: {target_calories:.0f} kcal

{advice}"""

                send_reply(reply_token, reply_message)
        else:
            # エラー
            logger.error(f"Error from daily_summary: {response_payload}")
            send_reply(reply_token, "総評の生成に失敗しました。後ほど再度お試しください。")

    except Exception as e:
        logger.error(f"Error handling daily advice request: {str(e)}", exc_info=True)
        send_reply(reply_token, "総評の生成中にエラーが発生しました。")


def handle_food_registration_request(line_user_id: str, text: str, reply_token: str) -> None:
    """
    食事登録リクエストを処理する

    Args:
        line_user_id: LINE User ID
        text: テキストメッセージ
        reply_token: 返信トークン

    要件: 11.2
    """
    # TODO: テキストから食品名と量を抽出する自然言語処理
    # 例: "朝食にご飯200gと納豆を食べた" -> ["ご飯", "200g"], ["納豆", "50g"]

    # 現在は簡易的な実装として、ヘルプメッセージを返す
    message = """食事登録は現在準備中です。

以下の形式でメッセージを送信してください：
「朝食にご飯200gと納豆50gを食べた」

または、食品のバーコード画像を送信してください。"""

    send_reply(reply_token, message)


def send_help_message(reply_token: str) -> None:
    """
    ヘルプメッセージを送信する

    Args:
        reply_token: 返信トークン

    要件: 11.4, 11.5
    """
    help_text = """【使い方】

■ 食事登録
食品のバーコード画像を送信するか、以下の形式でメッセージを送信してください：
「朝食にご飯200gと納豆50gを食べた」

■ 本日の総評
「総評」または「今日のアドバイス」と送信してください。

■ その他
質問や不明な点があれば、「ヘルプ」と送信してください。"""

    send_reply(reply_token, help_text)


def send_reply(reply_token: str, message: str) -> None:
    """
    LINE Messaging APIで返信する

    Args:
        reply_token: 返信トークン
        message: 返信メッセージ

    要件: 11.5
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
        }

        data = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }

        # LINE Messaging APIを呼び出し
        request = urllib.request.Request(
            LINE_REPLY_API_URL,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            logger.info(f"LINE API response: {response_body}")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"LINE API error: {e.code} {error_body}")
        raise
    except Exception as e:
        logger.error(f"Error sending reply: {str(e)}", exc_info=True)
        raise
