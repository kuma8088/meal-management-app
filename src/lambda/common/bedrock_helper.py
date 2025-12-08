"""
Bedrock統合ヘルパー（Claude 3を使用したAIアドバイス生成）

要件: なし（アドオン機能）
"""
import json
from typing import Dict, Any, Optional
import boto3
from .exceptions import ExternalServiceError
from .logger import get_logger
from .retry import exponential_backoff_retry

logger = get_logger(__name__)


class BedrockHelper:
    """Bedrock Claude APIヘルパークラス"""

    def __init__(
        self,
        region_name: str = "ap-northeast-1",
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    ):
        """
        初期化

        Args:
            region_name: AWSリージョン名
            model_id: Bedrock Claude モデルID（Haiku推奨：コスト削減）
        """
        self.region_name = region_name
        self.model_id = model_id

        # Bedrock Runtimeクライアント
        self.bedrock_runtime = boto3.client(
            "bedrock-runtime",
            region_name=region_name
        )

    @exponential_backoff_retry(max_retries=3)
    def generate_advice(
        self,
        statistics: Dict[str, Any],
        user_data: Dict[str, Any],
        max_chars: int = 300
    ) -> str:
        """
        週次統計からAIアドバイスを生成する

        Args:
            statistics: 週次統計辞書（avg_daily_calories, goal_achieved_daysなど）
            user_data: ユーザーデータ（TDEE、目標等）
            max_chars: 最大文字数（デフォルト300）

        Returns:
            AIが生成したアドバイス（日本語、max_chars以内）

        Raises:
            ExternalServiceError: Bedrock API呼び出しが失敗した場合
        """
        try:
            # プロンプトを構築
            prompt = self._build_advice_prompt(statistics, user_data, max_chars)

            logger.info(
                "Bedrockにアドバイス生成をリクエスト",
                extra={
                    "extra_data": {
                        "model_id": self.model_id,
                        "avg_calories": statistics.get("avg_daily_calories", 0)
                    }
                }
            )

            # Bedrock API呼び出し
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-06-01",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )

            # レスポンスをパース
            response_body = json.loads(response["body"].read().decode("utf-8"))

            # コンテンツを抽出
            content = response_body.get("content", [])
            if not content or not isinstance(content, list):
                raise ExternalServiceError(
                    "Bedrockレスポンスの形式が不正です",
                    details={"response": response_body}
                )

            # テキストを抽出（最初のテキストブロック）
            advice_text = ""
            for block in content:
                if block.get("type") == "text":
                    advice_text = block.get("text", "")
                    break

            if not advice_text:
                raise ExternalServiceError(
                    "Bedrockレスポンスにテキストが含まれていません",
                    details={"response": response_body}
                )

            # 文字数制限で切り詰める
            if len(advice_text) > max_chars:
                advice_text = advice_text[:max_chars].rstrip()
                # 末尾の不完全な文を除去
                if not advice_text.endswith(("。", "！", "？")):
                    advice_text = advice_text[:advice_text.rfind("。") + 1] if "。" in advice_text else advice_text

            logger.info(
                "アドバイス生成が完了しました",
                extra={
                    "extra_data": {
                        "advice_length": len(advice_text),
                        "max_chars": max_chars
                    }
                }
            )

            return advice_text

        except Exception as e:
            logger.error(
                f"Bedrockアドバイス生成に失敗しました: {str(e)}",
                exc_info=True,
                extra={
                    "extra_data": {
                        "model_id": self.model_id,
                        "error_type": type(e).__name__
                    }
                }
            )
            raise ExternalServiceError(
                "AIアドバイス生成に失敗しました",
                details={"error": str(e)}
            )

    def _build_advice_prompt(
        self,
        statistics: Dict[str, Any],
        user_data: Dict[str, Any],
        max_chars: int
    ) -> str:
        """
        アドバイス生成用プロンプトを構築

        Args:
            statistics: 週次統計
            user_data: ユーザーデータ
            max_chars: 最大文字数

        Returns:
            プロンプト文字列
        """
        avg_calories = statistics.get("avg_daily_calories", 0)
        avg_protein = statistics.get("avg_daily_protein", 0)
        goal_achieved_days = statistics.get("goal_achieved_days", 0)
        meal_count = statistics.get("meal_count", 0)
        tdee = user_data.get("tdee", 2000)
        daily_summaries = statistics.get("daily_summaries", [])

        # 日別サマリーの要約
        daily_summary_text = ""
        if daily_summaries:
            daily_summary_text = "日別データ:\n"
            for daily in daily_summaries[:3]:  # 最新3日のみ
                daily_summary_text += f"- {daily['date']}: {daily['calories']:.0f}kcal, タンパク質{daily['protein']:.1f}g\n"

        prompt = f"""あなたは栄養管理のアドバイザーです。以下のユーザーの週次食事統計をもとに、
実行可能で励ましになるアドバイスを日本語で{max_chars}文字以内で提供してください。

【ユーザーデータ】
- 目標カロリー（TDEE）: {tdee:.0f}kcal/日

【過去7日間の統計】
- 平均カロリー: {avg_calories:.0f}kcal/日
- 平均タンパク質: {avg_protein:.1f}g/日
- 目標達成日数: {goal_achieved_days}/7日
- 食事記録数: {meal_count}件

{daily_summary_text}

【条件】
- 日本語で回答してください
- {max_chars}文字以内の簡潔なアドバイスをください
- 励ましと改善提案の両方を含めてください
- 数字や専門用語は最小限にしてください
- 句点（。）で終わるようにしてください

アドバイス:"""

        return prompt
