"""
食品マスタパーサー

日本食品標準成分表やOpen Food Factsなどからの食品データをパース
"""
import csv
import json
import requests
from typing import List, Dict, Optional, Tuple
from io import StringIO
import uuid

from .models import Food, FoodSource
from .exceptions import ValidationError
from .logger import get_logger

logger = get_logger(__name__)


class StandardFoodParser:
    """
    日本食品標準成分表のCSVパーサー

    標準的なフォーマット:
    - food_id: 食品ID（生成）
    - name: 食品名
    - calories_per_100g: カロリー（100gあたり）
    - protein_per_100g: タンパク質（g）
    - fat_per_100g: 脂質（g）
    - carbs_per_100g: 炭水化物（g）
    - jan_code: JANコード（オプション）
    """

    # 標準的なCSV列のマッピング
    COLUMN_MAPPING = {
        '食品名': 'name',
        'エネルギー（kcal）': 'calories_per_100g',
        'たんぱく質（g）': 'protein_per_100g',
        '脂質（g）': 'fat_per_100g',
        '炭水化物（g）': 'carbs_per_100g',
        'JANコード': 'jan_code',
    }

    @staticmethod
    def parse_csv_content(csv_content: str) -> List[Food]:
        """
        CSVコンテンツをパース

        Args:
            csv_content: CSV形式の文字列

        Returns:
            パース済みのFoodオブジェクトリスト

        Raises:
            ValidationError: パースエラー
        """
        foods = []

        try:
            reader = csv.DictReader(StringIO(csv_content))

            if reader.fieldnames is None:
                raise ValidationError(
                    "CSVファイルが空または無効です",
                    details={"source": "csv_parsing"}
                )

            for row_num, row in enumerate(reader, start=2):  # ヘッダーはrow 1
                try:
                    food = StandardFoodParser._parse_row(row)
                    if food:
                        foods.append(food)
                except ValidationError as e:
                    logger.warning(
                        f"Row {row_num} parsing failed: {str(e)}"
                    )
                    continue

        except Exception as e:
            raise ValidationError(
                f"CSVパース中にエラーが発生しました: {str(e)}",
                details={"error": str(e)}
            )

        return foods

    @staticmethod
    def _parse_row(row: Dict[str, str]) -> Optional[Food]:
        """
        CSVの1行をパース

        Args:
            row: CSVの1行（辞書）

        Returns:
            パース済みのFoodオブジェクト、またはNone
        """
        # 必須フィールドを抽出
        name = row.get('食品名', '').strip()
        calories_str = row.get('エネルギー（kcal）', '').strip()
        protein_str = row.get('たんぱく質（g）', '').strip()
        fat_str = row.get('脂質（g）', '').strip()
        carbs_str = row.get('炭水化物（g）', '').strip()
        jan_code = row.get('JANコード', '').strip() or None

        # バリデーション
        if not name:
            return None

        try:
            calories = float(calories_str) if calories_str else 0.0
            protein = float(protein_str) if protein_str else 0.0
            fat = float(fat_str) if fat_str else 0.0
            carbs = float(carbs_str) if carbs_str else 0.0
        except ValueError as e:
            raise ValidationError(
                f"栄養値の数値パースに失敗: {str(e)}",
                details={"row": row}
            )

        # Foodオブジェクトを作成
        food = Food(
            food_id=f"standard_{uuid.uuid4().hex[:12]}",
            name=name,
            calories_per_100g=calories,
            protein_per_100g=protein,
            fat_per_100g=fat,
            carbs_per_100g=carbs,
            source=FoodSource.STANDARD,
            jan_code=jan_code
        )

        return food


class OpenFoodFactsClient:
    """
    Open Food Facts API クライアント

    https://world.openfoodfacts.org/api
    """

    BASE_URL = "https://world.openfoodfacts.org/api/v0"

    def __init__(self, timeout: int = 10):
        """
        初期化

        Args:
            timeout: リクエストタイムアウト（秒）
        """
        self.timeout = timeout

    def search_product(self, query: str) -> Optional[Dict]:
        """
        商品検索

        Args:
            query: 検索クエリ（商品名またはJANコード）

        Returns:
            商品情報、または見つからない場合はNone
        """
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                'search_terms': query,
                'json': 1,
                'action': 'process'
            }

            response = requests.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            products = data.get('products', [])

            if products:
                return products[0]
            return None

        except Exception as e:
            logger.warning(f"Open Food Facts search failed: {str(e)}")
            return None

    def product_to_food(self, product: Dict) -> Optional[Food]:
        """
        Open Food Factsの商品情報をFoodオブジェクトに変換

        Args:
            product: Open Food Factsの商品情報

        Returns:
            Foodオブジェクト、または変換失敗の場合はNone
        """
        try:
            name = product.get('product_name', '').strip()
            if not name:
                return None

            # 100gあたりの栄養値を取得
            nutrients = product.get('nutrients', {})

            # Open Food Factsのキーは異なるため、マッピングが必要
            calories_per_100g = (
                nutrients.get('energy-kcal_100g') or
                (nutrients.get('energy_100g', 0) / 4.184) or  # kJからkcalに変換
                0.0
            )
            protein_per_100g = nutrients.get('proteins_100g', 0.0) or 0.0
            fat_per_100g = nutrients.get('fat_100g', 0.0) or 0.0
            carbs_per_100g = nutrients.get('carbohydrates_100g', 0.0) or 0.0

            # JANコード
            jan_code = product.get('barcode', '').strip() or None

            food = Food(
                food_id=f"off_{uuid.uuid4().hex[:12]}",
                name=name,
                calories_per_100g=calories_per_100g,
                protein_per_100g=protein_per_100g,
                fat_per_100g=fat_per_100g,
                carbs_per_100g=carbs_per_100g,
                source=FoodSource.OPEN_FOOD_FACTS,
                jan_code=jan_code
            )

            return food

        except Exception as e:
            logger.warning(
                f"Failed to convert Open Food Facts product: {str(e)}"
            )
            return None


class FoodMasterImporter:
    """食品マスタデータインポーター"""

    def __init__(self):
        """初期化"""
        self.standard_parser = StandardFoodParser()
        self.off_client = OpenFoodFactsClient()

    def import_from_csv(self, csv_content: str) -> Tuple[List[Food], List[str]]:
        """
        CSVからインポート

        Args:
            csv_content: CSV形式の文字列

        Returns:
            (成功したFoodリスト, エラーメッセージリスト)
        """
        foods = []
        errors = []

        try:
            foods = self.standard_parser.parse_csv_content(csv_content)
            logger.info(f"Successfully imported {len(foods)} foods from CSV")
        except ValidationError as e:
            errors.append(str(e))
            logger.error(f"CSV import failed: {str(e)}")

        return foods, errors

    def import_from_url(self, csv_url: str) -> Tuple[List[Food], List[str]]:
        """
        URLからCSVをダウンロードしてインポート

        Args:
            csv_url: CSVファイルのURL

        Returns:
            (成功したFoodリスト, エラーメッセージリスト)
        """
        foods = []
        errors = []

        try:
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()

            csv_content = response.text
            foods, csv_errors = self.import_from_csv(csv_content)
            errors.extend(csv_errors)

            logger.info(
                f"Successfully imported from URL: {len(foods)} foods"
            )
        except Exception as e:
            error_msg = f"Failed to import from URL: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

        return foods, errors
