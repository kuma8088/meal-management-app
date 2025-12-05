"""
栄養計算ロジックのテスト

Property 11プロパティテスト、Property 12プロパティテスト、およびユニットテスト
"""
import pytest
import sys
from pathlib import Path
from hypothesis import given, strategies as st

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    NutritionCalculator,
    Food,
    MealFood,
    FoodSource,
    ValidationError,
)


class TestNutritionCalculatorPropertyBased:
    """栄養計算のプロパティベーステスト"""

    @given(
        calories_per_100g=st.floats(min_value=0, max_value=900, allow_nan=False, allow_infinity=False),
        protein_per_100g=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        fat_per_100g=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        carbs_per_100g=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        amount_grams=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    def test_nutrition_calculation_property(
        self,
        calories_per_100g,
        protein_per_100g,
        fat_per_100g,
        carbs_per_100g,
        amount_grams
    ):
        """
        Feature: meal-management-app, Property 11: 栄養情報の自動計算

        任意の食品と量が与えられた場合、システムはカロリー、タンパク質、脂質、
        炭水化物を正確に計算する必要があります。

        計算式: 栄養成分 = 100gあたりの値 × (量 / 100)

        検証: 要件 6.3, 7.1, 7.2, 7.3, 7.4
        """
        # テスト用の食品を作成
        food = Food(
            food_id="test_food",
            name="テスト食品",
            calories_per_100g=calories_per_100g,
            protein_per_100g=protein_per_100g,
            fat_per_100g=fat_per_100g,
            carbs_per_100g=carbs_per_100g,
            source=FoodSource.STANDARD
        )

        # 栄養情報を計算
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, amount_grams)

        # 計算結果のプロパティを検証
        multiplier = amount_grams / 100.0
        expected_calories = calories_per_100g * multiplier
        expected_protein = protein_per_100g * multiplier
        expected_fat = fat_per_100g * multiplier
        expected_carbs = carbs_per_100g * multiplier

        # すべての栄養成分が計算されていることを確認
        assert "calories" in nutrition
        assert "protein" in nutrition
        assert "fat" in nutrition
        assert "carbs" in nutrition

        # 計算値が正確であることを確認
        assert abs(nutrition["calories"] - expected_calories) < 0.001
        assert abs(nutrition["protein"] - expected_protein) < 0.001
        assert abs(nutrition["fat"] - expected_fat) < 0.001
        assert abs(nutrition["carbs"] - expected_carbs) < 0.001

        # すべての値が非負であることを確認
        assert nutrition["calories"] >= 0
        assert nutrition["protein"] >= 0
        assert nutrition["fat"] >= 0
        assert nutrition["carbs"] >= 0

    @given(
        num_foods=st.integers(min_value=1, max_value=10)
    )
    def test_multiple_foods_total_nutrition_property(self, num_foods):
        """
        Feature: meal-management-app, Property 12: 複数食品の栄養情報合計

        任意の複数の食品の栄養情報が与えられた場合、システムはそれぞれの
        合計を正確に計算する必要があります。

        合計は、各食品の各栄養成分を足したものに等しい。

        検証: 要件 7.5
        """
        # テスト用の栄養情報リストを生成
        nutrition_list = []
        expected_total_calories = 0.0
        expected_total_protein = 0.0
        expected_total_fat = 0.0
        expected_total_carbs = 0.0

        for i in range(num_foods):
            calories = float(i * 50 + 100)  # 100, 150, 200, ...
            protein = float(i * 5 + 10)     # 10, 15, 20, ...
            fat = float(i * 2 + 5)          # 5, 7, 9, ...
            carbs = float(i * 10 + 30)      # 30, 40, 50, ...

            nutrition_list.append({
                "calories": calories,
                "protein": protein,
                "fat": fat,
                "carbs": carbs
            })

            expected_total_calories += calories
            expected_total_protein += protein
            expected_total_fat += fat
            expected_total_carbs += carbs

        # 合計を計算
        total = NutritionCalculator.calculate_total_nutrition(nutrition_list)

        # すべての合計フィールドが含まれることを確認
        assert "total_calories" in total
        assert "total_protein" in total
        assert "total_fat" in total
        assert "total_carbs" in total

        # 合計値が正確であることを確認
        assert abs(total["total_calories"] - expected_total_calories) < 0.001
        assert abs(total["total_protein"] - expected_total_protein) < 0.001
        assert abs(total["total_fat"] - expected_total_fat) < 0.001
        assert abs(total["total_carbs"] - expected_total_carbs) < 0.001

        # すべての値が非負であることを確認
        assert total["total_calories"] >= 0
        assert total["total_protein"] >= 0
        assert total["total_fat"] >= 0
        assert total["total_carbs"] >= 0


