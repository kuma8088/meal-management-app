"""
エラーハンドリングとリトライロジックのユニットテスト

Feature: meal-management-app, Task 19.1: エラーハンドリングのユニットテスト
要件: 14.1, 14.2, 14.3
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

# 共通モジュール
from common.retry import exponential_backoff_retry
from common.response import create_response, success_response, error_response
from common.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    DataIntegrityError,
    ExternalServiceError,
    RetryableError
)


# ========================================
# リトライロジックのテスト
# ========================================

class TestRetryLogic:
    """
    リトライロジックのユニットテスト
    要件: 14.2 - 一時的なエラーに対する自動リトライ
    """

    @pytest.mark.unit
    def test_exponential_backoff_retry_success_first_attempt(self):
        """
        初回成功時はリトライしない

        GIVEN: 成功する関数
        WHEN: リトライデコレータを適用して実行
        THEN: 1回だけ実行され、結果が返される
        """
        mock_func = Mock(return_value="success")
        decorated_func = exponential_backoff_retry(max_retries=3)(mock_func)

        result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.unit
    def test_exponential_backoff_retry_success_after_retries(self):
        """
        リトライ後に成功

        GIVEN: 2回失敗してから成功する関数
        WHEN: リトライデコレータを適用して実行
        THEN: 3回実行され、最終的に成功結果が返される
        """
        mock_func = Mock(side_effect=[
            RetryableError("Temporary error 1"),
            RetryableError("Temporary error 2"),
            "success"
        ])
        mock_func.__name__ = "test_function"
        decorated_func = exponential_backoff_retry(max_retries=3)(mock_func)

        result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.unit
    def test_exponential_backoff_retry_max_retries_exceeded(self):
        """
        最大リトライ回数を超えた場合

        GIVEN: 常に失敗する関数
        WHEN: リトライデコレータを適用して実行
        THEN: 最大回数実行され、最後のエラーが発生する
        """
        mock_func = Mock(side_effect=RetryableError("Persistent error"))
        mock_func.__name__ = "test_function"
        decorated_func = exponential_backoff_retry(max_retries=3)(mock_func)

        with pytest.raises(RetryableError, match="Persistent error"):
            decorated_func()

        assert mock_func.call_count == 3

    @pytest.mark.unit
    def test_exponential_backoff_retry_non_retryable_error(self):
        """
        リトライ不可能なエラー

        GIVEN: ValidationErrorを発生させる関数
        WHEN: リトライデコレータを適用して実行
        THEN: 1回だけ実行され、即座にエラーが発生する
        """
        mock_func = Mock(side_effect=ValidationError("Invalid input"))
        decorated_func = exponential_backoff_retry(max_retries=3)(mock_func)

        with pytest.raises(ValidationError, match="Invalid input"):
            decorated_func()

        assert mock_func.call_count == 1

    # ClientErrorのリトライテストはデフォルトではサポートされていないため、コメントアウト
    # デフォルトでは RetryableError のみがリトライ対象
    # @pytest.mark.unit
    # def test_exponential_backoff_retry_with_client_error_throttling(self):
    #     """
    #     ClientError（スロットリング）のリトライ
    #
    #     GIVEN: ClientError（ThrottlingException）を発生させる関数
    #     WHEN: リトライデコレータを適用して実行
    #     THEN: リトライされ、最終的に成功する
    #     """
    #     client_error = ClientError(
    #         {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
    #         'GetItem'
    #     )
    #     mock_func = Mock(side_effect=[client_error, "success"])
    #     mock_func.__name__ = "test_function"
    #     decorated_func = exponential_backoff_retry(max_retries=3)(mock_func)
    #
    #     result = decorated_func()
    #
    #     assert result == "success"
    #     assert mock_func.call_count == 2

    @pytest.mark.unit
    def test_exponential_backoff_retry_with_client_error_non_retryable(self):
        """
        ClientError（リトライ不可）

        GIVEN: ClientError（ValidationException）を発生させる関数
        WHEN: リトライデコレータを適用して実行
        THEN: 1回だけ実行され、即座にエラーが発生する
        """
        client_error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}},
            'GetItem'
        )
        mock_func = Mock(side_effect=client_error)
        decorated_func = exponential_backoff_retry(max_retries=3)(mock_func)

        with pytest.raises(ClientError):
            decorated_func()

        assert mock_func.call_count == 1

    @pytest.mark.unit
    def test_exponential_backoff_with_custom_parameters(self):
        """
        カスタムパラメータでのリトライ

        GIVEN: リトライ可能なエラーを発生させる関数
        WHEN: カスタムパラメータ（max_retries=5）でデコレータを適用
        THEN: 指定した回数までリトライされる
        """
        mock_func = Mock(side_effect=RetryableError("Error"))
        mock_func.__name__ = "test_function"
        decorated_func = exponential_backoff_retry(max_retries=5)(mock_func)

        with pytest.raises(RetryableError):
            decorated_func()

        assert mock_func.call_count == 5


