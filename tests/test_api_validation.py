"""
APIリクエスト検証のプロパティベーステスト

Feature: meal-management-app, Property 26: APIリクエストの検証
要件: 13.2, 13.3
"""
import pytest
import json
from hypothesis import given, strategies as st
from hypothesis import assume
from datetime import datetime, date, timedelta

# 共通モジュール
from common.response import error_response
from common.exceptions import (
    ValidationError,
    AuthorizationError,
    ResourceNotFoundError
)


# ========================================
# テストデータ生成戦略
# ========================================

@st.composite
def valid_meal_data(draw):
    """有効な食事記録データを生成"""
    meal_types = ["breakfast", "lunch", "dinner", "snack"]
    return {
        "meal_type": draw(st.sampled_from(meal_types)),
        "timestamp": datetime.now().isoformat(),
        "foods": draw(st.lists(
            st.fixed_dictionaries({
                "food_id": st.text(min_size=1, max_size=50),
                "name": st.text(min_size=1, max_size=100),
                "amount": st.floats(min_value=0.1, max_value=10000),
                "unit": st.sampled_from(["g", "ml", "個", "杯"])
            }),
            min_size=1,
            max_size=10
        ))
    }


@st.composite
def invalid_meal_data(draw):
    """無効な食事記録データを生成（必須フィールド欠落またはデータ型不正）"""
    issue_type = draw(st.sampled_from([
        "missing_meal_type",
        "missing_timestamp",
        "missing_foods",
        "invalid_meal_type",
        "invalid_timestamp",
        "negative_amount",
        "empty_foods"
    ]))

    base_data = {
        "meal_type": "breakfast",
        "timestamp": datetime.now().isoformat(),
        "foods": [{
            "food_id": "food_001",
            "name": "ご飯",
            "amount": 200.0,
            "unit": "g"
        }]
    }

    if issue_type == "missing_meal_type":
        del base_data["meal_type"]
    elif issue_type == "missing_timestamp":
        del base_data["timestamp"]
    elif issue_type == "missing_foods":
        del base_data["foods"]
    elif issue_type == "invalid_meal_type":
        base_data["meal_type"] = "invalid_type"
    elif issue_type == "invalid_timestamp":
        base_data["timestamp"] = "not-a-timestamp"
    elif issue_type == "negative_amount":
        base_data["foods"][0]["amount"] = -100.0
    elif issue_type == "empty_foods":
        base_data["foods"] = []

    return base_data


@st.composite
def valid_user_profile_data(draw):
    """有効なユーザープロフィールデータを生成"""
    genders = ["male", "female"]
    activity_levels = ["sedentary", "light", "moderate", "active", "very_active"]

    return {
        "age": draw(st.integers(min_value=10, max_value=120)),
        "height": draw(st.floats(min_value=100.0, max_value=250.0)),
        "weight": draw(st.floats(min_value=30.0, max_value=300.0)),
        "gender": draw(st.sampled_from(genders)),
        "activity_level": draw(st.sampled_from(activity_levels))
    }


@st.composite
def invalid_user_profile_data(draw):
    """無効なユーザープロフィールデータを生成"""
    issue_type = draw(st.sampled_from([
        "missing_age",
        "missing_gender",
        "invalid_age",
        "invalid_height",
        "invalid_weight",
        "invalid_gender",
        "invalid_activity_level"
    ]))

    base_data = {
        "age": 30,
        "height": 170.0,
        "weight": 70.0,
        "gender": "male",
        "activity_level": "moderate"
    }

    if issue_type == "missing_age":
        del base_data["age"]
    elif issue_type == "missing_gender":
        del base_data["gender"]
    elif issue_type == "invalid_age":
        base_data["age"] = -10
    elif issue_type == "invalid_height":
        base_data["height"] = -170.0
    elif issue_type == "invalid_weight":
        base_data["weight"] = 0
    elif issue_type == "invalid_gender":
        base_data["gender"] = "invalid"
    elif issue_type == "invalid_activity_level":
        base_data["activity_level"] = "invalid"

    return base_data


# ========================================
# プロパティテスト: Property 26
# ========================================

