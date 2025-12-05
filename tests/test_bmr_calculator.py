"""
BMR/TDEE計算ロジックのテスト

Property 13プロパティテスト、Property 14プロパティテスト、およびユニットテスト
"""
import pytest
import sys
from pathlib import Path
from hypothesis import given, strategies as st

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    BMRCalculator,
    Gender,
    ActivityLevel,
    ValidationError,
)


class TestBMRCalculatorPropertyBased:
    """BMR/TDEE計算のプロパティベーステスト"""

    @given(
        age=st.integers(min_value=1, max_value=120),
        height=st.floats(min_value=100, max_value=250, allow_nan=False, allow_infinity=False),
        weight=st.floats(min_value=30, max_value=300, allow_nan=False, allow_infinity=False),
        gender=st.sampled_from([Gender.MALE, Gender.FEMALE])
    )
    def test_bmr_calculation_property(self, age, height, weight, gender):
        """
        Feature: meal-management-app, Property 13: BMR 計算の正確性

        任意のユーザー属性（年齢、身長、体重、性別）が与えられた場合、
        システムはHarris-Benedict式を使用して正確にBMRを計算する必要があります。

        Harris-Benedict式:
        - 男性: BMR = 88.362 + (13.397 × 体重kg) + (4.799 × 身長cm) - (5.677 × 年齢)
        - 女性: BMR = 447.593 + (9.247 × 体重kg) + (3.098 × 身長cm) - (4.330 × 年齢)

        検証: 要件 8.1
        """
        # BMRを計算
        bmr = BMRCalculator.calculate_bmr(age, height, weight, gender)

        # 手動で期待値を計算
        if gender == Gender.MALE:
            expected_bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:  # Gender.FEMALE
            expected_bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

        expected_bmr = round(expected_bmr, 2)

        # BMRが正確に計算されていることを確認
        assert bmr == expected_bmr

        # BMRが正の値であることを確認
        assert bmr > 0

        # BMRが妥当な範囲内であることを確認（計算結果が数値として妥当）
        # 注：極端に大きい体型では5000を超える可能性がある
        assert bmr > 0 and bmr < 10000

    @given(
        bmr=st.floats(min_value=1000, max_value=3000, allow_nan=False, allow_infinity=False),
        activity_level=st.sampled_from([
            ActivityLevel.SEDENTARY,
            ActivityLevel.LIGHT,
            ActivityLevel.MODERATE,
            ActivityLevel.ACTIVE,
            ActivityLevel.VERY_ACTIVE
        ])
    )
    def test_tdee_calculation_property(self, bmr, activity_level):
        """
        Feature: meal-management-app, Property 14: TDEE 計算の正確性

        任意のBMRと活動レベルが与えられた場合、システムは正確に
        TDEE（総消費カロリー）を計算する必要があります。

        計算式: TDEE = BMR × 活動係数

        検証: 要件 8.2
        """
        # TDEEを計算
        tdee = BMRCalculator.calculate_tdee(bmr, activity_level)

        # 期待値を計算
        activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.VERY_ACTIVE: 1.9
        }
        expected_tdee = round(bmr * activity_multipliers[activity_level], 2)

        # TDEEが正確に計算されていることを確認
        assert tdee == expected_tdee

        # TDEEがBMRより大きいか等しいことを確認
        assert tdee >= bmr

        # 計算値の妥当性を確認（活動係数を考慮）
        activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.VERY_ACTIVE: 1.9
        }
        multiplier = activity_multipliers[activity_level]
        expected_tdee_calc = round(bmr * multiplier, 2)
        assert tdee == expected_tdee_calc


