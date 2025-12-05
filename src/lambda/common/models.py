"""
データモデルクラス

要件: 7.1, 12.1
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Literal
from enum import Enum
import uuid

from .validation import (
    validate_required,
    validate_positive_number,
    validate_non_negative_number,
    validate_choice,
    validate_date_format
)
from .exceptions import ValidationError


# 列挙型定義
class Gender(str, Enum):
    """性別"""
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    """活動レベル"""
    SEDENTARY = "sedentary"  # ほとんど運動しない
    LIGHT = "light"  # 軽い運動
    MODERATE = "moderate"  # 中程度の運動
    ACTIVE = "active"  # 激しい運動
    VERY_ACTIVE = "very_active"  # 非常に激しい運動


class MealType(str, Enum):
    """食事タイプ"""
    BREAKFAST = "breakfast"  # 朝食
    LUNCH = "lunch"  # 昼食
    DINNER = "dinner"  # 夕食
    SNACK = "snack"  # 間食


class GoalType(str, Enum):
    """体重目標タイプ"""
    GAIN = "gain"  # 増量
    MAINTAIN = "maintain"  # 維持
    LOSE = "lose"  # 減量


class FoodSource(str, Enum):
    """食品データソース"""
    STANDARD = "STANDARD"  # 日本食品標準成分表
    OPEN_FOOD_FACTS = "OPEN_FOOD_FACTS"  # Open Food Facts
    AI_GENERATED = "AI_GENERATED"  # AI生成


@dataclass
class User:
    """
    ユーザーモデル
    
    Attributes:
        user_id: ユーザーID
        line_user_id: LINE User ID（オプション）
        cognito_user_id: Cognito User ID（オプション）
        age: 年齢
        height: 身長（cm）
        weight: 体重（kg）
        gender: 性別
        activity_level: 活動レベル
        bmr: 基礎代謝率
        tdee: 総消費カロリー
        created_at: 作成日時
        updated_at: 更新日時
    """
    user_id: str
    age: int
    height: float
    weight: float
    gender: Gender
    activity_level: ActivityLevel
    bmr: float
    tdee: float
    line_user_id: Optional[str] = None
    cognito_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初期化後のバリデーション"""
        # デフォルト値の設定
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        
        # バリデーション
        self.validate()
    
    def validate(self) -> None:
        """ユーザーデータのバリデーション"""
        validate_required(self.user_id, "user_id")
        validate_positive_number(self.age, "age")
        validate_positive_number(self.height, "height")
        validate_positive_number(self.weight, "weight")
        validate_required(self.gender, "gender")
        validate_required(self.activity_level, "activity_level")
        validate_non_negative_number(self.bmr, "bmr")
        validate_non_negative_number(self.tdee, "tdee")
        
        # 年齢の範囲チェック
        if self.age < 1 or self.age > 150:
            raise ValidationError(
                "年齢は1から150の範囲である必要があります",
                details={"field": "age", "value": self.age}
            )
        
        # 身長の範囲チェック
        if self.height < 50 or self.height > 300:
            raise ValidationError(
                "身長は50cmから300cmの範囲である必要があります",
                details={"field": "height", "value": self.height}
            )
        
        # 体重の範囲チェック
        if self.weight < 10 or self.weight > 500:
            raise ValidationError(
                "体重は10kgから500kgの範囲である必要があります",
                details={"field": "weight", "value": self.weight}
            )
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "user_id": self.user_id,
            "line_user_id": self.line_user_id,
            "cognito_user_id": self.cognito_user_id,
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "gender": self.gender.value if isinstance(self.gender, Gender) else self.gender,
            "activity_level": self.activity_level.value if isinstance(self.activity_level, ActivityLevel) else self.activity_level,
            "bmr": self.bmr,
            "tdee": self.tdee,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """辞書からインスタンスを作成"""
        # Enum型への変換
        if "gender" in data and isinstance(data["gender"], str):
            data["gender"] = Gender(data["gender"])
        if "activity_level" in data and isinstance(data["activity_level"], str):
            data["activity_level"] = ActivityLevel(data["activity_level"])
        
        # 日時型への変換
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        return cls(**data)


@dataclass
class MealFood:
    """
    食事に含まれる食品
    
    Attributes:
        food_id: 食品ID
        amount: 量（グラム）
    """
    food_id: str
    amount: float
    
    def __post_init__(self):
        """初期化後のバリデーション"""
        self.validate()
    
    def validate(self) -> None:
        """食品データのバリデーション"""
        validate_required(self.food_id, "food_id")
        validate_positive_number(self.amount, "amount")
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "food_id": self.food_id,
            "amount": self.amount
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MealFood":
        """辞書からインスタンスを作成"""
        return cls(**data)