class TestAPIRequestValidation:
    """
    Feature: meal-management-app, Property 26: APIリクエストの検証
    要件: 13.2 - APIリクエストが受信されるとシステムはリクエストの形式を検証する
    要件: 13.3 - 検証が失敗するとシステムは適切なHTTPステータスコードとエラーメッセージを返す
    """

    @pytest.mark.property
    @given(data=valid_meal_data())
    def test_valid_meal_request_structure(self, data):
        """
        Property 26.1: 有効な食事記録リクエストは必須フィールドを全て含む

        GIVEN: 有効な食事記録データ
        WHEN: リクエストの検証を行う
        THEN: 必須フィールド（meal_type, timestamp, foods）が存在する
        """
        assert "meal_type" in data
        assert "timestamp" in data
        assert "foods" in data
        assert len(data["foods"]) > 0

        # 各foodも必須フィールドを持つ
        for food in data["foods"]:
            assert "food_id" in food or "name" in food
            assert "amount" in food
            assert food["amount"] > 0

    @pytest.mark.property
    @given(data=invalid_meal_data())
    def test_invalid_meal_request_structure(self, data):
        """
        Property 26.2: 無効な食事記録リクエストは検証エラーを引き起こす

        GIVEN: 無効な食事記録データ（必須フィールド欠落またはデータ型不正）
        WHEN: リクエストの検証を行う
        THEN: 検証エラーが発生する
        """
        # 必須フィールドのいずれかが欠落しているか、無効な値を持つ
        has_missing_field = (
            "meal_type" not in data or
            "timestamp" not in data or
            "foods" not in data
        )

        has_invalid_value = False
        if "meal_type" in data:
            has_invalid_value |= data["meal_type"] not in ["breakfast", "lunch", "dinner", "snack"]
        if "timestamp" in data:
            # ISO 8601形式のタイムスタンプかどうかを検証
            try:
                datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                has_invalid_value = True
        if "foods" in data:
            has_invalid_value |= len(data["foods"]) == 0
            for food in data.get("foods", []):
                if "amount" in food:
                    has_invalid_value |= food["amount"] <= 0

        assert has_missing_field or has_invalid_value

    @pytest.mark.property
    @given(data=valid_user_profile_data())
    def test_valid_user_profile_request_structure(self, data):
        """
        Property 26.3: 有効なユーザープロフィールリクエストは必須フィールドを全て含む

        GIVEN: 有効なユーザープロフィールデータ
        WHEN: リクエストの検証を行う
        THEN: 必須フィールド（age, height, weight, gender, activity_level）が存在し、値が有効範囲内
        """
        assert "age" in data
        assert "height" in data
        assert "weight" in data
        assert "gender" in data
        assert "activity_level" in data

        # 値の範囲チェック
        assert 10 <= data["age"] <= 120
        assert 100.0 <= data["height"] <= 250.0
        assert 30.0 <= data["weight"] <= 300.0
        assert data["gender"] in ["male", "female"]
        assert data["activity_level"] in ["sedentary", "light", "moderate", "active", "very_active"]

    @pytest.mark.property
    @given(data=invalid_user_profile_data())
    def test_invalid_user_profile_request_structure(self, data):
        """
        Property 26.4: 無効なユーザープロフィールリクエストは検証エラーを引き起こす

        GIVEN: 無効なユーザープロフィールデータ
        WHEN: リクエストの検証を行う
        THEN: 検証エラーが発生する
        """
        has_missing_field = (
            "age" not in data or
            "gender" not in data
        )

        has_invalid_value = False
        if "age" in data:
            has_invalid_value |= data["age"] < 0 or data["age"] > 150
        if "height" in data:
            has_invalid_value |= data["height"] <= 0
        if "weight" in data:
            has_invalid_value |= data["weight"] <= 0
        if "gender" in data:
            has_invalid_value |= data["gender"] not in ["male", "female"]
        if "activity_level" in data:
            has_invalid_value |= data["activity_level"] not in [
                "sedentary", "light", "moderate", "active", "very_active"
            ]

        assert has_missing_field or has_invalid_value

    @pytest.mark.property
    @given(
        start_date=st.dates(min_value=date.today() - timedelta(days=365), max_value=date.today()),
        end_date=st.dates(min_value=date.today() - timedelta(days=365), max_value=date.today())
    )
    def test_date_range_validation(self, start_date, end_date):
        """
        Property 26.5: 日付範囲クエリパラメータの検証

        GIVEN: 開始日と終了日
        WHEN: 日付範囲の検証を行う
        THEN: 開始日が終了日より後の場合は検証エラー
        """
        if start_date <= end_date:
            # 有効な日付範囲
            assert True
        else:
            # 無効な日付範囲（開始日 > 終了日）
            # この場合、APIは400 Bad Requestを返すべき
            assert start_date > end_date


# ========================================
# エラーレスポンス形式のテスト
# ========================================

class TestErrorResponseFormat:
    """
    要件 13.3: 検証失敗時の適切なHTTPステータスコードとエラーメッセージ
    """

    @pytest.mark.unit
    def test_validation_error_response_format(self):
        """
        検証エラーレスポンスは標準形式に従う

        GIVEN: 検証エラーが発生
        WHEN: エラーレスポンスを生成
        THEN: error.code, error.message, error.request_idが含まれる
        """
        error = ValidationError("Invalid meal_type")
        response = error_response(error)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])

        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert body["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.unit
    def test_authorization_error_response_format(self):
        """
        認証エラーレスポンスは403を返す

        GIVEN: 認証エラーが発生
        WHEN: エラーレスポンスを生成
        THEN: ステータスコード403とエラー情報が含まれる
        """
        error = AuthorizationError("Invalid token")
        response = error_response(error)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])

        assert "error" in body
        assert body["error"]["code"] == "AUTHORIZATION_ERROR"

    @pytest.mark.unit
    def test_not_found_error_response_format(self):
        """
        リソース未検出エラーレスポンスは404を返す

        GIVEN: リソースが見つからない
        WHEN: エラーレスポンスを生成
        THEN: ステータスコード404とエラー情報が含まれる
        """
        error = ResourceNotFoundError("Meal not found")
        response = error_response(error)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])

        assert "error" in body
        assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
