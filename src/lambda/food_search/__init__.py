"""
食品検索 Lambda 関数

DynamoDB の Foods テーブルから食品を検索する。
食品名または JAN コードで検索可能。

要件: 2.4
"""
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from decimal import Decimal

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from common import (
    DynamoDBHelper,
    get_logger,
    success_response,
    error_response,
    ValidationError,
)

logger = get_logger(__name__)


class FoodSearchHandler:
    """食品検索ハンドラー"""

    def __init__(self):
        """初期化"""
        self.dynamodb = DynamoDBHelper(
            table_name=os.environ.get('FOODS_TABLE', 'meal-management-app-foods-dev')
        )

    def search_by_name(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        食品名で検索

        Args:
            query: 検索クエリ（食品名）
            limit: 最大結果数

        Returns:
            検索結果のリスト
        """
        try:
            # DynamoDB検索（部分一致）
            items = self.dynamodb.scan(
                filter_expression='contains(food_name, :query)',
                expression_attribute_values={
                    ':query': query
                },
                limit=limit
            )

            return [self._convert_item(item) for item in items]

        except Exception as e:
            logger.error(f"食品名検索エラー: {str(e)}", exc_info=True)
            raise

    def search_by_jan_code(self, jan_code: str) -> List[Dict[str, Any]]:
        """
        JAN コードで検索

        Args:
            jan_code: JAN コード

        Returns:
            検索結果のリスト
        """
        try:
            # DynamoDB検索（GSI使用）
            items = self.dynamodb.query(
                index_name='jan_code-index',
                key_condition_expression='jan_code = :jan_code',
                expression_attribute_values={
                    ':jan_code': jan_code
                }
            )

            return [self._convert_item(item) for item in items]

        except Exception as e:
            logger.error(f"JAN コード検索エラー: {str(e)}", exc_info=True)
            raise

    def _convert_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        DynamoDB アイテムを API レスポンス形式に変換

        Args:
            item: DynamoDB アイテム

        Returns:
            変換済みアイテム
        """
        return {
            'food_id': item.get('food_id'),
            'name': item.get('food_name'),
            'calories_per_100g': float(item.get('calories', 0)),
            'protein_per_100g': float(item.get('protein', 0)),
            'fat_per_100g': float(item.get('fat', 0)),
            'carbs_per_100g': float(item.get('carbs', 0)),
            'jan_code': item.get('jan_code'),
            'source': item.get('source'),
            'brands': item.get('brands'),
            'categories': item.get('categories'),
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda ハンドラー

    期待されるイベント:
    {
        "query": str,           # 食品名または JAN コード
        "search_type": str,     # "name" | "jan_code"
        "limit": int            # 最大結果数（オプション、デフォルト20）
    }

    レスポンス:
    {
        "foods": [
            {
                "food_id": str,
                "name": str,
                "calories_per_100g": float,
                "protein_per_100g": float,
                "fat_per_100g": float,
                "carbs_per_100g": float,
                "jan_code": str | None,
                "source": str
            }
        ]
    }
    """
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'

    logger.info(f"Food search handler invoked: {event}")

    try:
        # パラメータ取得（API Gateway or 直接呼び出し対応）
        query_params = event.get('queryStringParameters') or {}
        query = query_params.get('query') or event.get('query')
        search_type = query_params.get('search_type') or event.get('search_type', 'name')
        limit = int(query_params.get('limit') or event.get('limit', 20))

        # バリデーション
        if not query:
            return error_response(
                "query is required",
                request_id=request_id,
                status_code=400
            )

        if search_type not in ['name', 'jan_code']:
            return error_response(
                "search_type must be 'name' or 'jan_code'",
                request_id=request_id,
                status_code=400
            )

        # 検索実行
        handler = FoodSearchHandler()

        if search_type == 'name':
            foods = handler.search_by_name(query, limit)
        else:  # jan_code
            foods = handler.search_by_jan_code(query)

        logger.info(f"Found {len(foods)} foods for query: {query}")

        response_data = {
            'foods': foods,
            'count': len(foods),
        }

        # 結果が0件の場合、AI検索オプションを提示
        if len(foods) == 0:
            response_data['ai_search_available'] = True
            response_data['message'] = '該当する食品が見つかりませんでした。AI検索を利用できます。'

        return success_response(response_data)

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return error_response(
            str(e),
            request_id=request_id,
            status_code=400
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return error_response(
            "Internal server error",
            request_id=request_id,
            status_code=500
        )


# For local testing
if __name__ == "__main__":
    # テスト用イベント
    test_event = {
        "query": "白米",
        "search_type": "name",
        "limit": 5
    }

    class MockContext:
        request_id = "test-request-id"

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2, ensure_ascii=False))