@dataclass
class Meal:
    """
    食事記録モデル
    
    Attributes:
        meal_id: 食事記録ID
        user_id: ユーザーID
        meal_type: 食事タイプ
        foods: 食品リスト
        total_calories: 総カロリー
        total_protein: 総タンパク質（g）
        total_fat: 総脂質（g）
        total_carbs: 総炭水化物（g）
        timestamp: タイムスタンプ
        created_at: 作成日時
    """
    meal_id: str
    user_id: str
    meal_type: MealType
    foods: List[MealFood]
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    timestamp: datetime
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初期化後のバリデーション"""
        # デフォルト値の設定
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        
        # MealFoodオブジェクトへの変換
        if self.foods and isinstance(self.foods[0], dict):
            self.foods = [MealFood.from_dict(f) for f in self.foods]
        
        # バリデーション
        self.validate()
    
    def validate(self) -> None:
        """食事記録データのバリデーション"""
        validate_required(self.meal_id, "meal_id")
        validate_required(self.user_id, "user_id")
        validate_required(self.meal_type, "meal_type")
        validate_non_negative_number(self.total_calories, "total_calories")
        validate_non_negative_number(self.total_protein, "total_protein")
        validate_non_negative_number(self.total_fat, "total_fat")
        validate_non_negative_number(self.total_carbs, "total_carbs")
        
        # 食品リストの検証
        if not self.foods or len(self.foods) == 0:
            raise ValidationError(
                "食品リストは少なくとも1つの食品を含む必要があります",
                details={"field": "foods"}
            )
        
        # 各食品のバリデーション
        for food in self.foods:
            food.validate()
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "meal_id": self.meal_id,
            "user_id": self.user_id,
            "meal_type": self.meal_type.value if isinstance(self.meal_type, MealType) else self.meal_type,
            "foods": [f.to_dict() for f in self.foods],
            "total_calories": self.total_calories,
            "total_protein": self.total_protein,
            "total_fat": self.total_fat,
            "total_carbs": self.total_carbs,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Meal":
        """辞書からインスタンスを作成"""
        # Enum型への変換
        if "meal_type" in data and isinstance(data["meal_type"], str):
            data["meal_type"] = MealType(data["meal_type"])
        
        # 日時型への変換
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        # MealFoodオブジェクトへの変換
        if "foods" in data and data["foods"]:
            data["foods"] = [
                MealFood.from_dict(f) if isinstance(f, dict) else f
                for f in data["foods"]
            ]
        
        return cls(**data)


@dataclass
class Food:
    """
    食品マスタモデル
    
    Attributes:
        food_id: 食品ID
        name: 食品名
        calories_per_100g: カロリー（100gあたり）
        protein_per_100g: タンパク質（100gあたり、g）
        fat_per_100g: 脂質（100gあたり、g）
        carbs_per_100g: 炭水化物（100gあたり、g）
        jan_code: JANコード（オプション）
        source: データソース
        created_at: 作成日時
        updated_at: 更新日時
    """
    food_id: str
    name: str
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    source: FoodSource
    jan_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初期化後のバリデーション"""
        # デフォルト値の設定
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        
        # バリデーション
        self.validate()
    
    def validate(self) -> None:
        """食品データのバリデーション"""
        validate_required(self.food_id, "food_id")
        validate_required(self.name, "name")
        validate_non_negative_number(self.calories_per_100g, "calories_per_100g")
        validate_non_negative_number(self.protein_per_100g, "protein_per_100g")
        validate_non_negative_number(self.fat_per_100g, "fat_per_100g")
        validate_non_negative_number(self.carbs_per_100g, "carbs_per_100g")
        validate_required(self.source, "source")
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "food_id": self.food_id,
            "name": self.name,
            "calories_per_100g": self.calories_per_100g,
            "protein_per_100g": self.protein_per_100g,
            "fat_per_100g": self.fat_per_100g,
            "carbs_per_100g": self.carbs_per_100g,
            "jan_code": self.jan_code,
            "source": self.source.value if isinstance(self.source, FoodSource) else self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Food":
        """辞書からインスタンスを作成"""
        # Enum型への変換
        if "source" in data and isinstance(data["source"], str):
            data["source"] = FoodSource(data["source"])
        
        # 日時型への変換
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        return cls(**data)


