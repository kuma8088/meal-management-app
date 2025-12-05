"""
ユーザープロフィール管理ロジック

要件: 1.3, 4.3, 8.3
"""
from typing import Dict, Optional
from datetime import datetime
from .models import User, Gender, ActivityLevel
from .bmr_calculator import BMRCalculator
from .exceptions import ValidationError


class ProfileManager:
    """ユーザープロフィールを管理するクラス"""

    @staticmethod
    def create_profile(
        user_id: str,
        age: int,
        height: float,
        weight: float,
        gender: Gender,
        activity_level: ActivityLevel,
        line_user_id: Optional[str] = None,
        cognito_user_id: Optional[str] = None
    ) -> User:
        """
        ユーザープロフィールを作成し、BMRとTDEEを自動計算する

        Args:
            user_id: ユーザーID
            age: 年齢
            height: 身長（cm）
            weight: 体重（kg）
            gender: 性別
            activity_level: 活動レベル
            line_user_id: LINE User ID（オプション）
            cognito_user_id: Cognito User ID（オプション）

        Returns:
            作成されたUserオブジェクト

        Raises:
            ValidationError: 入力値が無効な場合

        要件: 4.3
        """
        # 基本バリデーション
        if not user_id:
            raise ValidationError("ユーザーIDは必須です")

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

        # BMRとTDEEを計算
        bmr_tdee = BMRCalculator.calculate_bmr_and_tdee(
            age, height, weight, gender, activity_level
        )

        # Userオブジェクトを作成
        now = datetime.now().isoformat()
        user = User(
            user_id=user_id,
            line_user_id=line_user_id,
            cognito_user_id=cognito_user_id,
            age=age,
            height=height,
            weight=weight,
            gender=gender,
            activity_level=activity_level,
            bmr=bmr_tdee["bmr"],
            tdee=bmr_tdee["tdee"],
            created_at=now,
            updated_at=now
        )

        return user

    @staticmethod
    def update_profile(
        user: User,
        age: Optional[int] = None,
        height: Optional[float] = None,
        weight: Optional[float] = None,
        gender: Optional[Gender] = None,
        activity_level: Optional[ActivityLevel] = None
    ) -> User:
        """
        ユーザープロフィールを更新し、BMRとTDEEを再計算する

        プロフィールの任意のフィールドを更新できます。
        更新があった場合、BMRとTDEEが自動的に再計算されます。

        Args:
            user: 更新するUserオブジェクト
            age: 新しい年齢（オプション）
            height: 新しい身長（オプション）
            weight: 新しい体重（オプション）
            gender: 新しい性別（オプション）
            activity_level: 新しい活動レベル（オプション）

        Returns:
            更新されたUserオブジェクト

        Raises:
            ValidationError: 入力値が無効な場合

        要件: 8.3
        """
        # フィールドを更新
        updated_age = age if age is not None else user.age
        updated_height = height if height is not None else user.height
        updated_weight = weight if weight is not None else user.weight
        updated_gender = gender if gender is not None else user.gender
        updated_activity_level = activity_level if activity_level is not None else user.activity_level

        # バリデーション
        if updated_age <= 0:
            raise ValidationError(
                "年齢は正の値である必要があります",
                details={"age": updated_age}
            )

        if updated_height <= 0:
            raise ValidationError(
                "身長は正の値である必要があります",
                details={"height": updated_height}
            )

        if updated_weight <= 0:
            raise ValidationError(
                "体重は正の値である必要があります",
                details={"weight": updated_weight}
            )

        # BMRとTDEEを再計算
        bmr_tdee = BMRCalculator.calculate_bmr_and_tdee(
            updated_age,
            updated_height,
            updated_weight,
            updated_gender,
            updated_activity_level
        )

        # Userオブジェクトを更新
        user.age = updated_age
        user.height = updated_height
        user.weight = updated_weight
        user.gender = updated_gender
        user.activity_level = updated_activity_level
        user.bmr = bmr_tdee["bmr"]
        user.tdee = bmr_tdee["tdee"]
        user.updated_at = datetime.now().isoformat()

        return user

    @staticmethod
    def get_profile_summary(user: User) -> Dict:
        """
        ユーザープロフィールのサマリーを取得する

        Args:
            user: Userオブジェクト

        Returns:
            プロフィールサマリーの辞書

        要件: 1.3
        """
        return {
            "user_id": user.user_id,
            "age": user.age,
            "height": user.height,
            "weight": user.weight,
            "gender": user.gender.value if isinstance(user.gender, Gender) else user.gender,
            "activity_level": user.activity_level.value if isinstance(user.activity_level, ActivityLevel) else user.activity_level,
            "bmr": user.bmr,
            "tdee": user.tdee,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
