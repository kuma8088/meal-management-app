"""
食品検索ロジックのテスト

Property 7, 8, 9のプロパティテスト、およびユニットテスト
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    FoodSearch,
    Food,
    FoodSource,
    ValidationError,
)


class TestFoodSearchPropertyBased:
    """食品検索のプロパティベーステスト"""

    @given(
        query=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")
    )
    def test_partial_match_search_property(self, query):
        """
        Feature: meal-management-app, Property 7: 食品名の部分一致検索

        任意の検索クエリに対して、食品名に検索クエリが部分文字列として
        含まれるすべての食品が検索結果に含まれる必要があります。

        検証: 要件 4.1
        """
        # モックの食品データを作成
        # クエリを含む食品と含まない食品を混在させる
        mock_foods = [
            {
                "food_id": "food1",
                "name": f"Test {query} Food",
                "calories_per_100g": 100.0,
                "protein_per_100g": 10.0,
                "fat_per_100g": 5.0,
                "carbs_per_100g": 15.0,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            {
                "food_id": "food2",
                "name": f"Another {query}",
                "calories_per_100g": 200.0,
                "protein_per_100g": 20.0,
                "fat_per_100g": 10.0,
                "carbs_per_100g": 25.0,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            {
                "food_id": "food3",
                "name": "Different Food",
                "calories_per_100g": 150.0,
                "protein_per_100g": 15.0,
                "fat_per_100g": 7.5,
                "carbs_per_100g": 20.0,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        ]

        # DynamoDBHelperをモック
        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            # scanメソッドはクエリを含む食品のみを返す（DynamoDBの動作を模倣）
            mock_instance.scan.return_value = [
                food for food in mock_foods if query in food["name"]
            ]
            mock_db.return_value = mock_instance

            # FoodSearchインスタンスを作成
            food_search = FoodSearch()

            # 検索を実行
            results = food_search.search_by_name(query)

            # プロパティ 7 の検証: すべての結果に検索クエリが含まれている
            for food in results:
                assert query in food.name, f"検索結果 '{food.name}' にクエリ '{query}' が含まれていません"

            # 逆の検証: クエリを含まない食品は結果に含まれていない
            result_ids = {food.food_id for food in results}
            for food in mock_foods:
                if query in food["name"]:
                    # クエリを含む食品は結果に含まれているはず
                    assert food["food_id"] in result_ids
                else:
                    # クエリを含まない食品は結果に含まれていないはず
                    assert food["food_id"] not in result_ids

    @given(
        jan_code=st.text(
            alphabet=st.characters(whitelist_categories=("Nd",)),
            min_size=8,
            max_size=13
        )
    )
    def test_jan_code_exact_match_property(self, jan_code):
        """
        Feature: meal-management-app, Property 8: JANコードの完全一致検索

        任意のJANコード検索に対して、そのJANコードと完全に一致する
        食品のみが検索結果に含まれる必要があります。

        検証: 要件 4.2
        """
        # モックの食品データ
        matching_food = {
            "food_id": "food1",
            "name": "Matching Product",
            "calories_per_100g": 100.0,
            "protein_per_100g": 10.0,
            "fat_per_100g": 5.0,
            "carbs_per_100g": 15.0,
            "jan_code": jan_code,
            "source": "OPEN_FOOD_FACTS",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }

        # DynamoDBHelperをモック
        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            # queryメソッドは完全一致する食品を返す
            mock_instance.query.return_value = [matching_food]
            mock_db.return_value = mock_instance

            # FoodSearchインスタンスを作成
            food_search = FoodSearch()

            # 検索を実行
            result = food_search.search_by_jan_code(jan_code)

            # プロパティ 8 の検証: JANコードが完全に一致している
            assert result is not None
            assert result.jan_code == jan_code, f"検索結果のJANコード '{result.jan_code}' が検索クエリ '{jan_code}' と一致しません"

    @given(
        foods_count=st.integers(min_value=1, max_value=10)
    )
    def test_search_results_required_information_property(self, foods_count):
        """
        Feature: meal-management-app, Property 9: 検索結果の必須情報

        任意の検索結果リストの各食品は、食品名、カロリー、タンパク質、
        脂質、炭水化物の情報を含む必要があります。

        検証: 要件 4.3
        """
        # モックの食品データを生成
        mock_foods = []
        for i in range(foods_count):
            mock_foods.append({
                "food_id": f"food{i}",
                "name": f"Test Food {i}",
                "calories_per_100g": 100.0 + i * 10,
                "protein_per_100g": 10.0 + i,
                "fat_per_100g": 5.0 + i * 0.5,
                "carbs_per_100g": 15.0 + i * 2,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            })

        # DynamoDBHelperをモック
        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.scan.return_value = mock_foods
            mock_db.return_value = mock_instance

            # FoodSearchインスタンスを作成
            food_search = FoodSearch()

            # 検索を実行
            results = food_search.search_by_name("Test")

            # プロパティ 9 の検証: すべての結果に必須情報が含まれている
            assert len(results) == foods_count

            for food in results:
                # 必須フィールドの存在確認
                assert hasattr(food, "name") and food.name is not None
                assert hasattr(food, "calories_per_100g") and food.calories_per_100g is not None
                assert hasattr(food, "protein_per_100g") and food.protein_per_100g is not None
                assert hasattr(food, "fat_per_100g") and food.fat_per_100g is not None
                assert hasattr(food, "carbs_per_100g") and food.carbs_per_100g is not None

                # 値の型確認
                assert isinstance(food.name, str)
                assert isinstance(food.calories_per_100g, (int, float))
                assert isinstance(food.protein_per_100g, (int, float))
                assert isinstance(food.fat_per_100g, (int, float))
                assert isinstance(food.carbs_per_100g, (int, float))


class TestFoodSearch:
    """食品検索クラスのユニットテスト"""

    def test_search_by_name_basic(self):
        """基本的な食品名検索"""
        mock_foods = [
            {
                "food_id": "food1",
                "name": "白米",
                "calories_per_100g": 168.0,
                "protein_per_100g": 2.5,
                "fat_per_100g": 0.3,
                "carbs_per_100g": 37.1,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        ]

        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.scan.return_value = mock_foods
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            results = food_search.search_by_name("白米")

            assert len(results) == 1
            assert results[0].name == "白米"
            assert results[0].calories_per_100g == 168.0

    def test_search_by_name_no_results(self):
        """検索結果がない場合"""
        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.scan.return_value = []
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            results = food_search.search_by_name("存在しない食品")

            assert len(results) == 0

    def test_search_by_name_empty_query(self):
        """空のクエリでのバリデーション"""
        food_search = FoodSearch()

        with pytest.raises(ValidationError):
            food_search.search_by_name("")

    def test_search_by_name_whitespace_query(self):
        """空白のみのクエリでのバリデーション"""
        food_search = FoodSearch()

        with pytest.raises(ValidationError):
            food_search.search_by_name("   ")

    def test_search_by_name_with_limit(self):
        """制限付き検索"""
        mock_foods = [
            {
                "food_id": f"food{i}",
                "name": f"米{i}",
                "calories_per_100g": 168.0,
                "protein_per_100g": 2.5,
                "fat_per_100g": 0.3,
                "carbs_per_100g": 37.1,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
            for i in range(5)
        ]

        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.scan.return_value = mock_foods[:3]  # limitが適用された結果
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            results = food_search.search_by_name("米", limit=3)

            assert len(results) == 3

    def test_search_by_jan_code_found(self):
        """JANコード検索で食品が見つかる場合"""
        mock_food = {
            "food_id": "food1",
            "name": "コカ・コーラ",
            "calories_per_100g": 45.0,
            "protein_per_100g": 0.0,
            "fat_per_100g": 0.0,
            "carbs_per_100g": 11.3,
            "jan_code": "4902102072557",
            "source": "OPEN_FOOD_FACTS",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }

        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.query.return_value = [mock_food]
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            result = food_search.search_by_jan_code("4902102072557")

            assert result is not None
            assert result.name == "コカ・コーラ"
            assert result.jan_code == "4902102072557"

    def test_search_by_jan_code_not_found(self):
        """JANコード検索で食品が見つからない場合"""
        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.query.return_value = []
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            result = food_search.search_by_jan_code("0000000000000")

            assert result is None

    def test_search_by_jan_code_empty(self):
        """空のJANコードでのバリデーション"""
        food_search = FoodSearch()

        with pytest.raises(ValidationError):
            food_search.search_by_jan_code("")

    def test_search_by_jan_code_whitespace(self):
        """空白のみのJANコードでのバリデーション"""
        food_search = FoodSearch()

        with pytest.raises(ValidationError):
            food_search.search_by_jan_code("   ")

    def test_search_by_name_with_invalid_data(self):
        """無効なデータが含まれる場合（スキップされる）"""
        mock_foods = [
            {
                "food_id": "food1",
                "name": "正常な食品",
                "calories_per_100g": 100.0,
                "protein_per_100g": 10.0,
                "fat_per_100g": 5.0,
                "carbs_per_100g": 15.0,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            {
                "food_id": "food2",
                "name": "不正な食品"
                # 必須フィールドが欠けている
            }
        ]

        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.scan.return_value = mock_foods
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            results = food_search.search_by_name("食品")

            # 無効なデータはスキップされ、正常なデータのみが返される
            assert len(results) == 1
            assert results[0].name == "正常な食品"

    def test_search_by_jan_code_with_invalid_data(self):
        """JANコード検索で無効なデータが返される場合"""
        mock_food = {
            "food_id": "food1",
            "name": "不正な食品"
            # 必須フィールドが欠けている
        }

        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.query.return_value = [mock_food]
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            result = food_search.search_by_jan_code("1234567890123")

            # 無効なデータの場合はNoneを返す
            assert result is None

    def test_search_by_name_multiple_results(self):
        """複数の検索結果が返される場合"""
        mock_foods = [
            {
                "food_id": "food1",
                "name": "鶏むね肉",
                "calories_per_100g": 108.0,
                "protein_per_100g": 22.3,
                "fat_per_100g": 1.5,
                "carbs_per_100g": 0.0,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            {
                "food_id": "food2",
                "name": "鶏もも肉",
                "calories_per_100g": 200.0,
                "protein_per_100g": 16.2,
                "fat_per_100g": 14.0,
                "carbs_per_100g": 0.0,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            {
                "food_id": "food3",
                "name": "鶏ささみ",
                "calories_per_100g": 105.0,
                "protein_per_100g": 23.0,
                "fat_per_100g": 0.8,
                "carbs_per_100g": 0.0,
                "source": "STANDARD",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        ]

        with patch("common.food_search.DynamoDBHelper") as mock_db:
            mock_instance = Mock()
            mock_instance.scan.return_value = mock_foods
            mock_db.return_value = mock_instance

            food_search = FoodSearch()
            results = food_search.search_by_name("鶏")

            assert len(results) == 3
            names = {food.name for food in results}
            assert names == {"鶏むね肉", "鶏もも肉", "鶏ささみ"}
