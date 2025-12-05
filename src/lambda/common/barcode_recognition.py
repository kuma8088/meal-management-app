"""
バーコード認識ロジック

要件: 5.1, 5.2, 5.3
"""
import boto3
import requests
from typing import Optional, Dict
from .exceptions import ValidationError, ExternalServiceError
from .logger import get_logger
from .retry import exponential_backoff_retry

logger = get_logger(__name__)


class BarcodeRecognition:
    """バーコード認識クラス（Amazon Textract使用）"""

    # 最小信頼度スコア（これ以下のスコアの結果は信頼できないと判断）
    MIN_CONFIDENCE = 70.0

    def __init__(self, region_name: str = "ap-northeast-1"):
        """
        初期化

        Args:
            region_name: AWSリージョン名
        """
        self.textract = boto3.client("textract", region_name=region_name)
        self.region_name = region_name

    def recognize_from_url(
        self,
        image_url: str,
        line_channel_access_token: Optional[str] = None
    ) -> Dict[str, any]:
        """
        画像URLからJANコードを認識する

        Args:
            image_url: 画像のURL（LINE Content API URL）
            line_channel_access_token: LINE Channel Access Token

        Returns:
            認識結果の辞書:
            {
                "jan_code": str | None,
                "confidence": float
            }

        Raises:
            ValidationError: URLが無効な場合
            ExternalServiceError: 画像取得またはTextract API呼び出しが失敗した場合

        要件: 5.1, 5.2, 5.3
        """
        # バリデーション
        if not image_url or not image_url.strip():
            raise ValidationError(
                "画像URLは必須です",
                details={"image_url": image_url}
            )

        logger.info(
            f"バーコード認識を開始: {image_url}",
            extra={
                "extra_data": {
                    "image_url": image_url
                }
            }
        )

        try:
            # ステップ1: LINE Content APIから画像を取得
            image_data = self._fetch_image_from_line(
                image_url,
                line_channel_access_token
            )

            # ステップ2: Textractでバーコードを認識
            jan_code, confidence = self._recognize_barcode_with_textract(image_data)

            result = {
                "jan_code": jan_code,
                "confidence": confidence
            }

            if jan_code:
                logger.info(
                    f"バーコード認識成功: {jan_code} (信頼度: {confidence}%)",
                    extra={
                        "extra_data": {
                            "jan_code": jan_code,
                            "confidence": confidence
                        }
                    }
                )
            else:
                logger.info(
                    "バーコードが見つかりませんでした",
                    extra={
                        "extra_data": {
                            "confidence": confidence
                        }
                    }
                )

            return result

        except Exception as e:
            logger.error(
                f"バーコード認識でエラーが発生しました: {e}",
                extra={
                    "extra_data": {
                        "image_url": image_url,
                        "error": str(e)
                    }
                }
            )
            raise ExternalServiceError(
                "バーコード認識に失敗しました",
                details={"image_url": image_url, "error": str(e)}
            )

    def recognize_from_bytes(self, image_data: bytes) -> Dict[str, any]:
        """
        画像バイトデータからJANコードを認識する

        Args:
            image_data: 画像のバイトデータ

        Returns:
            認識結果の辞書:
            {
                "jan_code": str | None,
                "confidence": float
            }

        Raises:
            ValidationError: 画像データが無効な場合
            ExternalServiceError: Textract API呼び出しが失敗した場合

        要件: 5.2, 5.3
        """
        # バリデーション
        if not image_data:
            raise ValidationError(
                "画像データは必須です",
                details={"image_data_size": 0}
            )

        logger.info(
            f"バーコード認識を開始: {len(image_data)}バイト",
            extra={
                "extra_data": {
                    "image_size": len(image_data)
                }
            }
        )

        try:
            # Textractでバーコードを認識
            jan_code, confidence = self._recognize_barcode_with_textract(image_data)

            result = {
                "jan_code": jan_code,
                "confidence": confidence
            }

            if jan_code:
                logger.info(
                    f"バーコード認識成功: {jan_code} (信頼度: {confidence}%)",
                    extra={
                        "extra_data": {
                            "jan_code": jan_code,
                            "confidence": confidence
                        }
                    }
                )
            else:
                logger.info(
                    "バーコードが見つかりませんでした",
                    extra={
                        "extra_data": {
                            "confidence": confidence
                        }
                    }
                )

            return result

        except Exception as e:
            logger.error(
                f"バーコード認識でエラーが発生しました: {e}",
                extra={
                    "extra_data": {
                        "error": str(e)
                    }
                }
            )
            raise ExternalServiceError(
                "バーコード認識に失敗しました",
                details={"error": str(e)}
            )

    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(ExternalServiceError,)
    )
    def _fetch_image_from_line(
        self,
        image_url: str,
        channel_access_token: Optional[str]
    ) -> bytes:
        """
        LINE Content APIから画像を取得する

        Args:
            image_url: 画像のURL
            channel_access_token: LINE Channel Access Token

        Returns:
            画像のバイトデータ

        Raises:
            ExternalServiceError: 画像取得が失敗した場合

        要件: 5.1
        """
        try:
            headers = {}
            if channel_access_token:
                headers["Authorization"] = f"Bearer {channel_access_token}"

            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()

            logger.info(
                f"画像取得成功: {len(response.content)}バイト",
                extra={
                    "extra_data": {
                        "image_url": image_url,
                        "size": len(response.content)
                    }
                }
            )

            return response.content

        except requests.RequestException as e:
            logger.error(
                f"画像取得に失敗しました: {e}",
                extra={
                    "extra_data": {
                        "image_url": image_url,
                        "error": str(e)
                    }
                }
            )
            raise ExternalServiceError(
                "画像取得に失敗しました",
                details={"image_url": image_url, "error": str(e)}
            )

    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(ExternalServiceError,)
    )
    def _recognize_barcode_with_textract(
        self,
        image_data: bytes
    ) -> tuple[Optional[str], float]:
        """
        Textractを使ってバーコードを認識する

        Args:
            image_data: 画像のバイトデータ

        Returns:
            (JANコード, 信頼度スコア) のタプル
            JANコードが見つからない場合は (None, 0.0)

        Raises:
            ExternalServiceError: Textract API呼び出しが失敗した場合

        要件: 5.2, 5.3
        """
        try:
            # Textract APIを呼び出し
            response = self.textract.analyze_document(
                Document={"Bytes": image_data},
                FeatureTypes=["FORMS"]  # バーコード検出にはFORMS機能を使用
            )

            # バーコードを検索
            jan_code, confidence = self._extract_barcode_from_response(response)

            return jan_code, confidence

        except Exception as e:
            logger.error(
                f"Textract API呼び出しに失敗しました: {e}",
                extra={
                    "extra_data": {
                        "error": str(e)
                    }
                }
            )
            raise ExternalServiceError(
                "バーコード認識APIの呼び出しに失敗しました",
                details={"error": str(e)}
            )

    def _extract_barcode_from_response(
        self,
        response: Dict
    ) -> tuple[Optional[str], float]:
        """
        Textractのレスポンスからバーコードを抽出する

        Args:
            response: Textract APIのレスポンス

        Returns:
            (JANコード, 信頼度スコア) のタプル

        要件: 5.2, 5.3
        """
        # Blocksから数値のみのテキストを検索（JANコードは数字のみ）
        blocks = response.get("Blocks", [])

        best_candidate = None
        best_confidence = 0.0

        for block in blocks:
            if block.get("BlockType") == "LINE":
                text = block.get("Text", "")
                confidence = block.get("Confidence", 0.0)

                # JANコードは数字のみで8桁、12桁、13桁、または14桁
                if text.isdigit() and len(text) in [8, 12, 13, 14]:
                    # 信頼度が最小閾値以上で、これまでの候補より高い場合
                    if confidence >= self.MIN_CONFIDENCE and confidence > best_confidence:
                        best_candidate = text
                        best_confidence = confidence

        return best_candidate, best_confidence
