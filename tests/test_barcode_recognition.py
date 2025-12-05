"""
バーコード認識ロジックのテスト

統合テスト
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    BarcodeRecognition,
    ValidationError,
    ExternalServiceError,
)


class TestBarcodeRecognition:
    """バーコード認識クラスの統合テスト"""

    def test_recognize_from_url_success(self):
        """URLからのバーコード認識が成功する場合"""
        image_url = "https://api-data.line.me/v2/bot/message/123/content"
        channel_access_token = "test_token"

        # モック画像データ
        mock_image_data = b"fake_image_data"

        # モックTextractレスポンス
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "4902102072557",  # 13桁のJANコード
                    "Confidence": 95.5
                }
            ]
        }

        with patch("common.barcode_recognition.requests") as mock_requests, \
             patch("common.barcode_recognition.boto3") as mock_boto3:

            # requestsモック
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.raise_for_status = Mock()
            mock_requests.get.return_value = mock_response

            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_url(
                image_url,
                channel_access_token
            )

            # 検証
            assert result is not None
            assert result["jan_code"] == "4902102072557"
            assert result["confidence"] == 95.5

            # 画像取得が呼び出されたことを確認
            mock_requests.get.assert_called_once()
            assert mock_requests.get.call_args[0][0] == image_url
            assert "Authorization" in mock_requests.get.call_args[1]["headers"]

            # Textractが呼び出されたことを確認
            mock_textract.analyze_document.assert_called_once()

    def test_recognize_from_url_no_barcode_found(self):
        """バーコードが見つからない場合"""
        image_url = "https://api-data.line.me/v2/bot/message/456/content"

        # モック画像データ
        mock_image_data = b"fake_image_data"

        # モックTextractレスポンス（バーコードなし）
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "Some text",
                    "Confidence": 90.0
                }
            ]
        }

        with patch("common.barcode_recognition.requests") as mock_requests, \
             patch("common.barcode_recognition.boto3") as mock_boto3:

            # requestsモック
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.raise_for_status = Mock()
            mock_requests.get.return_value = mock_response

            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_url(image_url)

            # 検証
            assert result is not None
            assert result["jan_code"] is None
            assert result["confidence"] == 0.0

    def test_recognize_from_url_empty_url(self):
        """空のURLでのバリデーション"""
        recognition = BarcodeRecognition()

        with pytest.raises(ValidationError):
            recognition.recognize_from_url("")

    def test_recognize_from_url_image_fetch_error(self):
        """画像取得エラーの場合"""
        image_url = "https://api-data.line.me/v2/bot/message/789/content"

        with patch("common.barcode_recognition.requests") as mock_requests:
            # requestsモック（エラー）
            mock_requests.get.side_effect = Exception("Network error")

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行してエラーが発生することを確認
            with pytest.raises(ExternalServiceError):
                recognition.recognize_from_url(image_url)

    def test_recognize_from_bytes_success(self):
        """バイトデータからのバーコード認識が成功する場合"""
        image_data = b"fake_image_data"

        # モックTextractレスポンス
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "4901780541528",  # 13桁のJANコード
                    "Confidence": 88.7
                }
            ]
        }

        with patch("common.barcode_recognition.boto3") as mock_boto3:
            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_bytes(image_data)

            # 検証
            assert result is not None
            assert result["jan_code"] == "4901780541528"
            assert result["confidence"] == 88.7

    def test_recognize_from_bytes_empty_data(self):
        """空のデータでのバリデーション"""
        recognition = BarcodeRecognition()

        with pytest.raises(ValidationError):
            recognition.recognize_from_bytes(b"")

    def test_recognize_from_bytes_textract_error(self):
        """Textract APIエラーの場合"""
        image_data = b"fake_image_data"

        with patch("common.barcode_recognition.boto3") as mock_boto3:
            # Textractモック（エラー）
            mock_textract = Mock()
            mock_textract.analyze_document.side_effect = Exception("Textract error")
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行してエラーが発生することを確認
            with pytest.raises(ExternalServiceError):
                recognition.recognize_from_bytes(image_data)

    def test_extract_barcode_8_digits(self):
        """8桁のJANコードを抽出"""
        # モックTextractレスポンス
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "12345678",  # 8桁のJANコード
                    "Confidence": 92.3
                }
            ]
        }

        with patch("common.barcode_recognition.boto3") as mock_boto3:
            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_bytes(b"fake_image_data")

            # 検証
            assert result["jan_code"] == "12345678"
            assert result["confidence"] == 92.3

    def test_extract_barcode_12_digits(self):
        """12桁のJANコードを抽出"""
        # モックTextractレスポンス
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "490123456789",  # 12桁のJANコード
                    "Confidence": 89.1
                }
            ]
        }

        with patch("common.barcode_recognition.boto3") as mock_boto3:
            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_bytes(b"fake_image_data")

            # 検証
            assert result["jan_code"] == "490123456789"
            assert result["confidence"] == 89.1

    def test_extract_barcode_low_confidence(self):
        """信頼度が低いバーコードは除外される"""
        # モックTextractレスポンス（信頼度が閾値未満）
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "4901234567890",  # 13桁のJANコード
                    "Confidence": 65.0  # MIN_CONFIDENCE (70.0) 未満
                }
            ]
        }

        with patch("common.barcode_recognition.boto3") as mock_boto3:
            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_bytes(b"fake_image_data")

            # 検証：信頼度が低いため、バーコードなしとして扱われる
            assert result["jan_code"] is None
            assert result["confidence"] == 0.0

    def test_extract_barcode_multiple_candidates(self):
        """複数の候補がある場合、最も信頼度の高いものを選択"""
        # モックTextractレスポンス
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "4901234567890",  # 13桁のJANコード
                    "Confidence": 85.5
                },
                {
                    "BlockType": "LINE",
                    "Text": "4902102072557",  # 13桁のJANコード
                    "Confidence": 92.3  # より高い信頼度
                },
                {
                    "BlockType": "LINE",
                    "Text": "Some text",
                    "Confidence": 90.0
                }
            ]
        }

        with patch("common.barcode_recognition.boto3") as mock_boto3:
            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_bytes(b"fake_image_data")

            # 検証：最も信頼度の高いJANコードが選択される
            assert result["jan_code"] == "4902102072557"
            assert result["confidence"] == 92.3

    def test_extract_barcode_invalid_length(self):
        """無効な桁数のコードは除外される"""
        # モックTextractレスポンス
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "123",  # 3桁（無効）
                    "Confidence": 95.0
                },
                {
                    "BlockType": "LINE",
                    "Text": "12345678901234567",  # 17桁（無効）
                    "Confidence": 90.0
                }
            ]
        }

        with patch("common.barcode_recognition.boto3") as mock_boto3:
            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_bytes(b"fake_image_data")

            # 検証：有効な桁数のJANコードがないため、Noneが返される
            assert result["jan_code"] is None
            assert result["confidence"] == 0.0

    def test_recognize_from_url_with_token(self):
        """LINE Channel Access Tokenありで画像を取得"""
        image_url = "https://api-data.line.me/v2/bot/message/123/content"
        channel_access_token = "test_channel_token"

        # モック画像データ
        mock_image_data = b"fake_image_data"

        # モックTextractレスポンス
        mock_textract_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "4901234567890",
                    "Confidence": 90.0
                }
            ]
        }

        with patch("common.barcode_recognition.requests") as mock_requests, \
             patch("common.barcode_recognition.boto3") as mock_boto3:

            # requestsモック
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.raise_for_status = Mock()
            mock_requests.get.return_value = mock_response

            # Textractモック
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = mock_textract_response
            mock_boto3.client.return_value = mock_textract

            # BarcodeRecognitionインスタンスを作成
            recognition = BarcodeRecognition()

            # バーコード認識を実行
            result = recognition.recognize_from_url(
                image_url,
                channel_access_token
            )

            # 検証
            assert result["jan_code"] == "4901234567890"

            # Authorizationヘッダーが設定されていることを確認
            call_kwargs = mock_requests.get.call_args[1]
            assert "headers" in call_kwargs
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == f"Bearer {channel_access_token}"
