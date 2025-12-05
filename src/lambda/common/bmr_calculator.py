"""
BMR/TDEE 計算ロジック

Harris-Benedict式を使用して基礎代謝率(BMR)と総消費カロリー(TDEE)を計算します。

要件: 4.1, 4.2, 4.3
"""
from typing import Dict
from .models import Gender, ActivityLevel
from .exceptions import ValidationError


class BMRCalculator:
    """BMR(基礎代謝率)とTDEE(総消費カロリー)を計算するクラス"""
    
    # 活動係数の定義
    ACTIVITY_MULTIPLIERS = {
        ActivityLevel.SEDENTARY: 1.2,      # ほとんど運動しない
        ActivityLevel.LIGHT: 1.375,        # 軽い運動
        ActivityLevel.MODERATE: 1.55,      # 中程度の運動
        ActivityLevel.ACTIVE: 1.725,       # 激しい運動
        ActivityLevel.VERY_ACTIVE: 1.9     # 非常に激しい運動
    }
    
    @staticmethod
    def calculate_bmr(
        age: int,
        height: float,
        weight: float,
        gender: Gender
    ) -> float:
        """
        Harris-Benedict式を使用してBMR(基礎代謝率)を計算する
        
        Harris-Benedict式:
        - 男性: BMR = 88.362 + (13.397 × 体重kg) + (4.799 × 身長cm) - (5.677 × 年齢)
        - 女性: BMR = 447.593 + (9.247 × 体重kg) + (3.098 × 身長cm) - (4.330 × 年齢)
        
        Args:
            age: 年齢
            height: 身長（cm）
            weight: 体重（kg）
            gender: 性別
        
        Returns:
            BMR（kcal/日）
        
        Raises:
            ValidationError: 入力値が無効な場合
        
        要件: 4.1, 8.1
        """
        # バリデーション
        if age <= 0:
            raise ValidationError(
                "年齢は正の値である必要があります",
                details={"age": age}
            )
        
        if height <= 0:
            raise ValidationError(
                "身長は正の値である必要があります",
                details={"height": height}
            )
        
        if weight <= 0:
            raise ValidationError(
                "体重は正の値である必要があります",
                details={"weight": weight}
            )
        
        # Harris-Benedict式による計算
        if gender == Gender.MALE:
            bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        elif gender == Gender.FEMALE:
            bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
        else:
            raise ValidationError(
                f"無効な性別: {gender}",
                details={"gender": gender}
            )
        
        return round(bmr, 2)
    
    @staticmethod
    def calculate_tdee(
        bmr: float,
        activity_level: ActivityLevel
    ) -> float:
        """
        活動係数を使用してTDEE(総消費カロリー)を計算する
        
        TDEE = BMR × 活動係数
        
        活動係数:
        - SEDENTARY (ほとんど運動しない): 1.2
        - LIGHT (軽い運動): 1.375
        - MODERATE (中程度の運動): 1.55
        - ACTIVE (激しい運動): 1.725
        - VERY_ACTIVE (非常に激しい運動): 1.9
        
        Args:
            bmr: 基礎代謝率（kcal/日）
            activity_level: 活動レベル
        
        Returns:
            TDEE（kcal/日）
        
        Raises:
            ValidationError: 入力値が無効な場合
        
        要件: 4.2, 8.2
        """
        # バリデーション
        if bmr < 0:
            raise ValidationError(
                "BMRは非負の値である必要があります",
                details={"bmr": bmr}
            )
        
        # 活動係数を取得
        multiplier = BMRCalculator.ACTIVITY_MULTIPLIERS.get(activity_level)
        if multiplier is None:
            raise ValidationError(
                f"無効な活動レベル: {activity_level}",
                details={"activity_level": activity_level}
            )
        
        # TDEEを計算
        tdee = bmr * multiplier
        
        return round(tdee, 2)
    
    @staticmethod
    def calculate_bmr_and_tdee(
        age: int,
        height: float,
        weight: float,
        gender: Gender,
        activity_level: ActivityLevel
    ) -> Dict[str, float]:
        """
        BMRとTDEEを一度に計算する
        
        Args:
            age: 年齢
            height: 身長（cm）
            weight: 体重（kg）
            gender: 性別
            activity_level: 活動レベル
        
        Returns:
            BMRとTDEEを含む辞書
        
        要件: 4.1, 4.2, 4.3, 8.1, 8.2, 8.3
        """
        bmr = BMRCalculator.calculate_bmr(age, height, weight, gender)
        tdee = BMRCalculator.calculate_tdee(bmr, activity_level)
        
        return {
            "bmr": bmr,
            "tdee": tdee
        }
