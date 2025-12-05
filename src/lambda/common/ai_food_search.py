"""
AI食品検索ロジック

要件: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import boto3
from .models import Food, FoodSource
from .dynamodb_helper import DynamoDBHelper
from .s3_helper import S3Helper
from .food_search import FoodSearch
from .exceptions import ValidationError, ExternalServiceError
from .logger import get_logger
from .retry import exponential_backoff_retry

logger = get_logger(__name__)


class AIFoodSearch:
    """AI食品検索クラス（Bedrock Claude使用）"""

    def __init__(
        self,
        foods_table_name: str = "Foods",
        s3_bucket_name: str = "meal-management-food-master",
        s3_csv_key: str = "food_master.csv",
        region_name: str = "ap-northeast-1",
        bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    ):
        """
        初期化

        Args:
            foods_table_name: Foodsテーブル名
            s3_bucket_name: 食品マスタCSVが保存されているS3バケット名
            s3_csv_key: 食品マスタCSVのS3キー
            region_name: AWSリージョン名
            bedrock_model_id: Bedrock Claude モデルID
        """
        self.food_search = FoodSearch(foods_table_name, region_name)
        self.db_helper = DynamoDBHelper(foods_table_name, region_name)
        self.s3_helper = S3Helper(s3_bucket_name, region_name)
        self.s3_bucket_name = s3_bucket_name
        self.s3_csv_key = s3_csv_key
        self.bedrock_model_id = bedrock_model_id

        # Bedrock Runtimeクライアント
        self.bedrock_runtime = boto3.client(
            "bedrock-runtime",
            region_name=region_name
        )

    def search_with_ai(self, query: str, save_to_cache: bool = True) -> Optional[Food]:
        """
        AI検索を使って食品を検索する

        このメソッドは以下の流れで動作します:
        1. まずDynamoDBキャッシュを確認
        2. キャッシュがなければBedrock Claudeを使ってS3のCSVを検索
        3. 見つかった場合、AI_GENERATEDフラグ付きでDynamoDBに保存
        4. 次回同じ検索があった場合はキャッシュから返す

        Args:
            query: 検索クエリ（食品名）
            save_to_cache: DynamoDBにキャッシュとして保存するか

        Returns:
            検索結果の食品（見つからない場合はNone）

        Raises:
            ValidationError: クエリが無効な場合
            ExternalServiceError: Bedrock API呼び出しが失敗した場合

        要件: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
        """
        # バリデーション
        if not query or not query.strip():
            raise ValidationError(
                "検索クエリは必須です",
                details={"query": query}
            )

        query = query.strip()

        # ステップ1: DynamoDBキャッシュを確認（Property 6: キャッシング）
        cached_results = self.food_search.search_by_name(query, limit=10)
        ai_generated_foods = [
            food for food in cached_results
            if food.source == FoodSource.AI_GENERATED and food.name.lower() == query.lower()
        ]

        if ai_generated_foods:
            logger.info(
                f"AI検索結果のキャッシュが見つかりました: {query}",
                extra={
                    "extra_data": {
                        "query": query,
                        "food_id": ai_generated_foods[0].food_id,
                        "cached": True
                    }
                }
            )
            return ai_generated_foods[0]

        # ステップ2: Bedrock Claudeを使ってS3のCSVを検索
        logger.info(
            f"AI検索を実行します: {query}",
            extra={
                "extra_data": {
                    "query": query,
                    "s3_bucket": self.s3_bucket_name,
                    "s3_key": self.s3_csv_key
                }
            }
        )

        try:
            # S3からCSVデータを取得
            csv_content = self.s3_helper.get_object(self.s3_csv_key)

            # Bedrock APIを呼び出して食品を検索
            food_data = self._search_with_bedrock(query, csv_content)

            if not food_data:
                logger.info(
                    f"AI検索で食品が見つかりませんでした: {query}",
                    extra={
                        "extra_data": {
                            "query": query
                        }
                    }
                )
                return None

            # ステップ3: AI_GENERATEDフラグ付きでDynamoDBに保存（Property 5: AIマーキング）
            now = datetime.now()
            food = Food(
                food_id=str(uuid.uuid4()),
                name=food_data["name"],
                calories_per_100g=food_data["calories_per_100g"],
                protein_per_100g=food_data["protein_per_100g"],
                fat_per_100g=food_data["fat_per_100g"],
                carbs_per_100g=food_data["carbs_per_100g"],
                jan_code=food_data.get("jan_code"),
                source=FoodSource.AI_GENERATED,  # Property 5: AI_GENERATEDフラグ
                created_at=now,
                updated_at=now
            )

            if save_to_cache:
                # DynamoDBに保存してキャッシュ
                self.db_helper.put_item(food.to_dict())

                logger.info(
                    f"AI検索結果をキャッシュに保存しました: {query} -> {food.name}",
                    extra={
                        "extra_data": {
                            "query": query,
                            "food_id": food.food_id,
                            "food_name": food.name,
                            "source": "AI_GENERATED"
                        }
                    }
                )

            return food

        except Exception as e:
            logger.error(
                f"AI検索でエラーが発生しました: {query}",
                extra={
                    "extra_data": {
                        "query": query,
                        "error": str(e)
                    }
                }
            )
            raise ExternalServiceError(
                "AI検索に失敗しました",
                details={"query": query, "error": str(e)}
            )

    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(ExternalServiceError,)
    )
    def _search_with_bedrock(
        self,
        query: str,
        csv_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Bedrock Claudeを使ってCSVから食品を検索する

        Args:
            query: 検索クエリ
            csv_content: 食品マスタCSVの内容

        Returns:
            食品データの辞書（見つからない場合はNone）

        Raises:
            ExternalServiceError: Bedrock API呼び出しが失敗した場合
        """
        # Bedrockへのプロンプト
        prompt = f"""以下のCSVデータから、「{query}」という食品を検索してください。

CSVデータ（最初の100行のみ表示）:
{self._truncate_csv(csv_content, max_lines=100)}

指示:
1. 「{query}」に最も近い食品を1つ見つけてください
2. 見つかった場合、以下のJSON形式で応答してください:
{{
    "name": "食品名",
    "calories_per_100g": カロリー(数値),
    "protein_per_100g": タンパク質(数値),
    "fat_per_100g": 脂質(数値),
    "carbs_per_100g": 炭水化物(数値),
    "jan_code": "JANコード（あれば）"
}}

3. 見つからない場合は、以下のJSON形式で応答してください:
{{"found": false}}

重要: JSON以外のテキストは含めず、JSONのみを返してください。
"""

        try:
            # Bedrock APIを呼び出し
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(request_body)
            )

            # レスポンスをパース
            response_body = json.loads(response["body"].read())

            # Claudeの応答からJSONを抽出
            content = response_body["content"][0]["text"]

            # JSONをパース
            result = json.loads(content.strip())

            if result.get("found") is False:
                return None

            # 必須フィールドの検証
            required_fields = ["name", "calories_per_100g", "protein_per_100g", "fat_per_100g", "carbs_per_100g"]
            if not all(field in result for field in required_fields):
                logger.warning(
                    f"Bedrock応答に必須フィールドが不足: {result}",
                    extra={
                        "extra_data": {
                            "result": result,
                            "required_fields": required_fields
                        }
                    }
                )
                return None

            return result

        except json.JSONDecodeError as e:
            logger.error(
                f"Bedrock応答のJSONパースに失敗: {e}",
                extra={
                    "extra_data": {
                        "error": str(e)
                    }
                }
            )
            raise ExternalServiceError(
                "AI検索の応答パースに失敗しました",
                details={"error": str(e)}
            )

        except Exception as e:
            logger.error(
                f"Bedrock API呼び出しに失敗: {e}",
                extra={
                    "extra_data": {
                        "error": str(e)
                    }
                }
            )
            raise ExternalServiceError(
                "AI検索APIの呼び出しに失敗しました",
                details={"error": str(e)}
            )

    def _truncate_csv(self, csv_content: str, max_lines: int = 100) -> str:
        """
        CSVを指定行数に切り詰める

        Args:
            csv_content: CSVの内容
            max_lines: 最大行数

        Returns:
            切り詰められたCSV
        """
        lines = csv_content.split("\n")
        if len(lines) <= max_lines:
            return csv_content

        return "\n".join(lines[:max_lines]) + f"\n... (残り{len(lines) - max_lines}行)"