@dataclass
class Goal:
    """
    体重目標モデル
    
    Attributes:
        goal_id: 目標ID
        user_id: ユーザーID
        current_weight: 現在の体重（kg）
        target_weight: 目標体重（kg）
        target_date: 目標日
        goal_type: 目標タイプ
        daily_calorie_adjustment: 1日あたりのカロリー調整量
        target_calories: 目標カロリー
        recommended_protein: 推奨タンパク質（g）
        recommended_fat: 推奨脂質（g）
        recommended_carbs: 推奨炭水化物（g）
        recommended_exercise_minutes: 推奨運動時間（分）
        created_at: 作成日時
        updated_at: 更新日時
    """
    goal_id: str
    user_id: str
    current_weight: float
    target_weight: float
    target_date: date
    goal_type: GoalType
    daily_calorie_adjustment: float
    target_calories: float
    recommended_protein: float
    recommended_fat: float
    recommended_carbs: float
    recommended_exercise_minutes: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初期化後のバリデーション"""
        # デフォルト値の設定
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        
        # バリデーション
        self.validate()
    
    def validate(self) -> None:
        """目標データのバリデーション"""
        validate_required(self.goal_id, "goal_id")
        validate_required(self.user_id, "user_id")
        validate_positive_number(self.current_weight, "current_weight")
        validate_positive_number(self.target_weight, "target_weight")
        validate_required(self.target_date, "target_date")
        validate_required(self.goal_type, "goal_type")
        validate_non_negative_number(self.target_calories, "target_calories")
        validate_non_negative_number(self.recommended_protein, "recommended_protein")
        validate_non_negative_number(self.recommended_fat, "recommended_fat")
        validate_non_negative_number(self.recommended_carbs, "recommended_carbs")
        validate_non_negative_number(self.recommended_exercise_minutes, "recommended_exercise_minutes")
        
        # 体重の範囲チェック
        if self.current_weight < 10 or self.current_weight > 500:
            raise ValidationError(
                "現在の体重は10kgから500kgの範囲である必要があります",
                details={"field": "current_weight", "value": self.current_weight}
            )
        
        if self.target_weight < 10 or self.target_weight > 500:
            raise ValidationError(
                "目標体重は10kgから500kgの範囲である必要があります",
                details={"field": "target_weight", "value": self.target_weight}
            )
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "goal_id": self.goal_id,
            "user_id": self.user_id,
            "current_weight": self.current_weight,
            "target_weight": self.target_weight,
            "target_date": self.target_date.isoformat() if isinstance(self.target_date, date) else self.target_date,
            "goal_type": self.goal_type.value if isinstance(self.goal_type, GoalType) else self.goal_type,
            "daily_calorie_adjustment": self.daily_calorie_adjustment,
            "target_calories": self.target_calories,
            "recommended_protein": self.recommended_protein,
            "recommended_fat": self.recommended_fat,
            "recommended_carbs": self.recommended_carbs,
            "recommended_exercise_minutes": self.recommended_exercise_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Goal":
        """辞書からインスタンスを作成"""
        # Enum型への変換
        if "goal_type" in data and isinstance(data["goal_type"], str):
            data["goal_type"] = GoalType(data["goal_type"])
        
        # 日付型への変換
        if "target_date" in data and isinstance(data["target_date"], str):
            data["target_date"] = date.fromisoformat(data["target_date"])
        
        # 日時型への変換
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        return cls(**data)


@dataclass
class AdviceUsage:
    """
    アドバイス利用状況モデル
    
    Attributes:
        user_id: ユーザーID
        date: 日付
        usage_count: 利用回数
        last_used_at: 最終利用日時
    """
    user_id: str
    date: date
    usage_count: int
    last_used_at: datetime
    
    def __post_init__(self):
        """初期化後のバリデーション"""
        self.validate()
    
    def validate(self) -> None:
        """利用状況データのバリデーション"""
        validate_required(self.user_id, "user_id")
        validate_required(self.date, "date")
        validate_non_negative_number(self.usage_count, "usage_count")
        validate_required(self.last_used_at, "last_used_at")
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "user_id": self.user_id,
            "date": self.date.isoformat() if isinstance(self.date, date) else self.date,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AdviceUsage":
        """辞書からインスタンスを作成"""
        # 日付型への変換
        if "date" in data and isinstance(data["date"], str):
            data["date"] = date.fromisoformat(data["date"])
        
        # 日時型への変換
        if "last_used_at" in data and isinstance(data["last_used_at"], str):
            data["last_used_at"] = datetime.fromisoformat(data["last_used_at"])
        
        return cls(**data)
