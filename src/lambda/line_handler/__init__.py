"""
LINE Webhook Handler Lambda関数

要件: 1.1, 9.1, 9.2, 9.3, 9.4, 9.5, 11.1, 11.2, 11.3, 11.4, 11.5
"""
import json
import os
import hmac
import hashlib
import base64
import re
from typing import Any, Dict, List, Optional, Tuple
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
    DynamoDBHelper,
    get_logger,
    success_response,
    error_response,
    BarcodeRecognition
)

logger = get_logger(__name__)

# 環境変数
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_REPLY_API_URL = "https://api.line.me/v2/bot/message/reply"
DAILY_SUMMARY_FUNCTION_NAME = os.environ.get("DAILY_SUMMARY_FUNCTION_NAME", "")
FOOD_SEARCH_FUNCTION_NAME = os.environ.get("FOOD_SEARCH_FUNCTION_NAME", "")
MEAL_REGISTRATION_FUNCTION_NAME = os.environ.get("MEAL_REGISTRATION_FUNCTION_NAME", "")
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "Users")
LIFF_ID = os.environ.get("LIFF_ID", "2008658695-M1gQv1N3")
LIFF_URL = f"https://liff.line.me/{LIFF_ID}"

# Lambda clients (他のLambda関数を呼び出す)
lambda_client = boto3.client("lambda")

# DynamoDB helper
users_db = DynamoDBHelper(USERS_TABLE_NAME)


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


def get_or_create_user(line_user_id: str) -> str:
    """
    LINE User ID からユーザーを取得または作成する

    Args:
        line_user_id: LINE User ID

    Returns:
        user_id: システム内部のユーザーID

    Note:
        LINE ユーザーが初めてメッセージを送信した際に、
        自動的に Users テーブルにエントリを作成する。
    """
    import uuid
    from datetime import datetime

    try:
        # LineUserIdIndex GSI でユーザーを検索
        response = users_db.table.query(
            IndexName="LineUserIdIndex",
            KeyConditionExpression="line_user_id = :line_user_id",
            ExpressionAttributeValues={
                ":line_user_id": line_user_id
            },
            Limit=1
        )

        items = response.get("Items", [])

        if items:
            # 既存ユーザーが見つかった
            user_id = items[0].get("user_id")
            logger.info(f"Found existing user: line_user_id={line_user_id}, user_id={user_id}")
            return user_id

        # 新規ユーザーを作成
        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        user_data = {
            "user_id": user_id,
            "line_user_id": line_user_id,
            "created_at": now,
            "updated_at": now,
            # デフォルト値（後でプロフィール設定で更新可能）
            "tdee": 2000.0,
            "bmr": 1500.0,
            "source": "line"
        }

        users_db.put_item(user_data)

        logger.info(f"Created new user: line_user_id={line_user_id}, user_id={user_id}")

        return user_id

    except Exception as e:
        logger.error(f"Error in get_or_create_user: {str(e)}", exc_info=True)
        # エラー時は LINE User ID をそのまま使用（フォールバック）
        return line_user_id


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

    # ユーザーを取得または作成
    user_id = get_or_create_user(line_user_id)

    logger.info(f"Processing message: type={message_type}, line_user_id={line_user_id}, user_id={user_id}")

    try:
        if message_type == "text":
            # テキストメッセージを処理（要件: 11.2, 11.3, 11.4）
            process_text_message(user_id, line_user_id, message, reply_token)
        elif message_type == "image":
            # 画像メッセージを処理（バーコード認識）
            process_image_message(user_id, message, reply_token)
        else:
            # 未対応のメッセージタイプ
            logger.info(f"Unsupported message type: {message_type}")
            send_reply(reply_token, "申し訳ございません。このメッセージタイプには対応していません。")

    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        send_reply(reply_token, "エラーが発生しました。後ほど再度お試しください。")