class TestNutritionCalculator:
    """栄養計算クラスのユニットテスト"""

    def test_calculate_nutrition_for_amount_basic(self):
        """基本的な単一食品の栄養計算"""
        food = Food(
            food_id="rice",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )

        # 100gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 100)

        assert nutrition["calories"] == 168.0
        assert nutrition["protein"] == 2.5
        assert nutrition["fat"] == 0.3
        assert nutrition["carbs"] == 37.1

    def test_calculate_nutrition_for_amount_50g(self):
        """50gの栄養計算"""
        food = Food(
            food_id="rice",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )

        # 50gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 50)

        assert abs(nutrition["calories"] - 84.0) < 0.001
        assert abs(nutrition["protein"] - 1.25) < 0.001
        assert abs(nutrition["fat"] - 0.15) < 0.001
        assert abs(nutrition["carbs"] - 18.55) < 0.001

    def test_calculate_nutrition_for_amount_200g(self):
        """200gの栄養計算"""
        food = Food(
            food_id="rice",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )

        # 200gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 200)

        assert abs(nutrition["calories"] - 336.0) < 0.001
        assert abs(nutrition["protein"] - 5.0) < 0.001
        assert abs(nutrition["fat"] - 0.6) < 0.001
        assert abs(nutrition["carbs"] - 74.2) < 0.001

    def test_calculate_nutrition_for_amount_zero_grams(self):
        """0gの栄養計算"""
        food = Food(
            food_id="rice",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )

        # 0gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 0)

        assert nutrition["calories"] == 0.0
        assert nutrition["protein"] == 0.0
        assert nutrition["fat"] == 0.0
        assert nutrition["carbs"] == 0.0

    def test_calculate_nutrition_for_amount_negative_amount(self):
        """負の量でのバリデーション"""
        food = Food(
            food_id="rice",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )

        # 負の量は例外を発生させるべき
        with pytest.raises(ValidationError):
            NutritionCalculator.calculate_nutrition_for_amount(food, -10)

    def test_calculate_total_nutrition_single_food(self):
        """単一食品の合計栄養計算"""
        nutrition_list = [
            {
                "calories": 168.0,
                "protein": 2.5,
                "fat": 0.3,
                "carbs": 37.1
            }
        ]

        total = NutritionCalculator.calculate_total_nutrition(nutrition_list)

        assert total["total_calories"] == 168.0
        assert total["total_protein"] == 2.5
        assert total["total_fat"] == 0.3
        assert total["total_carbs"] == 37.1

    def test_calculate_total_nutrition_multiple_foods(self):
        """複数食品の合計栄養計算"""
        nutrition_list = [
            {
                "calories": 168.0,
                "protein": 2.5,
                "fat": 0.3,
                "carbs": 37.1
            },
            {
                "calories": 151.0,
                "protein": 12.3,
                "fat": 10.3,
                "carbs": 0.3
            },
            {
                "calories": 61.0,
                "protein": 3.2,
                "fat": 3.6,
                "carbs": 4.8
            }
        ]

        total = NutritionCalculator.calculate_total_nutrition(nutrition_list)

        assert abs(total["total_calories"] - 380.0) < 0.001
        assert abs(total["total_protein"] - 18.0) < 0.001
        assert abs(total["total_fat"] - 14.2) < 0.001
        assert abs(total["total_carbs"] - 42.2) < 0.001

    def test_calculate_total_nutrition_empty_list(self):
        """空のリストの合計栄養計算"""
        nutrition_list = []

        total = NutritionCalculator.calculate_total_nutrition(nutrition_list)

        assert total["total_calories"] == 0.0
        assert total["total_protein"] == 0.0
        assert total["total_fat"] == 0.0
        assert total["total_carbs"] == 0.0

    def test_calculate_meal_nutrition(self):
        """食事全体の栄養計算"""
        # 食品データベースを作成
        food_database = {
            "rice": Food(
                food_id="rice",
                name="白米",
                calories_per_100g=168.0,
                protein_per_100g=2.5,
                fat_per_100g=0.3,
                carbs_per_100g=37.1,
                source=FoodSource.STANDARD
            ),
            "egg": Food(
                food_id="egg",
                name="鶏卵",
                calories_per_100g=151.0,
                protein_per_100g=12.3,
                fat_per_100g=10.3,
                carbs_per_100g=0.3,
                source=FoodSource.STANDARD
            )
        }

        # 食事を構成する食品
        meal_foods = [
            MealFood(food_id="rice", amount=100.0),
            MealFood(food_id="egg", amount=50.0)
        ]

        # 栄養情報を計算
        total = NutritionCalculator.calculate_meal_nutrition(meal_foods, food_database)

        # 期待値
        # rice: 100g -> 168 cal, 2.5 protein, 0.3 fat, 37.1 carbs
        # egg: 50g -> 75.5 cal, 6.15 protein, 5.15 fat, 0.15 carbs
        # total: 243.5 cal, 8.65 protein, 5.45 fat, 37.25 carbs

        assert abs(total["total_calories"] - 243.5) < 0.1
        assert abs(total["total_protein"] - 8.65) < 0.1
        assert abs(total["total_fat"] - 5.45) < 0.1
        assert abs(total["total_carbs"] - 37.25) < 0.1

    def test_calculate_meal_nutrition_missing_food(self):
        """存在しない食品IDでのエラーハンドリング"""
        food_database = {
            "rice": Food(
                food_id="rice",
                name="白米",
                calories_per_100g=168.0,
                protein_per_100g=2.5,
                fat_per_100g=0.3,
                carbs_per_100g=37.1,
                source=FoodSource.STANDARD
            )
        }

        # 存在しない食品IDを含む
        meal_foods = [
            MealFood(food_id="rice", amount=100.0),
            MealFood(food_id="unknown_food", amount=50.0)
        ]

        # 存在しない食品IDはValidationErrorを発生させるべき
        with pytest.raises(ValidationError):
            NutritionCalculator.calculate_meal_nutrition(meal_foods, food_database)

    def test_calculate_meal_nutrition_single_food(self):
        """単一食品の食事計算"""
        food_database = {
            "rice": Food(
                food_id="rice",
                name="白米",
                calories_per_100g=168.0,
                protein_per_100g=2.5,
                fat_per_100g=0.3,
                carbs_per_100g=37.1,
                source=FoodSource.STANDARD
            )
        }

        meal_foods = [MealFood(food_id="rice", amount=150.0)]

        total = NutritionCalculator.calculate_meal_nutrition(meal_foods, food_database)

        expected_calories = 168.0 * 1.5
        expected_protein = 2.5 * 1.5
        expected_fat = 0.3 * 1.5
        expected_carbs = 37.1 * 1.5

        assert abs(total["total_calories"] - expected_calories) < 0.001
        assert abs(total["total_protein"] - expected_protein) < 0.001
        assert abs(total["total_fat"] - expected_fat) < 0.001
        assert abs(total["total_carbs"] - expected_carbs) < 0.001

    def test_calculate_nutrition_edge_case_large_amount(self):
        """大きな量での計算"""
        food = Food(
            food_id="rice",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )

        # 1000gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 1000)

        assert abs(nutrition["calories"] - 1680.0) < 0.1
        assert abs(nutrition["protein"] - 25.0) < 0.1
        assert abs(nutrition["fat"] - 3.0) < 0.1
        assert abs(nutrition["carbs"] - 371.0) < 0.1

    def test_calculate_nutrition_edge_case_small_amount(self):
        """小さな量での計算"""
        food = Food(
            food_id="rice",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )

        # 1gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 1)

        assert abs(nutrition["calories"] - 1.68) < 0.01
        assert abs(nutrition["protein"] - 0.025) < 0.001
        assert abs(nutrition["fat"] - 0.003) < 0.001
        assert abs(nutrition["carbs"] - 0.371) < 0.001
