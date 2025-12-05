"""
体重目標管理ロジックのテスト

Property 16, 17, 18, 19プロパティテスト、およびユニットテスト
"""
import pytest
import sys
from pathlib import Path
from datetime import date, timedelta
from hypothesis import given, strategies as st, assume

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    GoalCalculator,
    GoalType,
    ValidationError,
)


class TestGoalCalculatorPropertyBased:
    """体重目標管理のプロパティベーステスト"""

    @given(
        current_weight=st.floats(min_value=40, max_value=150, allow_nan=False, allow_infinity=False),
        target_weight=st.floats(min_value=40, max_value=150, allow_nan=False, allow_infinity=False),
        days_to_target=st.integers(min_value=7, max_value=365)
    )
    def test_calorie_adjustment_calculation_property(
        self,
        current_weight,
        target_weight,
        days_to_target
    ):
        """
        Feature: meal-management-app, Property 16: カロリー調整量の計算

        任意の現在の体重、目標体重、目標時期の組み合わせに対して、
        システムは1日あたりの必要カロリー調整量を正しく計算する必要があります。

        計算式: カロリー調整量 = (目標体重 - 現在体重) × 7700 kcal/kg ÷ 日数

        検証: 要件 9.2
        """
        # 極端な体重変化を避ける（50kg以上の変化は非現実的）
        weight_difference = abs(target_weight - current_weight)
        assume(weight_difference <= 50)

        # 浮動小数点誤差による微小な体重差を除外（0.001kg未満はスキップ）
        assume(weight_difference >= 0.001)

        # テスト用の日付を設定
        current_date = date.today()
        target_date = current_date + timedelta(days=days_to_target)

        # カロリー調整量を計算
        daily_adjustment = GoalCalculator.calculate_daily_calorie_adjustment(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # 期待値を計算
        weight_difference = target_weight - current_weight
        total_calorie_adjustment = weight_difference * 7700.0
        expected_daily_adjustment = round(total_calorie_adjustment / days_to_target, 2)

        # カロリー調整量が正確に計算されていることを確認
        assert daily_adjustment == expected_daily_adjustment

        # 増量の場合は正の値、減量の場合は負の値、維持の場合は0に近い
        if target_weight > current_weight:
            assert daily_adjustment > 0
        elif target_weight < current_weight:
            assert daily_adjustment < 0
        else:
            assert abs(daily_adjustment) < 0.01

    @given(
        tdee=st.floats(min_value=1000, max_value=4000, allow_nan=False, allow_infinity=False),
        daily_adjustment=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    def test_target_calories_calculation_property(self, tdee, daily_adjustment):
        """
        Feature: meal-management-app, Property 17: 目標カロリーの計算

        任意のTDEEとカロリー調整量の組み合わせに対して、
        目標カロリーはTDEEに調整量を加算または減算した値と等しい必要があります。

        計算式: 目標カロリー = TDEE + カロリー調整量

        検証: 要件 9.3
        """
        # TDEEが負にならないように調整
        assume(tdee + daily_adjustment >= 0)

        # 目標カロリーを計算
        target_calories = GoalCalculator.calculate_target_calories(tdee, daily_adjustment)

        # 期待値を計算
        expected_target_calories = round(tdee + daily_adjustment, 2)

        # 目標カロリーが正確に計算されていることを確認
        assert target_calories == expected_target_calories

        # 目標カロリーは非負
        assert target_calories >= 0

        # 関係性の検証（浮動小数点誤差を考慮）
        if daily_adjustment > 0.01:
            assert target_calories > tdee
        elif daily_adjustment < -0.01:
            assert target_calories < tdee
        else:
            assert abs(target_calories - tdee) < 0.02

    @given(
        target_calories=st.floats(min_value=1000, max_value=4000, allow_nan=False, allow_infinity=False),
        goal_type=st.sampled_from([GoalType.GAIN, GoalType.MAINTAIN, GoalType.LOSE])
    )
    def test_pfc_balance_calculation_property(self, target_calories, goal_type):
        """
        Feature: meal-management-app, Property 18: PFCバランスの計算

        任意の目標カロリーに対して、システムは推奨されるタンパク質、脂質、
        炭水化物のバランスを計算する必要があります。

        検証: 要件 9.4
        """
        # PFCバランスを計算
        pfc = GoalCalculator.calculate_pfc_balance(target_calories, goal_type)

        # すべてのフィールドが含まれることを確認
        assert "protein" in pfc
        assert "fat" in pfc
        assert "carbs" in pfc

        # すべての値が非負であることを確認
        assert pfc["protein"] >= 0
        assert pfc["fat"] >= 0
        assert pfc["carbs"] >= 0

        # PFCの合計カロリーが目標カロリーに近いことを確認
        protein_calories = pfc["protein"] * 4.0
        fat_calories = pfc["fat"] * 9.0
        carbs_calories = pfc["carbs"] * 4.0
        total_pfc_calories = protein_calories + fat_calories + carbs_calories

        # 誤差1%以内
        assert abs(total_pfc_calories - target_calories) < target_calories * 0.01

        # 目標タイプごとのPFC比率を検証
        protein_ratio = protein_calories / target_calories
        fat_ratio = fat_calories / target_calories
        carbs_ratio = carbs_calories / target_calories

        if goal_type == GoalType.GAIN:
            # 増量: タンパク質30%, 脂質25%, 炭水化物45%
            assert abs(protein_ratio - 0.30) < 0.01
            assert abs(fat_ratio - 0.25) < 0.01
            assert abs(carbs_ratio - 0.45) < 0.01
        elif goal_type == GoalType.MAINTAIN:
            # 維持: タンパク質25%, 脂質25%, 炭水化物50%
            assert abs(protein_ratio - 0.25) < 0.01
            assert abs(fat_ratio - 0.25) < 0.01
            assert abs(carbs_ratio - 0.50) < 0.01
        elif goal_type == GoalType.LOSE:
            # 減量: タンパク質30%, 脂質20%, 炭水化物50%
            assert abs(protein_ratio - 0.30) < 0.01
            assert abs(fat_ratio - 0.20) < 0.01
            assert abs(carbs_ratio - 0.50) < 0.01

    @given(
        current_weight=st.floats(min_value=50, max_value=100, allow_nan=False, allow_infinity=False),
        weight_change=st.floats(min_value=1, max_value=20, allow_nan=False, allow_infinity=False),
        weeks=st.floats(min_value=1, max_value=52, allow_nan=False, allow_infinity=False)
    )
    def test_unrealistic_goal_warning_property(self, current_weight, weight_change, weeks):
        """
        Feature: meal-management-app, Property 19: 非現実的な目標の警告

        任意の目標が週あたり0.5kgを超える体重変化を要求する場合、
        システムは警告メッセージを表示する必要があります。

        検証: 要件 9.6
        """
        # テスト用の日付を設定
        current_date = date.today()
        days_to_target = int(weeks * 7)
        target_date = current_date + timedelta(days=days_to_target)

        # 目標体重を設定（減量ケース）
        target_weight = current_weight - weight_change

        # 警告をチェック
        warning = GoalCalculator.check_unrealistic_goal(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # 週あたりの体重変化を計算
        weekly_change = weight_change / weeks

        # 非現実的な目標の場合は警告が表示されることを確認（浮動小数点誤差を考慮）
        if weekly_change > 0.501:  # 浮動小数点誤差を考慮して0.501
            assert warning is not None
            assert "警告" in warning
            assert "健康的なペース" in warning
        elif weekly_change < 0.499:  # 明らかに安全なペース
            assert warning is None
        # 0.499から0.501の間は境界値なのでスキップ


class TestGoalCalculator:
    """体重目標管理クラスのユニットテスト"""

    def test_calorie_adjustment_gain_scenario(self):
        """増量シナリオのカロリー調整量計算"""
        current_weight = 60.0
        target_weight = 65.0  # 5kg増量
        current_date = date(2024, 1, 1)
        target_date = date(2024, 4, 1)  # 91日後

        daily_adjustment = GoalCalculator.calculate_daily_calorie_adjustment(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # 5kg × 7700kcal/kg ÷ 91日 = 423.08 kcal/日
        expected = round((5.0 * 7700) / 91, 2)
        assert daily_adjustment == expected
        assert daily_adjustment > 0  # 増量なので正の値

    def test_calorie_adjustment_lose_scenario(self):
        """減量シナリオのカロリー調整量計算"""
        current_weight = 70.0
        target_weight = 65.0  # 5kg減量
        current_date = date(2024, 1, 1)
        target_date = date(2024, 4, 1)  # 91日後

        daily_adjustment = GoalCalculator.calculate_daily_calorie_adjustment(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # -5kg × 7700kcal/kg ÷ 91日 = -423.08 kcal/日
        expected = round((-5.0 * 7700) / 91, 2)
        assert daily_adjustment == expected
        assert daily_adjustment < 0  # 減量なので負の値

    def test_calorie_adjustment_maintain_scenario(self):
        """体重維持シナリオのカロリー調整量計算"""
        current_weight = 65.0
        target_weight = 65.0  # 維持
        current_date = date(2024, 1, 1)
        target_date = date(2024, 4, 1)

        daily_adjustment = GoalCalculator.calculate_daily_calorie_adjustment(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # 0kg × 7700kcal/kg ÷ 91日 = 0 kcal/日
        assert daily_adjustment == 0.0

    def test_calorie_adjustment_invalid_weight(self):
        """無効な体重でのバリデーション"""
        current_date = date(2024, 1, 1)
        target_date = date(2024, 4, 1)

        # 負の現在体重
        with pytest.raises(ValidationError):
            GoalCalculator.calculate_daily_calorie_adjustment(
                -60.0, 65.0, target_date, current_date
            )

        # 負の目標体重
        with pytest.raises(ValidationError):
            GoalCalculator.calculate_daily_calorie_adjustment(
                60.0, -65.0, target_date, current_date
            )

    def test_calorie_adjustment_past_target_date(self):
        """過去の目標日でのバリデーション"""
        current_date = date(2024, 4, 1)
        target_date = date(2024, 1, 1)  # 過去の日付

        with pytest.raises(ValidationError):
            GoalCalculator.calculate_daily_calorie_adjustment(
                60.0, 65.0, target_date, current_date
            )

    def test_target_calories_basic(self):
        """基本的な目標カロリー計算"""
        tdee = 2000.0
        daily_adjustment = 300.0

        target_calories = GoalCalculator.calculate_target_calories(tdee, daily_adjustment)

        assert target_calories == 2300.0

    def test_target_calories_negative_adjustment(self):
        """マイナス調整の目標カロリー計算"""
        tdee = 2000.0
        daily_adjustment = -500.0

        target_calories = GoalCalculator.calculate_target_calories(tdee, daily_adjustment)

        assert target_calories == 1500.0

    def test_target_calories_invalid_negative_result(self):
        """目標カロリーが負になる場合のバリデーション"""
        tdee = 1000.0
        daily_adjustment = -1500.0

        with pytest.raises(ValidationError):
            GoalCalculator.calculate_target_calories(tdee, daily_adjustment)

    def test_pfc_balance_gain(self):
        """増量時のPFCバランス計算"""
        target_calories = 2500.0

        pfc = GoalCalculator.calculate_pfc_balance(target_calories, GoalType.GAIN)

        # タンパク質30%, 脂質25%, 炭水化物45%
        expected_protein = round((2500.0 * 0.30) / 4.0, 2)
        expected_fat = round((2500.0 * 0.25) / 9.0, 2)
        expected_carbs = round((2500.0 * 0.45) / 4.0, 2)

        assert pfc["protein"] == expected_protein
        assert pfc["fat"] == expected_fat
        assert pfc["carbs"] == expected_carbs

    def test_pfc_balance_maintain(self):
        """維持時のPFCバランス計算"""
        target_calories = 2000.0

        pfc = GoalCalculator.calculate_pfc_balance(target_calories, GoalType.MAINTAIN)

        # タンパク質25%, 脂質25%, 炭水化物50%
        expected_protein = round((2000.0 * 0.25) / 4.0, 2)
        expected_fat = round((2000.0 * 0.25) / 9.0, 2)
        expected_carbs = round((2000.0 * 0.50) / 4.0, 2)

        assert pfc["protein"] == expected_protein
        assert pfc["fat"] == expected_fat
        assert pfc["carbs"] == expected_carbs

    def test_pfc_balance_lose(self):
        """減量時のPFCバランス計算"""
        target_calories = 1800.0

        pfc = GoalCalculator.calculate_pfc_balance(target_calories, GoalType.LOSE)

        # タンパク質30%, 脂質20%, 炭水化物50%
        expected_protein = round((1800.0 * 0.30) / 4.0, 2)
        expected_fat = round((1800.0 * 0.20) / 9.0, 2)
        expected_carbs = round((1800.0 * 0.50) / 4.0, 2)

        assert pfc["protein"] == expected_protein
        assert pfc["fat"] == expected_fat
        assert pfc["carbs"] == expected_carbs

    def test_recommended_exercise_for_weight_loss(self):
        """減量時の推奨運動量計算"""
        daily_adjustment = -500.0  # 500kcal減量

        exercise_minutes = GoalCalculator.calculate_recommended_exercise(daily_adjustment)

        # カロリー調整量の30%を運動で補う: 500 * 0.3 = 150kcal
        # 運動による消費率 5kcal/分: 150 / 5 = 30分
        assert exercise_minutes == 30

    def test_recommended_exercise_for_weight_gain(self):
        """増量時の推奨運動量計算"""
        daily_adjustment = 300.0  # 増量

        exercise_minutes = GoalCalculator.calculate_recommended_exercise(daily_adjustment)

        # 増量時は運動推奨なし
        assert exercise_minutes == 0

    def test_unrealistic_goal_warning_triggered(self):
        """非現実的な目標での警告発生"""
        current_weight = 70.0
        target_weight = 60.0  # 10kg減量
        current_date = date(2024, 1, 1)
        target_date = date(2024, 2, 1)  # 31日後（約4.4週間）

        warning = GoalCalculator.check_unrealistic_goal(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # 週あたり約2.26kgの減量 > 0.5kg
        assert warning is not None
        assert "警告" in warning
        assert "健康的なペース" in warning

    def test_unrealistic_goal_no_warning(self):
        """健康的な目標での警告なし"""
        current_weight = 70.0
        target_weight = 68.0  # 2kg減量
        current_date = date(2024, 1, 1)
        target_date = date(2024, 2, 15)  # 45日後（約6.4週間）

        warning = GoalCalculator.check_unrealistic_goal(
            current_weight,
            target_weight,
            target_date,
            current_date
        )

        # 週あたり約0.31kgの減量 < 0.5kg
        assert warning is None

    def test_calculate_goal_comprehensive(self):
        """体重目標の総合計算"""
        current_weight = 65.0
        target_weight = 70.0  # 5kg増量
        current_date = date(2024, 1, 1)
        target_date = date(2024, 7, 1)  # 182日後（約26週間）
        tdee = 2200.0

        result = GoalCalculator.calculate_goal(
            current_weight,
            target_weight,
            target_date,
            tdee,
            GoalType.GAIN,
            current_date
        )

        # すべてのフィールドが含まれることを確認
        assert "daily_calorie_adjustment" in result
        assert "target_calories" in result
        assert "recommended_protein" in result
        assert "recommended_fat" in result
        assert "recommended_carbs" in result
        assert "recommended_exercise_minutes" in result
        assert "warning" in result

        # カロリー調整量が正の値（増量）
        assert result["daily_calorie_adjustment"] > 0

        # 目標カロリーがTDEEより大きい
        assert result["target_calories"] > tdee

        # PFCバランスが設定されている
        assert result["recommended_protein"] > 0
        assert result["recommended_fat"] > 0
        assert result["recommended_carbs"] > 0

        # 増量なので運動推奨なし
        assert result["recommended_exercise_minutes"] == 0

        # 健康的なペース（週あたり約0.19kg）なので警告なし
        assert result["warning"] is None

    def test_calculate_goal_with_warning(self):
        """警告付きの体重目標計算"""
        current_weight = 80.0
        target_weight = 70.0  # 10kg減量
        current_date = date(2024, 1, 1)
        target_date = date(2024, 3, 1)  # 60日後（約8.6週間）
        tdee = 2400.0

        result = GoalCalculator.calculate_goal(
            current_weight,
            target_weight,
            target_date,
            tdee,
            GoalType.LOSE,
            current_date
        )

        # カロリー調整量が負の値（減量）
        assert result["daily_calorie_adjustment"] < 0

        # 目標カロリーがTDEEより小さい
        assert result["target_calories"] < tdee

        # 減量なので運動推奨あり
        assert result["recommended_exercise_minutes"] > 0

        # 週あたり約1.16kgの減量 > 0.5kg → 警告あり
        assert result["warning"] is not None
        assert "警告" in result["warning"]