def process_text_message(user_id: str, line_user_id: str, message: Dict[str, Any], reply_token: str) -> None:
    """
    テキストメッセージを処理する

    Args:
        user_id: システム内部のユーザーID（UUID形式）
        line_user_id: LINE User ID（U + 32文字の16進数）
        message: メッセージオブジェクト
        reply_token: 返信トークン

    要件: 11.2, 11.3, 11.4
    """
    text = message.get("text", "").strip()

    logger.info(f"Processing text message: {text}")

    # メッセージの意図を判定
    if is_id_request(text):
        # ID確認リクエスト（デバッグ・サポート用）
        handle_id_request(user_id, line_user_id, reply_token)
    elif is_app_request(text):
        # アプリ（LIFF）リンクリクエスト
        send_app_link(reply_token)
    elif is_daily_advice_request(text):
        # 総評リクエスト（要件: 11.3）
        handle_daily_advice_request(user_id, reply_token)
    elif is_food_registration_request(text):
        # 食事登録リクエスト（要件: 11.2）
        handle_food_registration_request(user_id, text, reply_token)
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

    # バーコード認識を実行
    try:
        # バーコード認識クラスのインスタンス化
        barcode_recognizer = BarcodeRecognition()

        # 画像からJANコードを認識
        result = barcode_recognizer.recognize_from_url(
            image_url=image_url,
            line_channel_access_token=LINE_CHANNEL_ACCESS_TOKEN
        )

        jan_code = result.get("jan_code")
        confidence = result.get("confidence", 0)

        if not jan_code:
            send_reply(reply_token, "バーコードを認識できませんでした。もう一度、はっきりとバーコードが写るように撮影してください。")
            return

        logger.info(f"Recognized JAN code: {jan_code} (confidence: {confidence})")

        # JANコードで食品を検索
        # food_search Lambda関数を呼び出し
        try:
            response = lambda_client.invoke(
                FunctionName=os.environ.get("FOOD_SEARCH_FUNCTION_NAME", "food_search"),
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    "queryStringParameters": {
                        "jan_code": jan_code
                    }
                })
            )

            search_result = json.loads(response['Payload'].read())

            if search_result.get("statusCode") == 200:
                body = json.loads(search_result.get("body", "{}"))
                foods = body.get("foods", [])

                if foods:
                    food = foods[0]  # 最初の結果を使用
                    # 食品情報を整形してメッセージを作成
                    message = f"【{food.get('name', '不明')}】\n"
                    message += f"カロリー: {food.get('calories_per_100g', 0):.1f} kcal/100g\n"
                    message += f"たんぱく質: {food.get('protein_per_100g', 0):.1f} g/100g\n"
                    message += f"脂質: {food.get('fat_per_100g', 0):.1f} g/100g\n"
                    message += f"炭水化物: {food.get('carbs_per_100g', 0):.1f} g/100g"

                    send_reply(reply_token, message)
                else:
                    send_reply(reply_token, f"JANコード「{jan_code}」の食品情報が見つかりませんでした。")
            else:
                send_reply(reply_token, "食品検索中にエラーが発生しました。")

        except Exception as e:
            logger.error(f"Error searching food: {str(e)}", exc_info=True)
            send_reply(reply_token, f"JANコード「{jan_code}」で食品を検索できませんでした。")

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        send_reply(reply_token, "画像の処理中にエラーが発生しました。")


def is_id_request(text: str) -> bool:
    """
    テキストがID確認リクエストかどうか判定

    Args:
        text: テキストメッセージ

    Returns:
        ID確認リクエストならTrue
    """
    text_lower = text.lower().strip()
    keywords = ["id", "myid", "my id", "マイid", "ユーザーid", "userid"]

    return text_lower in keywords or any(keyword in text_lower for keyword in keywords)


def handle_id_request(user_id: str, line_user_id: str, reply_token: str) -> None:
    """
    ユーザーIDを返信する（デバッグ・サポート用）

    Args:
        user_id: システム内部のユーザーID
        line_user_id: LINE User ID
        reply_token: 返信トークン
    """
    message = f"""【あなたのID情報】

■ LINE User ID
{line_user_id}

■ システムユーザーID
{user_id}

※ LINE User IDはLINEアカウントを識別するためのIDです。
※ LIFFアプリ利用時の認証に使用されます。"""

    send_reply(reply_token, message)


def is_app_request(text: str) -> bool:
    """
    テキストがアプリ（LIFF）リンクリクエストかどうか判定

    Args:
        text: テキストメッセージ

    Returns:
        アプリリンクリクエストならTrue
    """
    keywords = ["アプリ", "web", "ウェブ", "webアプリ", "liff"]
    text_lower = text.lower()

    return any(keyword.lower() in text_lower for keyword in keywords)


def send_app_link(reply_token: str) -> None:
    """
    アプリ（LIFF）リンクを送信する

    Args:
        reply_token: 返信トークン
    """
    message = f"""📱 食事管理アプリ

下のリンクをタップしてアプリを開いてください：

{LIFF_URL}

※ プロフィール設定や食事履歴の確認ができます"""

    send_reply(reply_token, message)


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
    # パターン1: 「ご飯 150g」形式（食品名 + 量）
    amount_pattern = r'\d+\s*(g|グラム|ml|ミリリットル)'
    if re.search(amount_pattern, text, re.IGNORECASE):
        return True

    # パターン2: キーワードベース
    keywords = ["食べた", "朝食", "昼食", "夕食", "おやつ", "登録", "記録"]
    text_lower = text.lower()

    return any(keyword in text_lower for keyword in keywords)


