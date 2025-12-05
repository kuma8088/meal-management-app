"""
食品検索ロジック

要件: 4.1, 4.2, 4.3
"""
from typing import List, Optional
from .models import Food, FoodSource
from .dynamodb_helper import DynamoDBHelper
from .exceptions import ValidationError
from .logger import get_logger

logger = get_logger(__name__)


class FoodSearch:
    """食品検索クラス"""

    def __init__(self, table_name: str = "Foods", region_name: str = "ap-northeast-1"):
        """
        初期化

        Args:
            table_name: Foodsテーブル名
            region_name: AWSリージョン名
        """
        self.db_helper = DynamoDBHelper(table_name, region_name)
        self.table_name = table_name

    def search_by_name(self, query: str, limit: Optional[int] = None) -> List[Food]:
        """
        食品名で部分一致検索を行う

        Args:
            query: 検索クエリ（食品名の一部）
            limit: 取得する最大件数（オプション）

        Returns:
            検索結果の食品リスト

        Raises:
            ValidationError: クエリが無効な場合

        要件: 4.1
        """
        # バリデーション
        if not query or not query.strip():
            raise ValidationError(
                "検索クエリは必須です",
                details={"query": query}
            )

        query = query.strip()

        # DynamoDBでスキャンして部分一致検索
        # contains関数を使用して部分一致を実現
        items = self.db_helper.scan(
            filter_expression="contains(#name, :query)",
            expression_attribute_names={"#name": "name"},
            expression_attribute_values={":query": query},
            limit=limit
        )

        # Food オブジェクトに変換
        foods = []
        for item in items:
            try:
                food = Food(
                    food_id=item["food_id"],
                    name=item["name"],
                    calories_per_100g=item["calories_per_100g"],
                    protein_per_100g=item["protein_per_100g"],
                    fat_per_100g=item["fat_per_100g"],
                    carbs_per_100g=item["carbs_per_100g"],
                    jan_code=item.get("jan_code"),
                    source=FoodSource(item["source"]),
                    created_at=item["created_at"],
                    updated_at=item["updated_at"]
                )
                foods.append(food)
            except (KeyError, ValueError) as e:
                logger.warning(
                    f"食品データの変換に失敗しました: {item.get('food_id', 'unknown')}",
                    extra={
                        "extra_data": {
                            "food_id": item.get("food_id"),
                            "error": str(e)
                        }
                    }
                )
                continue

        logger.info(
            f"食品名検索を実行しました: クエリ={query}, 結果数={len(foods)}",
            extra={
                "extra_data": {
                    "query": query,
                    "result_count": len(foods)
                }
            }
        )

        return foods

    def search_by_jan_code(self, jan_code: str) -> Optional[Food]:
        """
        JANコードで完全一致検索を行う

        Args:
            jan_code: JANコード

        Returns:
            検索結果の食品（見つからない場合はNone）

        Raises:
            ValidationError: JANコードが無効な場合

        要件: 4.2
        """
        # バリデーション
        if not jan_code or not jan_code.strip():
            raise ValidationError(
                "JANコードは必須です",
                details={"jan_code": jan_code}
            )

        jan_code = jan_code.strip()

        # GSI2 (jan_code index) を使ってクエリ
        items = self.db_helper.query(
            key_condition_expression="jan_code = :jan_code",
            expression_attribute_values={":jan_code": jan_code},
            index_name="GSI2",
            limit=1
        )

        if not items:
            logger.info(
                f"JANコード検索で食品が見つかりませんでした: {jan_code}",
                extra={
                    "extra_data": {
                        "jan_code": jan_code
                    }
                }
            )
            return None

        # 最初の結果を返す
        item = items[0]

        try:
            food = Food(
                food_id=item["food_id"],
                name=item["name"],
                calories_per_100g=item["calories_per_100g"],
                protein_per_100g=item["protein_per_100g"],
                fat_per_100g=item["fat_per_100g"],
                carbs_per_100g=item["carbs_per_100g"],
                jan_code=item.get("jan_code"),
                source=FoodSource(item["source"]),
                created_at=item["created_at"],
                updated_at=item["updated_at"]
            )

            logger.info(
                f"JANコード検索で食品を見つけました: {jan_code} -> {food.name}",
                extra={
                    "extra_data": {
                        "jan_code": jan_code,
                        "food_id": food.food_id,
                        "food_name": food.name
                    }
                }
            )

            return food

        except (KeyError, ValueError) as e:
            logger.error(
                f"食品データの変換に失敗しました: {item.get('food_id', 'unknown')}",
                extra={
                    "extra_data": {
                        "food_id": item.get("food_id"),
                        "error": str(e)
                    }
                }
            )
            return None
