"""
Lambda Authorizer テスト

Feature: Cognito ID Federation, Phase 5
Cognito JWT トークンのみをサポート
"""
import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

# src/lambda/authorizer をインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "authorizer"))


class TestAuthorizerCognitoOnly:
    """Cognito JWT 認証テスト"""

    @pytest.fixture
    def mock_cognito_client(self):
        """Cognito クライアントのモック"""
        with patch('authorizer.cognito_client') as mock:
            yield mock

    @pytest.fixture
    def base_event(self):
        """基本イベント構造"""
        return {
            "methodArn": "arn:aws:execute-api:ap-northeast-1:123456789:api-id/dev/GET/users",
            "headers": {}
        }

    @pytest.mark.unit
    def test_cognito_jwt_auth_success(self, mock_cognito_client, base_event):
        """
        Feature: Cognito ID Federation, Property: Cognito JWT トークンで認証成功
        """
        from authorizer import lambda_handler

        mock_cognito_client.get_user.return_value = {
            "Username": "test-user",
            "UserAttributes": [
                {"Name": "sub", "Value": "cognito-user-id-123"},
                {"Name": "email", "Value": "test@example.com"},
            ]
        }

        base_event["headers"] = {
            "Authorization": "Bearer valid_cognito_token"
        }

        response = lambda_handler(base_event, None)

        assert response["principalId"] == "cognito-user-id-123"
        assert response["policyDocument"]["Statement"][0]["Effect"] == "Allow"
        assert response["context"]["authType"] == "cognito"
        assert response["context"]["userId"] == "cognito-user-id-123"
        assert response["context"]["email"] == "test@example.com"

        mock_cognito_client.get_user.assert_called_once_with(AccessToken="valid_cognito_token")

    @pytest.mark.unit
    def test_cognito_jwt_auth_failure(self, mock_cognito_client, base_event):
        """
        Feature: Cognito ID Federation, Property: 無効な Cognito JWT はエラー
        """
        from authorizer import lambda_handler
        from botocore.exceptions import ClientError

        mock_cognito_client.get_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}},
            "GetUser"
        )

        base_event["headers"] = {
            "Authorization": "Bearer invalid_token"
        }

        response = lambda_handler(base_event, None)

        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    @pytest.mark.unit
    def test_no_auth_headers(self, mock_cognito_client, base_event):
        """
        Feature: Cognito ID Federation, Property: 認証ヘッダーなしはエラー
        """
        from authorizer import lambda_handler

        base_event["headers"] = {}

        response = lambda_handler(base_event, None)

        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    @pytest.mark.unit
    def test_bearer_without_token(self, mock_cognito_client, base_event):
        """
        Feature: Cognito ID Federation, Property: Bearer のみでトークンなしはエラー
        """
        from authorizer import lambda_handler
        from botocore.exceptions import ClientError

        mock_cognito_client.get_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}},
            "GetUser"
        )

        base_event["headers"] = {
            "Authorization": "Bearer "
        }

        response = lambda_handler(base_event, None)

        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    @pytest.mark.unit
    def test_case_insensitive_headers(self, mock_cognito_client, base_event):
        """
        Feature: Cognito ID Federation, Property: ヘッダーは大文字小文字を区別しない
        """
        from authorizer import lambda_handler

        mock_cognito_client.get_user.return_value = {
            "Username": "test-user",
            "UserAttributes": [
                {"Name": "sub", "Value": "cognito-user-id"},
                {"Name": "email", "Value": "test@example.com"},
            ]
        }

        base_event["headers"] = {
            "authorization": "Bearer valid_token"  # 小文字
        }

        response = lambda_handler(base_event, None)

        assert response["policyDocument"]["Statement"][0]["Effect"] == "Allow"

    @pytest.mark.unit
    def test_user_not_found(self, mock_cognito_client, base_event):
        """
        Feature: Cognito ID Federation, Property: ユーザーが見つからない場合はエラー
        """
        from authorizer import lambda_handler
        from botocore.exceptions import ClientError

        mock_cognito_client.get_user.side_effect = ClientError(
            {"Error": {"Code": "UserNotFoundException", "Message": "User not found"}},
            "GetUser"
        )

        base_event["headers"] = {
            "Authorization": "Bearer token_for_deleted_user"
        }

        response = lambda_handler(base_event, None)

        assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"


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

        assert policy["policyDocument"]["Statement"][0]["Resource"].endswith("/dev/*")