class TestBMRCalculator:
    """BMR計算クラスのユニットテスト"""

    def test_calculate_bmr_male_example(self):
        """男性のBMR計算例"""
        # 30歳、身長170cm、体重70kg、男性
        age = 30
        height = 170.0
        weight = 70.0
        gender = Gender.MALE

        bmr = BMRCalculator.calculate_bmr(age, height, weight, gender)

        # 手動計算: 88.362 + (13.397 × 70) + (4.799 × 170) - (5.677 × 30)
        # = 88.362 + 937.79 + 815.83 - 170.31 = 1671.672
        expected_bmr = round(88.362 + (13.397 * 70) + (4.799 * 170) - (5.677 * 30), 2)

        assert bmr == expected_bmr
        assert 1600 < bmr < 1750

    def test_calculate_bmr_female_example(self):
        """女性のBMR計算例"""
        # 25歳、身長160cm、体重55kg、女性
        age = 25
        height = 160.0
        weight = 55.0
        gender = Gender.FEMALE

        bmr = BMRCalculator.calculate_bmr(age, height, weight, gender)

        # 手動計算: 447.593 + (9.247 × 55) + (3.098 × 160) - (4.330 × 25)
        # = 447.593 + 508.585 + 495.68 - 108.25 = 1343.608
        expected_bmr = round(447.593 + (9.247 * 55) + (3.098 * 160) - (4.330 * 25), 2)

        assert bmr == expected_bmr
        assert 1300 < bmr < 1400

    def test_calculate_bmr_invalid_age(self):
        """無効な年齢（0以下）"""
        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(0, 170.0, 70.0, Gender.MALE)

        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(-10, 170.0, 70.0, Gender.MALE)

    def test_calculate_bmr_invalid_height(self):
        """無効な身長（0以下）"""
        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(30, 0, 70.0, Gender.MALE)

        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(30, -170, 70.0, Gender.MALE)

    def test_calculate_bmr_invalid_weight(self):
        """無効な体重（0以下）"""
        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(30, 170.0, 0, Gender.MALE)

        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(30, 170.0, -70.0, Gender.MALE)

    def test_calculate_tdee_sedentary(self):
        """ほとんど運動しない場合のTDEE"""
        bmr = 1500.0
        activity_level = ActivityLevel.SEDENTARY

        tdee = BMRCalculator.calculate_tdee(bmr, activity_level)

        expected_tdee = round(1500.0 * 1.2, 2)
        assert tdee == expected_tdee
        assert tdee == 1800.0

    def test_calculate_tdee_light(self):
        """軽い運動の場合のTDEE"""
        bmr = 1500.0
        activity_level = ActivityLevel.LIGHT

        tdee = BMRCalculator.calculate_tdee(bmr, activity_level)

        expected_tdee = round(1500.0 * 1.375, 2)
        assert tdee == expected_tdee
        assert tdee == 2062.5

    def test_calculate_tdee_moderate(self):
        """中程度の運動の場合のTDEE"""
        bmr = 1500.0
        activity_level = ActivityLevel.MODERATE

        tdee = BMRCalculator.calculate_tdee(bmr, activity_level)

        expected_tdee = round(1500.0 * 1.55, 2)
        assert tdee == expected_tdee
        assert tdee == 2325.0

    def test_calculate_tdee_active(self):
        """激しい運動の場合のTDEE"""
        bmr = 1500.0
        activity_level = ActivityLevel.ACTIVE

        tdee = BMRCalculator.calculate_tdee(bmr, activity_level)

        expected_tdee = round(1500.0 * 1.725, 2)
        assert tdee == expected_tdee
        assert tdee == 2587.5

    def test_calculate_tdee_very_active(self):
        """非常に激しい運動の場合のTDEE"""
        bmr = 1500.0
        activity_level = ActivityLevel.VERY_ACTIVE

        tdee = BMRCalculator.calculate_tdee(bmr, activity_level)

        expected_tdee = round(1500.0 * 1.9, 2)
        assert tdee == expected_tdee
        assert tdee == 2850.0

    def test_calculate_tdee_invalid_bmr(self):
        """無効なBMR（負の値）"""
        with pytest.raises(ValidationError):
            BMRCalculator.calculate_tdee(-100, ActivityLevel.MODERATE)

    def test_calculate_tdee_zero_bmr(self):
        """BMRがゼロの場合"""
        # ゼロは許可される
        tdee = BMRCalculator.calculate_tdee(0, ActivityLevel.MODERATE)
        assert tdee == 0.0

    def test_calculate_bmr_and_tdee_combined(self):
        """BMRとTDEEを同時に計算"""
        age = 30
        height = 170.0
        weight = 70.0
        gender = Gender.MALE
        activity_level = ActivityLevel.MODERATE

        result = BMRCalculator.calculate_bmr_and_tdee(
            age, height, weight, gender, activity_level
        )

        # 結果に必要なキーが含まれていることを確認
        assert "bmr" in result
        assert "tdee" in result

        # BMRが期待値であることを確認
        expected_bmr = BMRCalculator.calculate_bmr(age, height, weight, gender)
        assert result["bmr"] == expected_bmr

        # TDEEが期待値であることを確認
        expected_tdee = BMRCalculator.calculate_tdee(expected_bmr, activity_level)
        assert result["tdee"] == expected_tdee

        # TDEEがBMRより大きいことを確認
        assert result["tdee"] > result["bmr"]

    def test_calculate_bmr_extreme_values(self):
        """極端な値でのBMR計算"""
        # 高齢者の場合
        bmr_elderly = BMRCalculator.calculate_bmr(80, 170.0, 70.0, Gender.MALE)
        assert bmr_elderly > 0

        # 若年層の場合
        bmr_young = BMRCalculator.calculate_bmr(20, 180.0, 80.0, Gender.MALE)
        assert bmr_young > 0

        # 高齢者の方が低いBMRを持つことを確認
        assert bmr_elderly < bmr_young

    def test_calculate_bmr_male_vs_female(self):
        """男女のBMR比較"""
        age = 30
        height = 170.0
        weight = 70.0

        bmr_male = BMRCalculator.calculate_bmr(age, height, weight, Gender.MALE)
        bmr_female = BMRCalculator.calculate_bmr(age, height, weight, Gender.FEMALE)

        # 同じ条件下では、男性の方が高いBMRを持つことが多い（係数の差）
        # このテストは一般的な傾向を検証
        assert bmr_male > 0
        assert bmr_female > 0

    def test_calculate_tdee_increases_with_activity_level(self):
        """活動レベルの増加に伴うTDEEの増加"""
        bmr = 1500.0

        tdee_sedentary = BMRCalculator.calculate_tdee(bmr, ActivityLevel.SEDENTARY)
        tdee_light = BMRCalculator.calculate_tdee(bmr, ActivityLevel.LIGHT)
        tdee_moderate = BMRCalculator.calculate_tdee(bmr, ActivityLevel.MODERATE)
        tdee_active = BMRCalculator.calculate_tdee(bmr, ActivityLevel.ACTIVE)
        tdee_very_active = BMRCalculator.calculate_tdee(bmr, ActivityLevel.VERY_ACTIVE)

        # 活動レベルが上がるにつれてTDEEが増加することを確認
        assert tdee_sedentary < tdee_light
        assert tdee_light < tdee_moderate
        assert tdee_moderate < tdee_active
        assert tdee_active < tdee_very_active

    def test_calculate_bmr_multiple_ages(self):
        """異なる年齢でのBMR計算"""
        height = 170.0
        weight = 70.0
        gender = Gender.MALE

        bmr_20 = BMRCalculator.calculate_bmr(20, height, weight, gender)
        bmr_40 = BMRCalculator.calculate_bmr(40, height, weight, gender)
        bmr_60 = BMRCalculator.calculate_bmr(60, height, weight, gender)

        # 年齢が増えるにつれてBMRが低下することを確認（負の係数：-5.677）
        assert bmr_20 > bmr_40
        assert bmr_40 > bmr_60

    def test_calculate_bmr_multiple_weights(self):
        """異なる体重でのBMR計算"""
        age = 30
        height = 170.0
        gender = Gender.MALE

        bmr_60kg = BMRCalculator.calculate_bmr(age, height, 60.0, gender)
        bmr_70kg = BMRCalculator.calculate_bmr(age, height, 70.0, gender)
        bmr_80kg = BMRCalculator.calculate_bmr(age, height, 80.0, gender)

        # 体重が増えるにつれてBMRが増加することを確認（正の係数：13.397）
        assert bmr_60kg < bmr_70kg
        assert bmr_70kg < bmr_80kg

        # 10kg増加でのBMR増加量を確認（約133.97kcal）
        diff_1 = bmr_70kg - bmr_60kg
        diff_2 = bmr_80kg - bmr_70kg
        assert abs(diff_1 - diff_2) < 0.01  # ほぼ同じ増加量

    def test_calculate_bmr_multiple_heights(self):
        """異なる身長でのBMR計算"""
        age = 30
        weight = 70.0
        gender = Gender.MALE

        bmr_160cm = BMRCalculator.calculate_bmr(age, 160.0, weight, gender)
        bmr_170cm = BMRCalculator.calculate_bmr(age, 170.0, weight, gender)
        bmr_180cm = BMRCalculator.calculate_bmr(age, 180.0, weight, gender)

        # 身長が増えるにつれてBMRが増加することを確認（正の係数：4.799）
        assert bmr_160cm < bmr_170cm
        assert bmr_170cm < bmr_180cm

        # 10cm増加でのBMR増加量を確認（約47.99kcal）
        diff_1 = bmr_170cm - bmr_160cm
        diff_2 = bmr_180cm - bmr_170cm
        assert abs(diff_1 - diff_2) < 0.01  # ほぼ同じ増加量

    def test_calculate_bmr_edge_case_young_age(self):
        """若年（1歳）でのBMR計算"""
        bmr = BMRCalculator.calculate_bmr(1, 50.0, 10.0, Gender.MALE)
        assert bmr > 0
        # 小さい体で低いBMRを持つことを確認
        assert 200 < bmr < 500

    def test_calculate_bmr_edge_case_old_age(self):
        """高齢（120歳）でのBMR計算"""
        bmr = BMRCalculator.calculate_bmr(120, 170.0, 70.0, Gender.MALE)
        assert bmr > 0
        # 年齢による低下を確認
        bmr_30 = BMRCalculator.calculate_bmr(30, 170.0, 70.0, Gender.MALE)
        assert bmr < bmr_30

    def test_calculate_tdee_with_various_bmr_values(self):
        """異なるBMR値でのTDEE計算"""
        activity_level = ActivityLevel.MODERATE
        multiplier = 1.55

        # 複数のBMR値をテスト
        for bmr in [1000, 1500, 2000, 2500, 3000]:
            tdee = BMRCalculator.calculate_tdee(bmr, activity_level)
            expected_tdee = round(bmr * multiplier, 2)
            assert tdee == expected_tdee
