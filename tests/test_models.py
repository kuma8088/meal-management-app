"""
データモデルのテスト
"""
import pytest
import sys
from datetime import datetime, date
from pathlib import Path
from hypothesis import given, strategies as st

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    User,
    Meal,
    MealFood,
    Food,
    Goal,
    AdviceUsage,
    Gender,
    ActivityLevel,
    MealType,
    GoalType,
    FoodSource,
    ValidationError
)


class TestUser:
    """Userモデルのテスト"""
    
    def test_create_valid_user(self):
        """有効なユーザーの作成"""
        user = User(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE,
            bmr=1500.0,
            tdee=2000.0
        )
        
        assert user.user_id == "user123"
        assert user.age == 30
        assert user.height == 170.0
        assert user.weight == 70.0
        assert user.gender == Gender.MALE
        assert user.activity_level == ActivityLevel.MODERATE
        assert user.bmr == 1500.0
        assert user.tdee == 2000.0
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_to_dict(self):
        """ユーザーの辞書変換"""
        user = User(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE,
            bmr=1500.0,
            tdee=2000.0
        )
        
        user_dict = user.to_dict()
        
        assert user_dict["user_id"] == "user123"
        assert user_dict["age"] == 30
        assert user_dict["gender"] == "male"
        assert user_dict["activity_level"] == "moderate"
    
    def test_user_from_dict(self):
        """辞書からユーザーを作成"""
        user_dict = {
            "user_id": "user123",
            "age": 30,
            "height": 170.0,
            "weight": 70.0,
            "gender": "male",
            "activity_level": "moderate",
            "bmr": 1500.0,
            "tdee": 2000.0
        }
        
        user = User.from_dict(user_dict)
        
        assert user.user_id == "user123"
        assert user.gender == Gender.MALE
        assert user.activity_level == ActivityLevel.MODERATE
    
    def test_user_invalid_age(self):
        """無効な年齢でエラー"""
        with pytest.raises(ValidationError):
            User(
                user_id="user123",
                age=0,
                height=170.0,
                weight=70.0,
                gender=Gender.MALE,
                activity_level=ActivityLevel.MODERATE,
                bmr=1500.0,
                tdee=2000.0
            )
    
    def test_user_invalid_height(self):
        """無効な身長でエラー"""
        with pytest.raises(ValidationError):
            User(
                user_id="user123",
                age=30,
                height=30.0,
                weight=70.0,
                gender=Gender.MALE,
                activity_level=ActivityLevel.MODERATE,
                bmr=1500.0,
                tdee=2000.0
            )


class TestMealFood:
    """MealFoodモデルのテスト"""
    
    def test_create_valid_meal_food(self):
        """有効な食品の作成"""
        meal_food = MealFood(
            food_id="food123",
            amount=100.0
        )
        
        assert meal_food.food_id == "food123"
        assert meal_food.amount == 100.0
    
    def test_meal_food_invalid_amount(self):
        """無効な量でエラー"""
        with pytest.raises(ValidationError):
            MealFood(
                food_id="food123",
                amount=-10.0
            )


class TestMeal:
    """Mealモデルのテスト"""
    
    def test_create_valid_meal(self):
        """有効な食事記録の作成"""
        meal = Meal(
            meal_id="meal123",
            user_id="user123",
            meal_type=MealType.BREAKFAST,
            foods=[
                MealFood(food_id="food1", amount=100.0),
                MealFood(food_id="food2", amount=50.0)
            ],
            total_calories=500.0,
            total_protein=20.0,
            total_fat=10.0,
            total_carbs=60.0,
            timestamp=datetime.utcnow()
        )
        
        assert meal.meal_id == "meal123"
        assert meal.user_id == "user123"
        assert meal.meal_type == MealType.BREAKFAST
        assert len(meal.foods) == 2
        assert meal.total_calories == 500.0
    
    def test_meal_to_dict(self):
        """食事記録の辞書変換"""
        meal = Meal(
            meal_id="meal123",
            user_id="user123",
            meal_type=MealType.BREAKFAST,
            foods=[MealFood(food_id="food1", amount=100.0)],
            total_calories=500.0,
            total_protein=20.0,
            total_fat=10.0,
            total_carbs=60.0,
            timestamp=datetime.utcnow()
        )
        
        meal_dict = meal.to_dict()
        
        assert meal_dict["meal_id"] == "meal123"
        assert meal_dict["meal_type"] == "breakfast"
        assert len(meal_dict["foods"]) == 1
    
    def test_meal_empty_foods(self):
        """空の食品リストでエラー"""
        with pytest.raises(ValidationError):
            Meal(
                meal_id="meal123",
                user_id="user123",
                meal_type=MealType.BREAKFAST,
                foods=[],
                total_calories=0.0,
                total_protein=0.0,
                total_fat=0.0,
                total_carbs=0.0,
                timestamp=datetime.utcnow()
            )


class TestFood:
    """Foodモデルのテスト"""
    
    def test_create_valid_food(self):
        """有効な食品の作成"""
        food = Food(
            food_id="food123",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD
        )
        
        assert food.food_id == "food123"
        assert food.name == "白米"
        assert food.calories_per_100g == 168.0
        assert food.source == FoodSource.STANDARD
    
    def test_food_to_dict(self):
        """食品の辞書変換"""
        food = Food(
            food_id="food123",
            name="白米",
            calories_per_100g=168.0,
            protein_per_100g=2.5,
            fat_per_100g=0.3,
            carbs_per_100g=37.1,
            source=FoodSource.STANDARD,
            jan_code="1234567890123"
        )
        
        food_dict = food.to_dict()
        
        assert food_dict["food_id"] == "food123"
        assert food_dict["name"] == "白米"
        assert food_dict["source"] == "STANDARD"
        assert food_dict["jan_code"] == "1234567890123"
    
    def test_food_from_dict(self):
        """辞書から食品を作成"""
        food_dict = {
            "food_id": "food123",
            "name": "白米",
            "calories_per_100g": 168.0,
            "protein_per_100g": 2.5,
            "fat_per_100g": 0.3,
            "carbs_per_100g": 37.1,
            "source": "STANDARD"
        }
        
        food = Food.from_dict(food_dict)
        
        assert food.food_id == "food123"
        assert food.source == FoodSource.STANDARD


