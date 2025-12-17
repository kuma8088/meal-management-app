"""
LIFF Login API のユニットテスト

Feature: Cognito ID Federation, Phase 3.1
"""
import pytest
import json
import base64
from unittest.mock import MagicMock, patch, ANY
from botocore.exceptions import ClientError

# テスト対象
import sys
from pathlib import Path

# src/lambda/liff_loginをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda" / "liff_login"))


class TestExtractUsernameFromToken:
    """LINE ID Token からユーザー名を抽出するテスト"""

    def test_extract_username_success(self):
        """
        Feature: Cognito ID Federation, Property: LINE ID Token の sub claim を正しく抽出
        """
        from liff_login import _extract_username_from_token

        # 有効な LINE ID Token をモック（署名検証なし）
        payload = {
            "sub": "U1234567890abcdef1234567890abcdef",
            "iss": "https://access.line.me",
            "aud": "1234567890",
            "exp": 9999999999,
            "iat": 1234567890,
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")

        # JWT 形式: header.payload.signature
        mock_token = f"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.fake_signature"

        result = _extract_username_from_token(mock_token)

        assert result == "line_U1234567890abcdef1234567890abcdef"

    def test_extract_username_invalid_jwt_format(self):
        """
        Feature: Cognito ID Federation, Property: 不正な JWT 形式はエラー
        """
        from liff_login import _extract_username_from_token

        # JWT 形式でないトークン
        result = _extract_username_from_token("invalid_token")
        assert result is None

    def test_extract_username_missing_sub(self):
        """
        Feature: Cognito ID Federation, Property: sub claim がない場合はエラー
        """
        from liff_login import _extract_username_from_token

        payload = {
            "iss": "https://access.line.me",
            "aud": "1234567890",
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")

        mock_token = f"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.fake_signature"

        result = _extract_username_from_token(mock_token)
        assert result is None


class TestParseRequestBody:
    """リクエストボディのパースをテスト"""

    def test_parse_json_string_body(self):
        """JSON 文字列のボディをパース"""
        from liff_login import _parse_request_body

        event = {"body": '{"line_id_token": "test_token"}'}
        result = _parse_request_body(event)

        assert result == {"line_id_token": "test_token"}

    def test_parse_dict_body(self):
        """辞書型のボディをそのまま返す"""
        from liff_login import _parse_request_body

        event = {"body": {"line_id_token": "test_token"}}
        result = _parse_request_body(event)

        assert result == {"line_id_token": "test_token"}

    def test_parse_empty_body(self):
        """空のボディは空の辞書を返す"""
        from liff_login import _parse_request_body

        event = {"body": ""}
        result = _parse_request_body(event)

        assert result == {}

    def test_parse_none_body(self):
        """None のボディは空の辞書を返す"""
        from liff_login import _parse_request_body

        event = {}
        result = _parse_request_body(event)

        assert result == {}


class TestLambdaHandler:
    """Lambda ハンドラーの統合テスト"""

    @pytest.fixture
    def mock_cognito_client(self):
        """Cognito クライアントのモック"""
        with patch('liff_login.cognito_client') as mock:
            yield mock

    @pytest.fixture
    def valid_line_token(self):
        """有効な LINE ID Token を生成"""
        payload = {
            "sub": "U1234567890abcdef1234567890abcdef",
            "iss": "https://access.line.me",
            "aud": "1234567890",
            "exp": 9999999999,
            "iat": 1234567890,
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")

        return f"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.fake_signature"

    @pytest.mark.unit
    def test_missing_token_returns_400(self, mock_cognito_client):
        """
        Feature: Cognito ID Federation, Property: line_id_token 必須
        """
        from liff_login import lambda_handler

        event = {"body": "{}"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "MISSING_TOKEN"

    @pytest.mark.unit
    def test_invalid_token_returns_400(self, mock_cognito_client):
        """
        Feature: Cognito ID Federation, Property: 不正なトークンは 400 エラー
        """
        from liff_login import lambda_handler

        event = {"body": json.dumps({"line_id_token": "invalid"})}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "INVALID_TOKEN"

    @pytest.mark.unit
    @patch('liff_login.USER_POOL_ID', 'ap-northeast-1_test')
    @patch('liff_login.CLIENT_ID', 'test_client_id')
    def test_successful_auth_returns_tokens(self, mock_cognito_client, valid_line_token):
        """
        Feature: Cognito ID Federation, Property: 認証成功時に Cognito トークンを返却
        """
        from liff_login import lambda_handler

        # AdminInitiateAuth のモック
        mock_cognito_client.admin_initiate_auth.return_value = {
            "ChallengeName": "CUSTOM_CHALLENGE",
            "Session": "test_session",
            "ChallengeParameters": {"nonce": "test_nonce"}
        }

        # AdminRespondToAuthChallenge のモック
        mock_cognito_client.admin_respond_to_auth_challenge.return_value = {
            "AuthenticationResult": {
                "IdToken": "test_id_token",
                "AccessToken": "test_access_token",
                "RefreshToken": "test_refresh_token",
                "ExpiresIn": 3600,
                "TokenType": "Bearer"
            }
        }

        event = {
            "body": json.dumps({
                "line_id_token": valid_line_token,
                "line_user_id": "U1234567890abcdef1234567890abcdef"
            })
        }
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["id_token"] == "test_id_token"
        assert body["access_token"] == "test_access_token"
        assert body["refresh_token"] == "test_refresh_token"

    @pytest.mark.unit
    @patch('liff_login.USER_POOL_ID', 'ap-northeast-1_test')
    @patch('liff_login.CLIENT_ID', 'test_client_id')
    def test_user_not_found_creates_new_user(self, mock_cognito_client, valid_line_token):
        """
        Feature: Cognito ID Federation, Property: ユーザーが存在しない場合は新規作成
        """
        from liff_login import lambda_handler

        # 初回の AdminInitiateAuth で UserNotFoundException
        mock_cognito_client.admin_initiate_auth.side_effect = [
            ClientError(
                {"Error": {"Code": "UserNotFoundException", "Message": "User not found"}},
                "AdminInitiateAuth"
            ),
            # 2回目は成功
            {
                "ChallengeName": "CUSTOM_CHALLENGE",
                "Session": "test_session",
                "ChallengeParameters": {"nonce": "test_nonce"}
            }
        ]

        # AdminCreateUser のモック
        mock_cognito_client.admin_create_user.return_value = {}
        mock_cognito_client.admin_set_user_password.return_value = {}

        # AdminRespondToAuthChallenge のモック
        mock_cognito_client.admin_respond_to_auth_challenge.return_value = {
            "AuthenticationResult": {
                "IdToken": "test_id_token",
                "AccessToken": "test_access_token",
                "RefreshToken": "test_refresh_token",
                "ExpiresIn": 3600,
                "TokenType": "Bearer"
            }
        }

        event = {
            "body": json.dumps({
                "line_id_token": valid_line_token,
                "line_user_id": "U1234567890abcdef1234567890abcdef"
            })
        }
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        # AdminCreateUser が呼ばれたことを確認
        mock_cognito_client.admin_create_user.assert_called_once()

    @pytest.mark.unit
    @patch('liff_login.USER_POOL_ID', 'ap-northeast-1_test')
    @patch('liff_login.CLIENT_ID', 'test_client_id')
    def test_cognito_error_returns_500(self, mock_cognito_client, valid_line_token):
        """
        Feature: Cognito ID Federation, Property: Cognito エラーは 500 エラー
        """
        from liff_login import lambda_handler

        # 予期しない Cognito エラー
        mock_cognito_client.admin_initiate_auth.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal error"}},
            "AdminInitiateAuth"
        )

        event = {
            "body": json.dumps({
                "line_id_token": valid_line_token,
                "line_user_id": "U1234567890abcdef1234567890abcdef"
            })
        }
        response = lambda_handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"]["code"] == "COGNITO_ERROR"


class TestCorsHeaders:
    """CORS ヘッダーのテスト"""

    def test_cors_headers_present(self):
        """
        Feature: Cognito ID Federation, Property: CORS ヘッダーが正しく設定される
        """
        from liff_login import _cors_headers

        headers = _cors_headers()

        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "Content-Type" in headers["Access-Control-Allow-Headers"]
        assert "POST" in headers["Access-Control-Allow-Methods"]


class TestErrorResponse:
    """エラーレスポンスのテスト"""

    def test_error_response_format(self):
        """
        Feature: Cognito ID Federation, Property: エラーレスポンスの形式
        """
        from liff_login import _error_response

        response = _error_response(400, "TEST_ERROR", "Test error message")

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "TEST_ERROR"
        assert body["error"]["message"] == "Test error message"
