"""
Lambda Authorizer 並行稼働テスト

Feature: Cognito ID Federation, Phase 3.3
X-Line-User-Id と Cognito JWT の両方の認証方式が同時に動作することを検証
"""
import pytest
import json
from unittest.mock import MagicMock, patch

# テスト対象
import sys
from pathlib import Path

# src/lambda/authorizerをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "authorizer"))


class TestAuthorizerParallelOperation:
    """並行稼働テスト: Cognito JWT と X-Line-User-Id の両方をサポート"""

    @pytest.fixture
    def mock_cognito_client(self):
        """Cognito クライアントのモック"""
        with patch('authorizer.cognito_client') as mock:
            yield mock

    @pytest.fixture
    def mock_dynamodb(self):
        """DynamoDB のモック"""
        with patch('authorizer.dynamodb') as mock:
            yield mock

    @pytest.fixture
    def base_event(self):
        """基本イベント構造"""
        return {
            "methodArn": "arn:aws:execute-api:ap-northeast-1:123456789:api-id/dev/GET/users",
            "headers": {}
        }

    # ===================================
    # Cognito JWT 認証テスト
    # ===================================

    @pytest.mark.unit
    def test_cognito_jwt_auth_success(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: Cognito JWT トークンで認証成功
        """
        from authorizer import lambda_handler

        # Cognito get_user のモック
        mock_cognito_client.get_user.return_value = {
            "Username": "test-user",
            "UserAttributes": [
                {"Name": "sub", "Value": "cognito-user-id-123"},
                {"Name": "email", "Value": "test@example.com"},
            ]
        }

        # Authorization ヘッダーに JWT トークンを設定
        base_event["headers"] = {
            "Authorization": "Bearer valid_cognito_token"
        }

        response = lambda_handler(base_event, None)

        # 認証成功を確認
        assert response["principalId"] == "cognito-user-id-123"
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Allow"
        assert response["context"]["authType"] == "cognito"
        assert response["context"]["userId"] == "cognito-user-id-123"
        assert response["context"]["email"] == "test@example.com"

        # Cognito API が呼ばれたことを確認
        mock_cognito_client.get_user.assert_called_once_with(AccessToken="valid_cognito_token")

    @pytest.mark.unit
    def test_cognito_jwt_auth_failure(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: 無効な Cognito JWT はエラー
        """
        from authorizer import lambda_handler
        from botocore.exceptions import ClientError

        # Cognito get_user がエラーを返す
        mock_cognito_client.get_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}},
            "GetUser"
        )

        # X-Line-User-Id もない
        base_event["headers"] = {
            "Authorization": "Bearer invalid_token"
        }

        response = lambda_handler(base_event, None)

        # 認証失敗（Deny）を確認
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    # ===================================
    # X-Line-User-Id 認証テスト
    # ===================================

    @pytest.mark.unit
    def test_line_user_id_auth_success(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: X-Line-User-Id で認証成功
        """
        from authorizer import lambda_handler

        # DynamoDB クエリのモック
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "user_id": "internal-user-id-456",
                    "line_user_id": "U1234567890abcdef1234567890abcdef"
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        # X-Line-User-Id ヘッダーを設定
        base_event["headers"] = {
            "X-Line-User-Id": "U1234567890abcdef1234567890abcdef"
        }

        response = lambda_handler(base_event, None)

        # 認証成功を確認
        assert response["principalId"] == "U1234567890abcdef1234567890abcdef"
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Allow"
        assert response["context"]["authType"] == "line"
        assert response["context"]["userId"] == "internal-user-id-456"
        assert response["context"]["lineUserId"] == "U1234567890abcdef1234567890abcdef"

    @pytest.mark.unit
    def test_line_user_id_not_found(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: 存在しない LINE User ID はエラー
        """
        from authorizer import lambda_handler

        # DynamoDB がユーザーを見つけられない
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table

        base_event["headers"] = {
            "X-Line-User-Id": "U0000000000000000000000000000000"
        }

        response = lambda_handler(base_event, None)

        # 認証失敗（Deny）を確認
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    @pytest.mark.unit
    def test_line_user_id_invalid_format(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: 不正な形式の LINE User ID はエラー
        """
        from authorizer import lambda_handler

        # 不正な形式の LINE User ID
        base_event["headers"] = {
            "X-Line-User-Id": "invalid_line_id"
        }

        response = lambda_handler(base_event, None)

        # 認証失敗（Deny）を確認
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    # ===================================
    # 並行稼働テスト: 優先順位の検証
    # ===================================

    @pytest.mark.unit
    def test_cognito_takes_priority_over_line(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: Cognito JWT が X-Line-User-Id より優先
        """
        from authorizer import lambda_handler

        # Cognito 認証成功のモック
        mock_cognito_client.get_user.return_value = {
            "Username": "cognito-user",
            "UserAttributes": [
                {"Name": "sub", "Value": "cognito-sub-id"},
                {"Name": "email", "Value": "cognito@example.com"},
            ]
        }

        # 両方のヘッダーを設定
        base_event["headers"] = {
            "Authorization": "Bearer valid_cognito_token",
            "X-Line-User-Id": "U1234567890abcdef1234567890abcdef"
        }

        response = lambda_handler(base_event, None)

        # Cognito で認証されていることを確認
        assert response["context"]["authType"] == "cognito"
        assert response["context"]["userId"] == "cognito-sub-id"

        # DynamoDB は呼ばれていないことを確認（Cognito が優先）
        mock_dynamodb.Table.return_value.query.assert_not_called()

    @pytest.mark.unit
    def test_fallback_to_line_when_cognito_fails(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: Cognito 失敗時は X-Line-User-Id にフォールバック
        """
        from authorizer import lambda_handler
        from botocore.exceptions import ClientError

        # Cognito 認証失敗
        mock_cognito_client.get_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}},
            "GetUser"
        )

        # LINE User ID は有効
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "user_id": "line-internal-id",
                    "line_user_id": "U1234567890abcdef1234567890abcdef"
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        # 両方のヘッダーを設定
        base_event["headers"] = {
            "Authorization": "Bearer invalid_token",
            "X-Line-User-Id": "U1234567890abcdef1234567890abcdef"
        }

        response = lambda_handler(base_event, None)

        # LINE で認証されていることを確認（フォールバック）
        assert response["context"]["authType"] == "line"
        assert response["context"]["userId"] == "line-internal-id"

    # ===================================
    # エッジケース
    # ===================================

    @pytest.mark.unit
    def test_no_auth_headers(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: 認証ヘッダーなしはエラー
        """
        from authorizer import lambda_handler

        # ヘッダーなし
        base_event["headers"] = {}

        response = lambda_handler(base_event, None)

        # 認証失敗（Deny）を確認
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    @pytest.mark.unit
    def test_bearer_without_token(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: Bearer のみでトークンなしはエラー
        """
        from authorizer import lambda_handler
        from botocore.exceptions import ClientError

        # 空のトークンは Cognito API でエラーになる
        mock_cognito_client.get_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}},
            "GetUser"
        )

        base_event["headers"] = {
            "Authorization": "Bearer "
        }

        response = lambda_handler(base_event, None)

        # 空のトークンでも API 呼び出しが発生し、エラーになる
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    @pytest.mark.unit
    def test_case_insensitive_headers(self, mock_cognito_client, mock_dynamodb, base_event):
        """
        Feature: Cognito ID Federation, Property: ヘッダーは大文字小文字を区別しない
        """
        from authorizer import lambda_handler

        # 小文字のヘッダー名
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "user_id": "user-from-lowercase-header",
                    "line_user_id": "U1234567890abcdef1234567890abcdef"
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        base_event["headers"] = {
            "x-line-user-id": "U1234567890abcdef1234567890abcdef"
        }

        response = lambda_handler(base_event, None)

        # 認証成功を確認
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Allow"
        assert response["context"]["authType"] == "line"


class TestAuthorizerPolicyGeneration:
    """IAM ポリシー生成のテスト"""

    @pytest.mark.unit
    def test_policy_structure(self):
        """
        Feature: Cognito ID Federation, Property: ポリシー構造が正しい
        """
        from authorizer import generate_policy

        policy = generate_policy(
            "test-principal",
            "Allow",
            "arn:aws:execute-api:ap-northeast-1:123:api/dev/GET/users",
            {"userId": "test-user-id"}
        )

        assert policy["principalId"] == "test-principal"
        assert policy["policyDocument"]["Version"] == "2012-10-17"
        assert len(policy["policyDocument"]["Statement"]) == 1
        assert policy["policyDocument"]["Statement"][0]["Effect"] == "Allow"
        assert policy["policyDocument"]["Statement"][0]["Action"] == "execute-api:Invoke"
        assert policy["context"]["userId"] == "test-user-id"

    @pytest.mark.unit
    def test_policy_resource_wildcard(self):
        """
        Feature: Cognito ID Federation, Property: リソースARNがワイルドカード化される
        """
        from authorizer import generate_policy

        policy = generate_policy(
            "test-principal",
            "Allow",
            "arn:aws:execute-api:ap-northeast-1:123:api/dev/GET/users/profile"
        )

        # dev/* にワイルドカード化されている
        assert policy["policyDocument"]["Statement"][0]["Resource"].endswith("/dev/*")
