"""
栄養計算ロジック

要件: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5
"""
from typing import List, Dict
from .models import Food, MealFood
from .exceptions import ValidationError


class NutritionCalculator:
    """栄養情報を計算するクラス"""
    
    @staticmethod
    def calculate_nutrition_for_amount(
        food: Food,
        amount_grams: float
    ) -> Dict[str, float]:
        """
        指定された量の食品の栄養情報を計算する
        
        Args:
            food: 食品オブジェクト
            amount_grams: 量（グラム）
        
        Returns:
            栄養情報の辞書（calories, protein, fat, carbs）
        
        Raises:
            ValidationError: 量が負の値の場合
        
        要件: 7.1, 7.2, 7.3, 7.4
        """
        if amount_grams < 0:
            raise ValidationError(
                "量は0以上である必要があります",
                details={"amount_grams": amount_grams}
            )
        
        # 100gあたりの栄養情報を実際の量に換算
        multiplier = amount_grams / 100.0
        
        return {
            "calories": food.calories_per_100g * multiplier,
            "protein": food.protein_per_100g * multiplier,
            "fat": food.fat_per_100g * multiplier,
            "carbs": food.carbs_per_100g * multiplier
        }
    
    @staticmethod
    def calculate_total_nutrition(
        foods_with_nutrition: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        複数の食品の栄養情報を合計する
        
        Args:
            foods_with_nutrition: 各食品の栄養情報のリスト
        
        Returns:
            合計栄養情報の辞書（total_calories, total_protein, total_fat, total_carbs）
        
        要件: 7.5
        """
        if not foods_with_nutrition:
            return {
                "total_calories": 0.0,
                "total_protein": 0.0,
                "total_fat": 0.0,
                "total_carbs": 0.0
            }
        
        total_calories = sum(item["calories"] for item in foods_with_nutrition)
        total_protein = sum(item["protein"] for item in foods_with_nutrition)
        total_fat = sum(item["fat"] for item in foods_with_nutrition)
        total_carbs = sum(item["carbs"] for item in foods_with_nutrition)
        
        return {
            "total_calories": total_calories,
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carbs": total_carbs
        }
    
    @staticmethod
    def calculate_meal_nutrition(
        meal_foods: List[MealFood],
        food_database: Dict[str, Food]
    ) -> Dict[str, float]:
        """
        食事全体の栄養情報を計算する
        
        Args:
            meal_foods: 食事に含まれる食品のリスト
            food_database: 食品IDをキーとする食品データベース
        
        Returns:
            合計栄養情報の辞書（total_calories, total_protein, total_fat, total_carbs）
        
        Raises:
            ValidationError: 食品IDが見つからない場合
        
        要件: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5
        """
        nutrition_list = []
        
        for meal_food in meal_foods:
            # 食品データベースから食品を取得
            food = food_database.get(meal_food.food_id)
            if food is None:
                raise ValidationError(
                    f"食品ID {meal_food.food_id} が見つかりません",
                    details={"food_id": meal_food.food_id}
                )
            
            # 各食品の栄養情報を計算
            nutrition = NutritionCalculator.calculate_nutrition_for_amount(
                food,
                meal_food.amount
            )
            nutrition_list.append(nutrition)
        
        # 合計を計算
        return NutritionCalculator.calculate_total_nutrition(nutrition_list)
