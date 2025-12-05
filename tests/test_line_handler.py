"""
LINE Webhook Handlerのテスト

Feature: meal-management-app, Task 17.1
"""
import pytest
import json
import hmac
import hashlib
import base64
from unittest.mock import MagicMock, patch, ANY
from datetime import date

# テスト対象
import sys
import os
from pathlib import Path

# src/lambda/commonとline_handlerをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "line_handler"))

from line_handler import lambda_handler


class TestLINEWebhookHandler:
    """LINE Webhook Handler integration tests"""

    @pytest.fixture
    def mock_lambda_client(self):
        """Lambda client mock"""
        with patch('line_handler.lambda_client') as mock:
            yield mock

    @pytest.fixture
    def valid_signature_event(self):
        """有効な署名を持つイベントを生成"""
        secret = "test_channel_secret"
        body = json.dumps({
            "events": [
                {
                    "type": "message",
                    "replyToken": "test_reply_token",
                    "source": {
                        "userId": "test_user_123"
                    },
                    "message": {
                        "type": "text",
                        "text": "こんにちは"
                    }
                }
            ]
        })

        # 署名を計算
        signature = base64.b64encode(
            hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        return {
            "headers": {
                "x-line-signature": signature
            },
            "body": body
        }

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    @patch('line_handler.send_reply')
    def test_signature_verification_success(self, mock_send_reply, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: 署名検証が成功する
        """
        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "OK"

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    def test_signature_verification_failure(self):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: 署名検証が失敗する
        """
        event = {
            "headers": {
                "x-line-signature": "invalid_signature"
            },
            "body": json.dumps({
                "events": []
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 403

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    @patch('line_handler.send_reply')
    def test_help_message(self, mock_send_reply, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: 不明なメッセージにヘルプを返信
        要件: 11.4
        """
        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200
        mock_send_reply.assert_called_once()

        # ヘルプメッセージの内容を確認
        call_args = mock_send_reply.call_args[0]
        reply_token = call_args[0]
        message = call_args[1]

        assert reply_token == "test_reply_token"
        assert "使い方" in message
        assert "食事登録" in message
        assert "総評" in message

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    @patch('line_handler.send_reply')
    @patch('line_handler.lambda_client')
    def test_daily_advice_request(self, mock_lambda_client, mock_send_reply, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: 総評リクエストの処理
        要件: 11.3
        """
        # イベントを総評リクエストに変更
        body = json.loads(valid_signature_event["body"])
        body["events"][0]["message"]["text"] = "今日の総評を教えて"
        valid_signature_event["body"] = json.dumps(body)

        # 署名を再計算
        signature = base64.b64encode(
            hmac.new(
                b"test_channel_secret",
                json.dumps(body).encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")
        valid_signature_event["headers"]["x-line-signature"] = signature

        # daily_summaryのレスポンスをモック
        mock_lambda_client.invoke.return_value = {
            "Payload": MagicMock(read=lambda: json.dumps({
                "statusCode": 200,
                "body": json.dumps({
                    "advice": "素晴らしい食事バランスです。",
                    "total_calories": 2000.0,
                    "target_calories": 2000.0,
                    "usage_limit_reached": False
                })
            }).encode())
        }

        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200

        # Lambda関数が呼ばれたことを確認
        mock_lambda_client.invoke.assert_called_once()

        # 返信が送られたことを確認
        mock_send_reply.assert_called_once()
        call_args = mock_send_reply.call_args[0]
        message = call_args[1]

        assert "本日の総評" in message
        assert "素晴らしい食事バランスです" in message
        assert "2000" in message

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    @patch('line_handler.send_reply')
    @patch('line_handler.lambda_client')
    def test_daily_advice_usage_limit(self, mock_lambda_client, mock_send_reply, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: 総評リクエストの利用制限
        要件: 11.3, 10.2
        """
        # イベントを総評リクエストに変更
        body = json.loads(valid_signature_event["body"])
        body["events"][0]["message"]["text"] = "総評"
        valid_signature_event["body"] = json.dumps(body)

        # 署名を再計算
        signature = base64.b64encode(
            hmac.new(
                b"test_channel_secret",
                json.dumps(body).encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")
        valid_signature_event["headers"]["x-line-signature"] = signature

        # daily_summaryのレスポンス（利用制限）
        mock_lambda_client.invoke.return_value = {
            "Payload": MagicMock(read=lambda: json.dumps({
                "statusCode": 200,
                "body": json.dumps({
                    "message": "本日のアドバイス生成は2回までです",
                    "usage_limit_reached": True,
                    "usage_count": 2,
                    "max_usage": 2
                })
            }).encode())
        }

        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200

        # 返信が送られたことを確認
        mock_send_reply.assert_called_once()
        call_args = mock_send_reply.call_args[0]
        message = call_args[1]

        assert "2回まで" in message

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    @patch('line_handler.send_reply')
    def test_food_registration_request(self, mock_send_reply, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: 食事登録リクエストの処理
        要件: 11.2
        """
        # イベントを食事登録リクエストに変更
        body = json.loads(valid_signature_event["body"])
        body["events"][0]["message"]["text"] = "朝食にご飯200gを食べた"
        valid_signature_event["body"] = json.dumps(body)

        # 署名を再計算
        signature = base64.b64encode(
            hmac.new(
                b"test_channel_secret",
                json.dumps(body).encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")
        valid_signature_event["headers"]["x-line-signature"] = signature

        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200

        # 返信が送られたことを確認（現在は準備中メッセージ）
        mock_send_reply.assert_called_once()
        call_args = mock_send_reply.call_args[0]
        message = call_args[1]

        assert "食事登録" in message or "準備中" in message

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    @patch('line_handler.send_reply')
    @patch('line_handler.BarcodeRecognition')
    @patch('line_handler.lambda_client')
    def test_image_message(self, mock_lambda_client, mock_barcode_class, mock_send_reply, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: 画像メッセージの処理
        """
        # BarcodeRecognitionのモックを設定
        mock_barcode_instance = mock_barcode_class.return_value
        mock_barcode_instance.recognize_from_url.return_value = {
            "jan_code": "4901234567890",
            "confidence": 0.95
        }

        # Lambda invocationのモック設定
        from io import BytesIO
        payload_data = json.dumps({
            "statusCode": 200,
            "body": json.dumps({
                "foods": [{
                    "food_id": "test_food_123",
                    "name": "テスト食品",
                    "calories_per_100g": 100,
                    "protein_per_100g": 5,
                    "fat_per_100g": 2,
                    "carbs_per_100g": 15
                }]
            })
        }).encode()

        mock_lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": BytesIO(payload_data)
        }

        # イベントを画像メッセージに変更
        body = json.loads(valid_signature_event["body"])
        body["events"][0]["message"] = {
            "type": "image",
            "id": "test_message_id_123"
        }
        valid_signature_event["body"] = json.dumps(body)

        # 署名を再計算
        signature = base64.b64encode(
            hmac.new(
                b"test_channel_secret",
                json.dumps(body).encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")
        valid_signature_event["headers"]["x-line-signature"] = signature

        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200

        # 返信が送られたことを確認
        mock_send_reply.assert_called_once()
        call_args = mock_send_reply.call_args[0]
        message = call_args[1]

        # 正常にバーコードが認識され、食品情報が返されたことを確認
        assert "テスト食品" in message or "カロリー" in message

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    def test_no_events(self, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: イベントがない場合
        """
        # イベントを空にする
        body = {"events": []}
        valid_signature_event["body"] = json.dumps(body)

        # 署名を再計算
        signature = base64.b64encode(
            hmac.new(
                b"test_channel_secret",
                json.dumps(body).encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")
        valid_signature_event["headers"]["x-line-signature"] = signature

        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "No events"

    @pytest.mark.integration
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_channel_secret')
    def test_non_message_event(self, valid_signature_event):
        """
        Feature: meal-management-app, Task 17.1
        統合テスト: メッセージ以外のイベント
        """
        # イベントをフォローイベントに変更
        body = json.loads(valid_signature_event["body"])
        body["events"][0]["type"] = "follow"
        valid_signature_event["body"] = json.dumps(body)

        # 署名を再計算
        signature = base64.b64encode(
            hmac.new(
                b"test_channel_secret",
                json.dumps(body).encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")
        valid_signature_event["headers"]["x-line-signature"] = signature

        response = lambda_handler(valid_signature_event, None)

        assert response["statusCode"] == 200


class TestMessageIntentDetection:
    """メッセージ意図判定のテスト"""

    @pytest.mark.unit
    def test_is_daily_advice_request(self):
        """総評リクエストの判定"""
        from line_handler import is_daily_advice_request

        assert is_daily_advice_request("今日の総評を教えて") is True
        assert is_daily_advice_request("総評") is True
        assert is_daily_advice_request("アドバイスください") is True
        assert is_daily_advice_request("今日のまとめ") is True
        assert is_daily_advice_request("こんにちは") is False
        assert is_daily_advice_request("朝食にご飯を食べた") is False

    @pytest.mark.unit
    def test_is_food_registration_request(self):
        """食事登録リクエストの判定"""
        from line_handler import is_food_registration_request

        assert is_food_registration_request("朝食にご飯200gを食べた") is True
        assert is_food_registration_request("昼食を登録") is True
        assert is_food_registration_request("夕食を記録したい") is True
        assert is_food_registration_request("おやつを食べた") is True
        assert is_food_registration_request("こんにちは") is False
        assert is_food_registration_request("総評を教えて") is False


class TestSignatureVerification:
    """署名検証のユニットテスト"""

    @pytest.mark.unit
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_secret')
    def test_verify_signature_valid(self):
        """有効な署名の検証"""
        from line_handler import verify_signature

        body = json.dumps({"events": []})
        signature = base64.b64encode(
            hmac.new(b"test_secret", body.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        event = {
            "headers": {"x-line-signature": signature},
            "body": body
        }

        assert verify_signature(event) is True

    @pytest.mark.unit
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_secret')
    def test_verify_signature_invalid(self):
        """無効な署名の検証"""
        from line_handler import verify_signature

        event = {
            "headers": {"x-line-signature": "invalid_signature"},
            "body": json.dumps({"events": []})
        }

        assert verify_signature(event) is False

    @pytest.mark.unit
    @patch('line_handler.LINE_CHANNEL_SECRET', 'test_secret')
    def test_verify_signature_missing(self):
        """署名が欠けている場合"""
        from line_handler import verify_signature

        event = {
            "headers": {},
            "body": json.dumps({"events": []})
        }

        assert verify_signature(event) is False
