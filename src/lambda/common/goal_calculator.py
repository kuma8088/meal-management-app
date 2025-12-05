"""
体重目標管理と栄養計画の計算ロジック

要件: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""
from typing import Dict, Optional
from datetime import datetime, date
from .models import GoalType
from .exceptions import ValidationError


class GoalCalculator:
    """体重目標管理と目標カロリーを計算するクラス"""

    # 1kgの体重変化に必要なカロリー
    CALORIES_PER_KG = 7700.0

    # 健康的な体重変化の上限（週あたりkg）
    SAFE_WEEKLY_CHANGE_KG = 0.5

    # PFCバランスの推奨割合
    PROTEIN_RATIO_MIN = 0.20  # タンパク質: 20-30%
    PROTEIN_RATIO_MAX = 0.30
    FAT_RATIO_MIN = 0.20      # 脂質: 20-30%
    FAT_RATIO_MAX = 0.30
    CARBS_RATIO_MIN = 0.40    # 炭水化物: 40-60%
    CARBS_RATIO_MAX = 0.60

    # 栄養素のカロリー換算
    PROTEIN_CALORIES_PER_G = 4.0
    FAT_CALORIES_PER_G = 9.0
    CARBS_CALORIES_PER_G = 4.0

    @staticmethod
    def calculate_daily_calorie_adjustment(
        current_weight: float,
        target_weight: float,
        target_date: date,
        current_date: Optional[date] = None
    ) -> float:
        """
        1日あたりの必要カロリー調整量を計算する

        カロリー調整量 = (目標体重 - 現在体重) × 7700 kcal/kg ÷ 日数

        Args:
            current_weight: 現在の体重（kg）
            target_weight: 目標体重（kg）
            target_date: 目標達成日
            current_date: 現在の日付（省略時は今日）

        Returns:
            1日あたりのカロリー調整量（kcal/日）
            プラス: 増量、マイナス: 減量

        Raises:
            ValidationError: 入力値が無効な場合

        要件: 9.2
        """
        # バリデーション
        if current_weight <= 0:
            raise ValidationError(
                "現在の体重は正の値である必要があります",
                details={"current_weight": current_weight}
            )

        if target_weight <= 0:
            raise ValidationError(
                "目標体重は正の値である必要があります",
                details={"target_weight": target_weight}
            )

        if current_date is None:
            current_date = date.today()

        # 日数を計算
        days_to_target = (target_date - current_date).days

        if days_to_target <= 0:
            raise ValidationError(
                "目標日は未来の日付である必要があります",
                details={
                    "target_date": target_date.isoformat(),
                    "current_date": current_date.isoformat()
                }
            )

        # 体重差分
        weight_difference = target_weight - current_weight

        # 総カロリー調整量
        total_calorie_adjustment = weight_difference * GoalCalculator.CALORIES_PER_KG

        # 1日あたりのカロリー調整量
        daily_adjustment = total_calorie_adjustment / days_to_target

        return round(daily_adjustment, 2)

    @staticmethod
    def calculate_target_calories(
        tdee: float,
        daily_calorie_adjustment: float
    ) -> float:
        """
        目標カロリーを計算する

        目標カロリー = TDEE + カロリー調整量

        Args:
            tdee: 総消費カロリー（kcal/日）
            daily_calorie_adjustment: 1日あたりのカロリー調整量（kcal/日）

        Returns:
            目標カロリー（kcal/日）

        Raises:
            ValidationError: 入力値が無効な場合

        要件: 9.3
        """
        # バリデーション
        if tdee < 0:
            raise ValidationError(
                "TDEEは非負の値である必要があります",
                details={"tdee": tdee}
            )

        # 目標カロリーを計算
        target_calories = tdee + daily_calorie_adjustment

        # 目標カロリーが負にならないようにする
        if target_calories < 0:
            raise ValidationError(
                "目標カロリーが負の値になります。目標設定を見直してください",
                details={
                    "tdee": tdee,
                    "daily_calorie_adjustment": daily_calorie_adjustment,
                    "target_calories": target_calories
                }
            )

        return round(target_calories, 2)

    @staticmethod
    def calculate_pfc_balance(
        target_calories: float,
        goal_type: GoalType
    ) -> Dict[str, float]:
        """
        推奨されるPFC（タンパク質・脂質・炭水化物）バランスを計算する

        目標タイプに応じてPFC比率を調整:
        - 増量: タンパク質30%, 脂質25%, 炭水化物45%
        - 維持: タンパク質25%, 脂質25%, 炭水化物50%
        - 減量: タンパク質30%, 脂質20%, 炭水化物50%

        Args:
            target_calories: 目標カロリー（kcal/日）
            goal_type: 目標タイプ

        Returns:
            推奨PFCの辞書（protein, fat, carbs in grams）

        Raises:
            ValidationError: 入力値が無効な場合

        要件: 9.4
        """
        # バリデーション
        if target_calories < 0:
            raise ValidationError(
                "目標カロリーは非負の値である必要があります",
                details={"target_calories": target_calories}
            )

        # 目標タイプに応じたPFC比率を設定
        if goal_type == GoalType.GAIN:
            # 増量: タンパク質多め、炭水化物もしっかり
            protein_ratio = 0.30
            fat_ratio = 0.25
            carbs_ratio = 0.45
        elif goal_type == GoalType.MAINTAIN:
            # 維持: バランス型
            protein_ratio = 0.25
            fat_ratio = 0.25
            carbs_ratio = 0.50
        elif goal_type == GoalType.LOSE:
            # 減量: タンパク質多め、脂質控えめ
            protein_ratio = 0.30
            fat_ratio = 0.20
            carbs_ratio = 0.50
        else:
            raise ValidationError(
                f"無効な目標タイプ: {goal_type}",
                details={"goal_type": goal_type}
            )

        # カロリーからグラム数を計算
        protein_calories = target_calories * protein_ratio
        fat_calories = target_calories * fat_ratio
        carbs_calories = target_calories * carbs_ratio

        protein_grams = protein_calories / GoalCalculator.PROTEIN_CALORIES_PER_G
        fat_grams = fat_calories / GoalCalculator.FAT_CALORIES_PER_G
        carbs_grams = carbs_calories / GoalCalculator.CARBS_CALORIES_PER_G

        return {
            "protein": round(protein_grams, 2),
            "fat": round(fat_grams, 2),
            "carbs": round(carbs_grams, 2)
        }

    @staticmethod
    def calculate_recommended_exercise(
        daily_calorie_adjustment: float,
        exercise_calorie_burn_rate: float = 5.0
    ) -> int:
        """
        推奨運動量を計算する

        カロリー調整量の一部を運動で補うための推奨運動時間を計算。
        減量の場合のみ運動を推奨。

        Args:
            daily_calorie_adjustment: 1日あたりのカロリー調整量（kcal/日）
            exercise_calorie_burn_rate: 運動によるカロリー消費率（kcal/分）

        Returns:
            推奨運動時間（分/日）

        要件: 9.5
        """
        # 減量の場合のみ運動を推奨
        if daily_calorie_adjustment >= 0:
            return 0

        # カロリー調整量の30%を運動で補うと仮定
        exercise_calorie_target = abs(daily_calorie_adjustment) * 0.3

        # 運動時間を計算
        exercise_minutes = exercise_calorie_target / exercise_calorie_burn_rate

        return round(exercise_minutes)

    @staticmethod
    def check_unrealistic_goal(
        current_weight: float,
        target_weight: float,
        target_date: date,
        current_date: Optional[date] = None
    ) -> Optional[str]:
        """
        非現実的な目標をチェックし、警告メッセージを返す

        健康的な体重変化の上限: 週あたり0.5kg

        Args:
            current_weight: 現在の体重（kg）
            target_weight: 目標体重（kg）
            target_date: 目標達成日
            current_date: 現在の日付（省略時は今日）

        Returns:
            警告メッセージ（問題がない場合はNone）

        要件: 9.6
        """
        if current_date is None:
            current_date = date.today()

        # 日数を計算
        days_to_target = (target_date - current_date).days

        if days_to_target <= 0:
            return "目標日は未来の日付である必要があります"

        # 週数を計算
        weeks_to_target = days_to_target / 7.0

        # 体重差分
        weight_difference = abs(target_weight - current_weight)

        # 週あたりの体重変化
        weekly_change = weight_difference / weeks_to_target

        # 非現実的な目標かチェック
        if weekly_change > GoalCalculator.SAFE_WEEKLY_CHANGE_KG:
            goal_action = "増量" if target_weight > current_weight else "減量"
            safe_weeks = weight_difference / GoalCalculator.SAFE_WEEKLY_CHANGE_KG
            safe_days = round(safe_weeks * 7)

            return (
                f"警告: この目標は週あたり{weekly_change:.2f}kgの{goal_action}が必要です。"
                f"健康的なペース（週あたり{GoalCalculator.SAFE_WEEKLY_CHANGE_KG}kg以内）を推奨します。"
                f"推奨期間: 約{safe_days}日以上"
            )

        return None

    @staticmethod
    def calculate_goal(
        current_weight: float,
        target_weight: float,
        target_date: date,
        tdee: float,
        goal_type: GoalType,
        current_date: Optional[date] = None
    ) -> Dict:
        """
        体重目標に関するすべての計算を一度に実行する

        Args:
            current_weight: 現在の体重（kg）
            target_weight: 目標体重（kg）
            target_date: 目標達成日
            tdee: 総消費カロリー（kcal/日）
            goal_type: 目標タイプ
            current_date: 現在の日付（省略時は今日）

        Returns:
            目標に関する計算結果の辞書

        要件: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
        """
        # 1日あたりのカロリー調整量を計算
        daily_calorie_adjustment = GoalCalculator.calculate_daily_calorie_adjustment(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # 目標カロリーを計算
        target_calories = GoalCalculator.calculate_target_calories(
            tdee,
            daily_calorie_adjustment
        )

        # 推奨PFCバランスを計算
        pfc = GoalCalculator.calculate_pfc_balance(target_calories, goal_type)

        # 推奨運動量を計算
        recommended_exercise_minutes = GoalCalculator.calculate_recommended_exercise(
            daily_calorie_adjustment
        )

        # 非現実的な目標をチェック
        warning = GoalCalculator.check_unrealistic_goal(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        return {
            "daily_calorie_adjustment": daily_calorie_adjustment,
            "target_calories": target_calories,
            "recommended_protein": pfc["protein"],
            "recommended_fat": pfc["fat"],
            "recommended_carbs": pfc["carbs"],
            "recommended_exercise_minutes": recommended_exercise_minutes,
            "warning": warning
        }
