"""
ユーザープロフィール管理ロジックのテスト

Property 15プロパティテスト、およびユニットテスト
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st, assume

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    ProfileManager,
    User,
    Gender,
    ActivityLevel,
    ValidationError,
)


class TestProfileManagerPropertyBased:
    """ユーザープロフィール管理のプロパティベーステスト"""

    @given(
        age=st.integers(min_value=10, max_value=100),
        height=st.floats(min_value=100, max_value=220, allow_nan=False, allow_infinity=False),
        weight=st.floats(min_value=30, max_value=200, allow_nan=False, allow_infinity=False),
        gender=st.sampled_from([Gender.MALE, Gender.FEMALE]),
        activity_level=st.sampled_from([
            ActivityLevel.SEDENTARY,
            ActivityLevel.LIGHT,
            ActivityLevel.MODERATE,
            ActivityLevel.ACTIVE,
            ActivityLevel.VERY_ACTIVE
        ])
    )
    def test_profile_update_recalculation_property(
        self,
        age,
        height,
        weight,
        gender,
        activity_level
    ):
        """
        Feature: meal-management-app, Property 15: プロフィール更新時の再計算

        任意のユーザープロフィール更新に対して、システムは自動的にBMRとTDEEを
        再計算する必要があります。

        検証: 要件 8.3
        """
        # 初期プロフィールを作成
        initial_user = ProfileManager.create_profile(
            user_id="test_user",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        # 初期のBMRとTDEEを記録
        initial_bmr = initial_user.bmr
        initial_tdee = initial_user.tdee

        # プロフィールを更新
        updated_user = ProfileManager.update_profile(
            initial_user,
            age=age,
            height=height,
            weight=weight,
            gender=gender,
            activity_level=activity_level
        )

        # 更新されたプロフィールの値が正しいことを確認
        assert updated_user.age == age
        assert updated_user.height == height
        assert updated_user.weight == weight
        assert updated_user.gender == gender
        assert updated_user.activity_level == activity_level

        # BMRとTDEEが再計算されていることを確認
        assert updated_user.bmr is not None
        assert updated_user.tdee is not None
        assert updated_user.bmr > 0
        assert updated_user.tdee > 0

        # BMRとTDEEがBMRCalculatorによる計算結果と一致することを確認
        from common.bmr_calculator import BMRCalculator
        expected_bmr = BMRCalculator.calculate_bmr(age, height, weight, gender)
        expected_tdee = BMRCalculator.calculate_tdee(expected_bmr, activity_level)

        assert updated_user.bmr == expected_bmr
        assert updated_user.tdee == expected_tdee

        # 更新日時が更新されていることを確認
        assert updated_user.updated_at != initial_user.created_at

        # 初期値と異なる値に更新された場合、BMR/TDEEも変わる可能性がある
        # （同じ値に更新した場合は同じBMR/TDEEになる可能性がある）
        if (age != 30 or height != 170.0 or weight != 70.0 or
            gender != Gender.MALE or activity_level != ActivityLevel.MODERATE):
            # 少なくとも1つのパラメータが変わった場合、BMRまたはTDEEが変わる可能性が高い
            # ただし、偶然同じ値になることもあるので、厳密には検証しない
            pass


class TestProfileManager:
    """ユーザープロフィール管理クラスのユニットテスト"""

    def test_create_profile_basic(self):
        """基本的なプロフィール作成"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        assert user.user_id == "user123"
        assert user.age == 30
        assert user.height == 170.0
        assert user.weight == 70.0
        assert user.gender == Gender.MALE
        assert user.activity_level == ActivityLevel.MODERATE
        assert user.bmr > 0
        assert user.tdee > 0
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_create_profile_with_line_user_id(self):
        """LINE User IDを含むプロフィール作成"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=25,
            height=165.0,
            weight=60.0,
            gender=Gender.FEMALE,
            activity_level=ActivityLevel.LIGHT,
            line_user_id="LINE123"
        )

        assert user.user_id == "user123"
        assert user.line_user_id == "LINE123"
        assert user.cognito_user_id is None

    def test_create_profile_with_cognito_user_id(self):
        """Cognito User IDを含むプロフィール作成"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=35,
            height=175.0,
            weight=75.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.ACTIVE,
            cognito_user_id="COGNITO123"
        )

        assert user.user_id == "user123"
        assert user.cognito_user_id == "COGNITO123"
        assert user.line_user_id is None

    def test_create_profile_invalid_age(self):
        """無効な年齢でのバリデーション"""
        with pytest.raises(ValidationError):
            ProfileManager.create_profile(
                user_id="user123",
                age=-5,
                height=170.0,
                weight=70.0,
                gender=Gender.MALE,
                activity_level=ActivityLevel.MODERATE
            )

    def test_create_profile_invalid_height(self):
        """無効な身長でのバリデーション"""
        with pytest.raises(ValidationError):
            ProfileManager.create_profile(
                user_id="user123",
                age=30,
                height=-170.0,
                weight=70.0,
                gender=Gender.MALE,
                activity_level=ActivityLevel.MODERATE
            )

    def test_create_profile_invalid_weight(self):
        """無効な体重でのバリデーション"""
        with pytest.raises(ValidationError):
            ProfileManager.create_profile(
                user_id="user123",
                age=30,
                height=170.0,
                weight=0,
                gender=Gender.MALE,
                activity_level=ActivityLevel.MODERATE
            )

    def test_create_profile_empty_user_id(self):
        """空のユーザーIDでのバリデーション"""
        with pytest.raises(ValidationError):
            ProfileManager.create_profile(
                user_id="",
                age=30,
                height=170.0,
                weight=70.0,
                gender=Gender.MALE,
                activity_level=ActivityLevel.MODERATE
            )

    def test_update_profile_age(self):
        """年齢のみ更新"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        initial_bmr = user.bmr
        initial_tdee = user.tdee

        updated_user = ProfileManager.update_profile(user, age=35)

        assert updated_user.age == 35
        assert updated_user.height == 170.0
        assert updated_user.weight == 70.0
        # 年齢が変わったので、BMRが変わるはず
        assert updated_user.bmr != initial_bmr
        assert updated_user.tdee != initial_tdee

    def test_update_profile_weight(self):
        """体重のみ更新"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        initial_bmr = user.bmr

        updated_user = ProfileManager.update_profile(user, weight=75.0)

        assert updated_user.weight == 75.0
        # 体重が変わったので、BMRが変わるはず
        assert updated_user.bmr != initial_bmr

    def test_update_profile_activity_level(self):
        """活動レベルのみ更新"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        initial_bmr = user.bmr
        initial_tdee = user.tdee

        updated_user = ProfileManager.update_profile(
            user,
            activity_level=ActivityLevel.ACTIVE
        )

        assert updated_user.activity_level == ActivityLevel.ACTIVE
        # 活動レベルが変わったので、TDEEが変わるはず（BMRは同じ）
        assert updated_user.bmr == initial_bmr
        assert updated_user.tdee != initial_tdee

    def test_update_profile_multiple_fields(self):
        """複数フィールドを同時に更新"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        updated_user = ProfileManager.update_profile(
            user,
            age=35,
            weight=75.0,
            activity_level=ActivityLevel.ACTIVE
        )

        assert updated_user.age == 35
        assert updated_user.weight == 75.0
        assert updated_user.activity_level == ActivityLevel.ACTIVE

    def test_update_profile_no_changes(self):
        """何も変更しない更新"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        initial_bmr = user.bmr
        initial_tdee = user.tdee

        updated_user = ProfileManager.update_profile(user)

        # 値は変わらない
        assert updated_user.age == 30
        assert updated_user.height == 170.0
        assert updated_user.weight == 70.0
        # BMR/TDEEも同じ
        assert updated_user.bmr == initial_bmr
        assert updated_user.tdee == initial_tdee

    def test_update_profile_invalid_age(self):
        """無効な年齢での更新バリデーション"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        with pytest.raises(ValidationError):
            ProfileManager.update_profile(user, age=-5)

    def test_update_profile_invalid_height(self):
        """無効な身長での更新バリデーション"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        with pytest.raises(ValidationError):
            ProfileManager.update_profile(user, height=0)

    def test_update_profile_invalid_weight(self):
        """無効な体重での更新バリデーション"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        with pytest.raises(ValidationError):
            ProfileManager.update_profile(user, weight=-10)

    def test_get_profile_summary(self):
        """プロフィールサマリーの取得"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE,
            line_user_id="LINE123"
        )

        summary = ProfileManager.get_profile_summary(user)

        assert summary["user_id"] == "user123"
        assert summary["age"] == 30
        assert summary["height"] == 170.0
        assert summary["weight"] == 70.0
        assert summary["gender"] == "male"
        assert summary["activity_level"] == "moderate"
        assert summary["bmr"] > 0
        assert summary["tdee"] > 0
        assert summary["created_at"] is not None
        assert summary["updated_at"] is not None

    def test_bmr_tdee_recalculation_on_update(self):
        """プロフィール更新時にBMR/TDEEが正しく再計算されることを確認"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        # 体重を75kgに更新
        updated_user = ProfileManager.update_profile(user, weight=75.0)

        # BMRCalculatorで期待値を計算
        from common.bmr_calculator import BMRCalculator
        expected_bmr = BMRCalculator.calculate_bmr(30, 170.0, 75.0, Gender.MALE)
        expected_tdee = BMRCalculator.calculate_tdee(expected_bmr, ActivityLevel.MODERATE)

        # 再計算されたBMR/TDEEが期待値と一致することを確認
        assert updated_user.bmr == expected_bmr
        assert updated_user.tdee == expected_tdee

    def test_update_profile_gender_change(self):
        """性別変更時のBMR/TDEE再計算"""
        user = ProfileManager.create_profile(
            user_id="user123",
            age=30,
            height=170.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )

        initial_bmr = user.bmr

        # 性別を変更
        updated_user = ProfileManager.update_profile(user, gender=Gender.FEMALE)

        assert updated_user.gender == Gender.FEMALE
        # 性別が変わったので、BMRが変わるはず（男性と女性で計算式が異なる）
        assert updated_user.bmr != initial_bmr