class TestGoal:
    """Goalモデルのテスト"""
    
    def test_create_valid_goal(self):
        """有効な目標の作成"""
        goal = Goal(
            goal_id="goal123",
            user_id="user123",
            current_weight=70.0,
            target_weight=65.0,
            target_date=date(2024, 12, 31),
            goal_type=GoalType.LOSE,
            daily_calorie_adjustment=-500.0,
            target_calories=1500.0,
            recommended_protein=100.0,
            recommended_fat=50.0,
            recommended_carbs=150.0,
            recommended_exercise_minutes=30
        )
        
        assert goal.goal_id == "goal123"
        assert goal.user_id == "user123"
        assert goal.current_weight == 70.0
        assert goal.target_weight == 65.0
        assert goal.goal_type == GoalType.LOSE
    
    def test_goal_to_dict(self):
        """目標の辞書変換"""
        goal = Goal(
            goal_id="goal123",
            user_id="user123",
            current_weight=70.0,
            target_weight=65.0,
            target_date=date(2024, 12, 31),
            goal_type=GoalType.LOSE,
            daily_calorie_adjustment=-500.0,
            target_calories=1500.0,
            recommended_protein=100.0,
            recommended_fat=50.0,
            recommended_carbs=150.0,
            recommended_exercise_minutes=30
        )
        
        goal_dict = goal.to_dict()
        
        assert goal_dict["goal_id"] == "goal123"
        assert goal_dict["goal_type"] == "lose"
        assert goal_dict["target_date"] == "2024-12-31"


class TestAdviceUsage:
    """AdviceUsageモデルのテスト"""

    def test_create_valid_advice_usage(self):
        """有効なアドバイス利用状況の作成"""
        advice_usage = AdviceUsage(
            user_id="user123",
            date=date(2024, 1, 1),
            usage_count=1,
            last_used_at=datetime.utcnow()
        )

        assert advice_usage.user_id == "user123"
        assert advice_usage.date == date(2024, 1, 1)
        assert advice_usage.usage_count == 1

    def test_advice_usage_to_dict(self):
        """アドバイス利用状況の辞書変換"""
        advice_usage = AdviceUsage(
            user_id="user123",
            date=date(2024, 1, 1),
            usage_count=1,
            last_used_at=datetime.utcnow()
        )

        usage_dict = advice_usage.to_dict()

        assert usage_dict["user_id"] == "user123"
        assert usage_dict["date"] == "2024-01-01"
        assert usage_dict["usage_count"] == 1


class TestFoodPropertyBased:
    """Foodモデルのプロパティベーステスト"""

    @given(
        food_id=st.text(min_size=1, max_size=50),
        name=st.text(min_size=1, max_size=100),
        calories_per_100g=st.floats(
            min_value=0,
            max_value=900,
            allow_nan=False,
            allow_infinity=False
        ),
        protein_per_100g=st.floats(
            min_value=0,
            max_value=100,
            allow_nan=False,
            allow_infinity=False
        ),
        fat_per_100g=st.floats(
            min_value=0,
            max_value=100,
            allow_nan=False,
            allow_infinity=False
        ),
        carbs_per_100g=st.floats(
            min_value=0,
            max_value=100,
            allow_nan=False,
            allow_infinity=False
        )
    )
    def test_food_required_fields_property(
        self,
        food_id,
        name,
        calories_per_100g,
        protein_per_100g,
        fat_per_100g,
        carbs_per_100g
    ):
        """
        Feature: meal-management-app, Property 4: 食品マスタの必須フィールド

        任意の食品レコードは、食品名、カロリー（100gあたり）、タンパク質（g）、
        脂質（g）、炭水化物（g）のすべてのフィールドを持つ必要があります。

        検証: 要件 2.5
        """
        # 有効なFood オブジェクトを作成
        food = Food(
            food_id=food_id,
            name=name,
            calories_per_100g=calories_per_100g,
            protein_per_100g=protein_per_100g,
            fat_per_100g=fat_per_100g,
            carbs_per_100g=carbs_per_100g,
            source=FoodSource.STANDARD
        )

        # すべての必須フィールドが存在することを確認
        assert food.food_id == food_id
        assert food.name == name
        assert food.calories_per_100g == calories_per_100g
        assert food.protein_per_100g == protein_per_100g
        assert food.fat_per_100g == fat_per_100g
        assert food.carbs_per_100g == carbs_per_100g

        # to_dict()でもすべてのフィールドが含まれることを確認
        food_dict = food.to_dict()
        assert "name" in food_dict
        assert "calories_per_100g" in food_dict
        assert "protein_per_100g" in food_dict
        assert "fat_per_100g" in food_dict
        assert "carbs_per_100g" in food_dict

        # from_dict()で復元可能であることを確認
        restored_food = Food.from_dict(food_dict)
        assert restored_food.name == name
        assert restored_food.calories_per_100g == calories_per_100g
        assert restored_food.protein_per_100g == protein_per_100g
        assert restored_food.fat_per_100g == fat_per_100g
        assert restored_food.carbs_per_100g == carbs_per_100g