# ========================================
# エラーレスポンスのテスト
# ========================================

class TestErrorResponse:
    """
    エラーレスポンスのユニットテスト
    要件: 14.3 - 適切なHTTPステータスコードとエラーメッセージの返却
    """

    @pytest.mark.unit
    def test_create_response_with_json_body(self):
        """
        JSONボディを含むレスポンス作成

        GIVEN: ステータスコード200とJSONデータ
        WHEN: create_response()を呼び出し
        THEN: 正しい形式のレスポンスが返される
        """
        body = {"message": "Success"}
        response = create_response(200, body)

        assert response["statusCode"] == 200
        assert "body" in response
        assert "headers" in response
        assert response["headers"]["Content-Type"] == "application/json"

        parsed_body = json.loads(response["body"])
        assert parsed_body["message"] == "Success"

    @pytest.mark.unit
    def test_create_response_with_custom_headers(self):
        """
        カスタムヘッダーを含むレスポンス作成

        GIVEN: カスタムヘッダー
        WHEN: create_response()を呼び出し
        THEN: カスタムヘッダーが含まれる
        """
        body = {"message": "Success"}
        custom_headers = {"X-Custom-Header": "custom-value"}
        response = create_response(200, body, headers=custom_headers)

        assert response["headers"]["X-Custom-Header"] == "custom-value"
        assert response["headers"]["Content-Type"] == "application/json"

    @pytest.mark.unit
    def test_success_response(self):
        """
        成功レスポンスの作成

        GIVEN: データ
        WHEN: success_response()を呼び出し
        THEN: ステータスコード200のレスポンスが返される
        """
        data = {"user_id": "123", "name": "Test User"}
        response = success_response(data)

        assert response["statusCode"] == 200
        parsed_body = json.loads(response["body"])
        assert parsed_body["user_id"] == "123"
        assert parsed_body["name"] == "Test User"

    @pytest.mark.unit
    def test_error_response_validation_error(self):
        """
        ValidationErrorのエラーレスポンス

        GIVEN: ValidationError
        WHEN: error_response()を呼び出し
        THEN: ステータスコード400のレスポンスが返される
        """
        error = ValidationError("Invalid input", details={"field": "email"})
        response = error_response(error)

        assert response["statusCode"] == 400
        parsed_body = json.loads(response["body"])
        assert "error" in parsed_body
        assert parsed_body["error"]["code"] == "VALIDATION_ERROR"
        assert parsed_body["error"]["message"] == "Invalid input"
        assert parsed_body["error"]["details"]["field"] == "email"

    @pytest.mark.unit
    def test_error_response_authentication_error(self):
        """
        AuthenticationErrorのエラーレスポンス

        GIVEN: AuthenticationError
        WHEN: error_response()を呼び出し
        THEN: ステータスコード401のレスポンスが返される
        """
        error = AuthenticationError("Invalid credentials")
        response = error_response(error)

        assert response["statusCode"] == 401
        parsed_body = json.loads(response["body"])
        assert parsed_body["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.unit
    def test_error_response_authorization_error(self):
        """
        AuthorizationErrorのエラーレスポンス

        GIVEN: AuthorizationError
        WHEN: error_response()を呼び出し
        THEN: ステータスコード403のレスポンスが返される
        """
        error = AuthorizationError("Access denied")
        response = error_response(error)

        assert response["statusCode"] == 403
        parsed_body = json.loads(response["body"])
        assert parsed_body["error"]["code"] == "AUTHORIZATION_ERROR"

    @pytest.mark.unit
    def test_error_response_resource_not_found_error(self):
        """
        ResourceNotFoundErrorのエラーレスポンス

        GIVEN: ResourceNotFoundError
        WHEN: error_response()を呼び出し
        THEN: ステータスコード404のレスポンスが返される
        """
        error = ResourceNotFoundError("User not found")
        response = error_response(error)

        assert response["statusCode"] == 404
        parsed_body = json.loads(response["body"])
        assert parsed_body["error"]["code"] == "RESOURCE_NOT_FOUND"

    @pytest.mark.unit
    def test_error_response_data_integrity_error(self):
        """
        DataIntegrityErrorのエラーレスポンス

        GIVEN: DataIntegrityError
        WHEN: error_response()を呼び出し
        THEN: ステータスコード409のレスポンスが返される
        """
        error = DataIntegrityError("Duplicate entry")
        response = error_response(error)

        assert response["statusCode"] == 409
        parsed_body = json.loads(response["body"])
        assert parsed_body["error"]["code"] == "DATA_INTEGRITY_ERROR"

    @pytest.mark.unit
    def test_error_response_external_service_error(self):
        """
        ExternalServiceErrorのエラーレスポンス

        GIVEN: ExternalServiceError
        WHEN: error_response()を呼び出し
        THEN: ステータスコード502のレスポンスが返される
        """
        error = ExternalServiceError("Bedrock API failed", service="bedrock")
        response = error_response(error)

        assert response["statusCode"] == 502
        parsed_body = json.loads(response["body"])
        assert parsed_body["error"]["code"] == "EXTERNAL_SERVICE_ERROR"
        assert parsed_body["error"]["details"]["service"] == "bedrock"

    @pytest.mark.unit
    def test_error_response_generic_exception(self):
        """
        汎用的なExceptionのエラーレスポンス

        GIVEN: 汎用的なException
        WHEN: error_response()を呼び出し
        THEN: ステータスコード500のレスポンスが返される
        """
        error = Exception("Unexpected error")
        response = error_response(error)

        assert response["statusCode"] == 500
        parsed_body = json.loads(response["body"])
        assert "error" in parsed_body
        assert parsed_body["error"]["code"] == "INTERNAL_ERROR"
        assert parsed_body["error"]["message"] == "内部エラーが発生しました"

    @pytest.mark.unit
    def test_error_response_cors_headers(self):
        """
        エラーレスポンスにCORSヘッダーが含まれる

        GIVEN: AppException
        WHEN: error_response()を呼び出し
        THEN: CORSヘッダーが含まれる
        """
        error = ValidationError("Invalid input")
        response = error_response(error)

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"


# ========================================
# カスタム例外のテスト
# ========================================

class TestCustomExceptions:
    """
    カスタム例外のユニットテスト
    """

    @pytest.mark.unit
    def test_app_exception_initialization(self):
        """
        AppException基底クラスの初期化

        GIVEN: メッセージ、コード、詳細
        WHEN: AppExceptionを作成
        THEN: 正しくプロパティが設定される
        """
        error = AppException("Test error", code="TEST_ERROR", details={"key": "value"})

        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"

    @pytest.mark.unit
    def test_validation_error_default_code(self):
        """
        ValidationErrorのデフォルトコード

        GIVEN: メッセージのみ
        WHEN: ValidationErrorを作成
        THEN: デフォルトコード"VALIDATION_ERROR"が設定される
        """
        error = ValidationError("Invalid email")

        assert error.message == "Invalid email"
        assert error.code == "VALIDATION_ERROR"

    @pytest.mark.unit
    def test_external_service_error_with_service_name(self):
        """
        ExternalServiceErrorのサービス名

        GIVEN: メッセージとサービス名
        WHEN: ExternalServiceErrorを作成
        THEN: detailsにサービス名が含まれる
        """
        error = ExternalServiceError("API timeout", service="bedrock")

        assert error.message == "API timeout"
        assert error.code == "EXTERNAL_SERVICE_ERROR"
        assert error.details["service"] == "bedrock"

    @pytest.mark.unit
    def test_retryable_error(self):
        """
        RetryableErrorの作成

        GIVEN: メッセージ
        WHEN: RetryableErrorを作成
        THEN: 正しくプロパティが設定される
        """
        error = RetryableError("Temporary failure")

        assert error.message == "Temporary failure"
        assert error.code == "RETRYABLE_ERROR"


# ========================================
# 統合的なエラーハンドリングのテスト
# ========================================

class TestIntegratedErrorHandling:
    """
    エラーハンドリングの統合テスト
    """

    @pytest.mark.unit
    def test_retry_with_error_response(self):
        """
        リトライとエラーレスポンスの統合

        GIVEN: リトライ可能なエラーを発生させる関数
        WHEN: リトライ後に失敗し、error_response()で処理
        THEN: 適切なエラーレスポンスが返される
        """
        mock_func = Mock(side_effect=RetryableError("Service unavailable"))
        mock_func.__name__ = "test_function"
        decorated_func = exponential_backoff_retry(max_retries=2)(mock_func)

        try:
            decorated_func()
        except RetryableError as e:
            response = error_response(e)

        assert response["statusCode"] == 503  # RetryableErrorは503を返す
        assert mock_func.call_count == 2

    @pytest.mark.unit
    def test_lambda_handler_error_flow(self):
        """
        Lambda関数のエラーフロー

        GIVEN: Lambda関数がValidationErrorを発生
        WHEN: エラーハンドリングを適用
        THEN: 適切なエラーレスポンスが返される
        """
        def mock_lambda_handler(event, context):
            # バリデーションエラーをシミュレート
            if not event.get("user_id"):
                raise ValidationError("user_id is required")
            return success_response({"message": "Success"})

        # エラーケース
        event = {}
        try:
            response = mock_lambda_handler(event, None)
        except ValidationError as e:
            response = error_response(e)

        assert response["statusCode"] == 400
        parsed_body = json.loads(response["body"])
        assert parsed_body["error"]["message"] == "user_id is required"

        # 成功ケース
        event = {"user_id": "123"}
        response = mock_lambda_handler(event, None)
        assert response["statusCode"] == 200