def parse_food_and_amount(text: str) -> Tuple[Optional[str], Optional[float], str]:
    """
    テキストから食品名と量を抽出する

    Args:
        text: テキストメッセージ（例: "ご飯 150g", "朝食 白米200g"）

    Returns:
        (food_name, amount_g, meal_type): 食品名、量(g)、食事タイプ
    """
    # 食事タイプの判定
    meal_type = "snack"  # デフォルト
    meal_type_keywords = {
        "朝食": "breakfast",
        "朝": "breakfast",
        "昼食": "lunch",
        "昼": "lunch",
        "夕食": "dinner",
        "夜": "dinner",
        "夕": "dinner",
        "おやつ": "snack",
        "間食": "snack",
    }
    for keyword, mtype in meal_type_keywords.items():
        if keyword in text:
            meal_type = mtype
            text = text.replace(keyword, "").strip()
            break

    # 量のパターン（例: 150g, 200グラム, 100ml）
    amount_pattern = r'(\d+(?:\.\d+)?)\s*(g|グラム|ml|ミリリットル)'
    amount_match = re.search(amount_pattern, text, re.IGNORECASE)

    if not amount_match:
        return None, None, meal_type

    amount = float(amount_match.group(1))
    unit = amount_match.group(2).lower()

    # ml はそのまま g として扱う（水など）
    if unit in ['ml', 'ミリリットル']:
        amount_g = amount
    else:
        amount_g = amount

    # 食品名を抽出（量の部分を除去）
    food_name = re.sub(amount_pattern, '', text, flags=re.IGNORECASE).strip()
    # 余分なキーワードを除去
    for keyword in ["食べた", "を", "に", "登録", "記録"]:
        food_name = food_name.replace(keyword, "").strip()

    if not food_name:
        return None, None, meal_type

    return food_name, amount_g, meal_type


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
            FunctionName=DAILY_SUMMARY_FUNCTION_NAME,
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
    # テキストから食品名と量を抽出
    food_name, amount_g, meal_type = parse_food_and_amount(text)

    if not food_name or not amount_g:
        # パースできなかった場合はヘルプメッセージ
        message = """食事登録の形式が認識できませんでした。

以下の形式で送信してください：
「ご飯 150g」
「朝食 白米 200g」
「昼食 サラダ100g」

または、食品のバーコード画像を送信してください。"""
        send_reply(reply_token, message)
        return

    logger.info(f"Parsed food registration: food={food_name}, amount={amount_g}g, meal_type={meal_type}")

    try:
        # Step 1: 食品検索
        search_response = lambda_client.invoke(
            FunctionName=FOOD_SEARCH_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                "queryStringParameters": {
                    "query": food_name,
                    "limit": "5"
                }
            })
        )

        search_result = json.loads(search_response['Payload'].read())

        if search_result.get("statusCode") != 200:
            logger.error(f"Food search failed: {search_result}")
            send_reply(reply_token, f"「{food_name}」の検索中にエラーが発生しました。")
            return

        body = json.loads(search_result.get("body", "{}"))
        foods = body.get("foods", [])

        if not foods:
            send_reply(reply_token, f"「{food_name}」に該当する食品が見つかりませんでした。別の名前で試してください。")
            return

        # 最初の検索結果を使用
        food = foods[0]
        food_id = food.get("food_id")
        matched_name = food.get("name") or food.get("food_name", food_name)

        logger.info(f"Found food: id={food_id}, name={matched_name}")

        # Step 2: 食事登録
        registration_response = lambda_client.invoke(
            FunctionName=MEAL_REGISTRATION_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                "httpMethod": "POST",
                "path": "/meals",
                "body": json.dumps({
                    "user_id": line_user_id,
                    "meal_type": meal_type,
                    "foods": [
                        {
                            "food_id": food_id,
                            "amount": amount_g
                        }
                    ]
                })
            })
        )

        reg_result = json.loads(registration_response['Payload'].read())

        if reg_result.get("statusCode") in [200, 201]:
            reg_body = json.loads(reg_result.get("body", "{}"))
            total_calories = reg_body.get("total_calories", 0)
            total_protein = reg_body.get("total_protein", 0)
            total_fat = reg_body.get("total_fat", 0)
            total_carbs = reg_body.get("total_carbs", 0)

            meal_type_jp = {
                "breakfast": "朝食",
                "lunch": "昼食",
                "dinner": "夕食",
                "snack": "間食"
            }.get(meal_type, "食事")

            message = f"""✅ 食事を登録しました！

【{meal_type_jp}】{matched_name} {amount_g:.0f}g

カロリー: {total_calories:.0f} kcal
たんぱく質: {total_protein:.1f} g
脂質: {total_fat:.1f} g
炭水化物: {total_carbs:.1f} g"""

            send_reply(reply_token, message)
        else:
            logger.error(f"Meal registration failed: {reg_result}")
            send_reply(reply_token, "食事の登録中にエラーが発生しました。")

    except Exception as e:
        logger.error(f"Error in food registration: {str(e)}", exc_info=True)
        send_reply(reply_token, "食事登録中にエラーが発生しました。後ほど再度お試しください。")


def send_help_message(reply_token: str) -> None:
    """
    ヘルプメッセージを送信する

    Args:
        reply_token: 返信トークン

    要件: 11.4, 11.5
    """
    help_text = """【使い方】

■ 食事登録
以下の形式でメッセージを送信してください：
「ご飯 150g」
「朝食 白米 200g」
「昼食 サラダ 100g」

または、食品のバーコード画像を送信してください。

■ 本日の総評
「総評」または「今日のアドバイス」と送信してください。

■ アプリを開く
「アプリ」と送信してください。

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
