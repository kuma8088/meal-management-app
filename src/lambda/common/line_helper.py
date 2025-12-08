"""
LINE Messaging API統合ヘルパー

要件: なし（アドオン機能）
"""
import json
from typing import Dict, Any, Optional
import requests
from .exceptions import ExternalServiceError
from .logger import get_logger
from .retry import exponential_backoff_retry

logger = get_logger(__name__)


class LINEHelper:
    """LINE Messaging APIヘルパークラス"""

    PUSH_MESSAGE_URL = "https://api.line.me/v2/bot/message/push"

    def __init__(self, channel_access_token: str):
        """
        初期化

        Args:
            channel_access_token: LINE Channel Access Token
        """
        self.channel_access_token = channel_access_token

    @exponential_backoff_retry(max_retries=3)
    def push_message(
        self,
        user_id: str,
        text: str,
        quick_reply_items: Optional[list] = None
    ) -> bool:
        """
        ユーザーにテキストメッセージをPush送信

        Args:
            user_id: LINE User ID（Cognito user_id または LINE user_id）
            text: メッセージテキスト
            quick_reply_items: クイックリプライアイテム（オプション）

        Returns:
            送信成功時True

        Raises:
            ExternalServiceError: API呼び出しが失敗した場合
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.channel_access_token}"
            }

            body = {
                "to": user_id,
                "messages": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }

            # クイックリプライを追加（オプション）
            if quick_reply_items:
                body["messages"][0]["quickReply"] = {
                    "items": quick_reply_items
                }

            logger.info(
                f"LINEメッセージ送信: user_id={user_id}, text_length={len(text)}",
                extra={
                    "extra_data": {
                        "user_id": user_id,
                        "text_length": len(text),
                        "has_quick_reply": bool(quick_reply_items)
                    }
                }
            )

            response = requests.post(
                self.PUSH_MESSAGE_URL,
                headers=headers,
                json=body,
                timeout=10
            )

            # ステータスコード確認
            if response.status_code not in [200, 201]:
                error_message = response.text
                logger.error(
                    f"LINE Push Message API エラー: status={response.status_code}, message={error_message}",
                    extra={
                        "extra_data": {
                            "user_id": user_id,
                            "status_code": response.status_code,
                            "error_message": error_message
                        }
                    }
                )
                raise ExternalServiceError(
                    f"LINE Push Message API エラー: {response.status_code}",
                    details={
                        "status_code": response.status_code,
                        "error": error_message
                    }
                )

            logger.info(
                f"LINEメッセージ送信完了: user_id={user_id}",
                extra={"extra_data": {"user_id": user_id}}
            )

            return True

        except requests.RequestException as e:
            logger.error(
                f"LINE Push Message 送信に失敗しました: {str(e)}",
                exc_info=True,
                extra={"extra_data": {"user_id": user_id}}
            )
            raise ExternalServiceError(
                "LINE Push Message 送信に失敗しました",
                details={"error": str(e)}
            )

    def push_weekly_report(
        self,
        user_id: str,
        user_name: Optional[str],
        statistics: Dict[str, Any],
        advice: str
    ) -> bool:
        """
        週次レポートメッセージを送信

        Args:
            user_id: LINE User ID
            user_name: ユーザー名（オプション）
            statistics: 週次統計辞書
            advice: AIアドバイス

        Returns:
            送信成功時True

        Raises:
            ExternalServiceError: API呼び出しが失敗した場合
        """
        try:
            # メッセージを構築
            greeting = f"{user_name}さんへの" if user_name else ""
            avg_calories = statistics.get("avg_daily_calories", 0)
            goal_achieved_days = statistics.get("goal_achieved_days", 0)

            message = f"""📊 {greeting}週次レポート

平均カロリー: {avg_calories:.0f}kcal/日
目標達成日数: {goal_achieved_days}/7日

💡 アドバイス:
{advice}

来週も頑張ってください！"""

            return self.push_message(user_id, message)

        except Exception as e:
            logger.error(
                f"週次レポート送信に失敗しました: {str(e)}",
                exc_info=True,
                extra={"extra_data": {"user_id": user_id}}
            )
            raise ExternalServiceError(
                "週次レポート送信に失敗しました",
                details={"error": str(e)}
            )
