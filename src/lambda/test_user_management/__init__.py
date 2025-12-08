"""
テストユーザー管理 Lambda関数

E2Eテスト用のテストユーザーを Cognito で作成・削除・管理する。
"""
import json
import os
import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime

# Cognito クライアント
cognito_client = boto3.client("cognito-idp", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))

# 環境変数
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")


class TestUserManager:
    """テストユーザー管理クラス"""

    def __init__(self, user_pool_id: str, client_id: str):
        """
        初期化

        Args:
            user_pool_id: Cognito User Pool ID
            client_id: Cognito Client ID
        """
        self.user_pool_id = user_pool_id
        self.client_id = client_id

    def create_test_user(self, email: str, password: str, user_attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        テストユーザーを作成

        Args:
            email: メールアドレス
            password: パスワード
            user_attributes: ユーザー属性（オプション）

        Returns:
            作成されたユーザー情報

        Raises:
            Exception: ユーザー作成失敗
        """
        try:
            # ユーザー属性の準備
            attributes = [
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ]

            # 追加属性があれば合わせる
            if user_attributes:
                for key, value in user_attributes.items():
                    attributes.append({"Name": key, "Value": value})

            # ユーザーを作成
            response = cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                TemporaryPassword=password,
                UserAttributes=attributes,
                MessageAction="SUPPRESS",  # ウェルカムメール送信しない
            )

            # パスワードを永続パスワードに設定
            cognito_client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
                Password=password,
                Permanent=True,
            )

            return {
                "success": True,
                "username": response["User"]["Username"],
                "email": email,
                "user_created_date": response["User"]["UserCreateDate"].isoformat(),
            }

        except Exception as e:
            raise Exception(f"テストユーザー作成失敗: {str(e)}")

    def delete_test_user(self, email: str) -> Dict[str, Any]:
        """
        テストユーザーを削除

        Args:
            email: メールアドレス

        Returns:
            削除結果

        Raises:
            Exception: ユーザー削除失敗
        """
        try:
            cognito_client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=email,
            )

            return {
                "success": True,
                "message": f"ユーザー {email} を削除しました",
                "email": email,
            }

        except Exception as e:
            raise Exception(f"テストユーザー削除失敗: {str(e)}")

    def get_test_user(self, email: str) -> Dict[str, Any]:
        """
        テストユーザー情報を取得

        Args:
            email: メールアドレス

        Returns:
            ユーザー情報

        Raises:
            Exception: ユーザー取得失敗
        """
        try:
            response = cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=email,
            )

            # ユーザー属性をDictに変換
            attributes = {}
            for attr in response["UserAttributes"]:
                attributes[attr["Name"]] = attr["Value"]

            return {
                "success": True,
                "username": response["Username"],
                "user_status": response["UserStatus"],
                "attributes": attributes,
                "user_create_date": response["UserCreateDate"].isoformat(),
                "user_last_modified_date": response["UserLastModifiedDate"].isoformat(),
            }

        except Exception as e:
            raise Exception(f"テストユーザー取得失敗: {str(e)}")

    def list_test_users(self, filter_prefix: str = "testuser-") -> List[Dict[str, Any]]:
        """
        テストユーザーをリスト取得

        Args:
            filter_prefix: フィルタープレフィックス（デフォルト: testuser-）

        Returns:
            テストユーザーのリスト

        Raises:
            Exception: ユーザーリスト取得失敗
        """
        try:
            response = cognito_client.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f'email ^= "{filter_prefix}"',
                Limit=60,
            )

            users = []
            for user in response.get("Users", []):
                attributes = {}
                for attr in user["Attributes"]:
                    attributes[attr["Name"]] = attr["Value"]

                users.append({
                    "username": user["Username"],
                    "user_status": user["UserStatus"],
                    "attributes": attributes,
                    "user_create_date": user["UserCreateDate"].isoformat(),
                })

            return users

        except Exception as e:
            raise Exception(f"テストユーザーリスト取得失敗: {str(e)}")

    def reset_test_user_password(self, email: str, new_password: str) -> Dict[str, Any]:
        """
        テストユーザーのパスワードをリセット

        Args:
            email: メールアドレス
            new_password: 新しいパスワード

        Returns:
            リセット結果

        Raises:
            Exception: パスワードリセット失敗
        """
        try:
            cognito_client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
                Password=new_password,
                Permanent=True,
            )

            return {
                "success": True,
                "message": f"ユーザー {email} のパスワードをリセットしました",
                "email": email,
            }

        except Exception as e:
            raise Exception(f"パスワードリセット失敗: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda ハンドラー

    操作タイプに基づいて、テストユーザーを管理する

    Query Parameters:
        - operation: create | delete | get | list | reset_password
        - email: ユーザーメールアドレス
        - password: パスワード（create時必須）
        - name: ユーザー名（create時オプション）

    Returns:
        実行結果
    """
    try:
        # パラメータ取得
        query_params = event.get("queryStringParameters", {}) or {}
        operation = query_params.get("operation", "").lower()
        email = query_params.get("email", "").strip()

        # ユーザーマネージャー初期化
        manager = TestUserManager(COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID)

        # 操作実行
        if operation == "create":
            password = query_params.get("password", "")
            name = query_params.get("name", "Test User")

            if not password:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "password パラメータが必須です",
                    }),
                }

            user_attributes = {"name": name} if name else {}
            result = manager.create_test_user(email, password, user_attributes)
            return {
                "statusCode": 201,
                "body": json.dumps(result),
            }

        elif operation == "delete":
            if not email:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "email パラメータが必須です",
                    }),
                }

            result = manager.delete_test_user(email)
            return {
                "statusCode": 200,
                "body": json.dumps(result),
            }

        elif operation == "get":
            if not email:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "email パラメータが必須です",
                    }),
                }

            result = manager.get_test_user(email)
            return {
                "statusCode": 200,
                "body": json.dumps(result),
            }

        elif operation == "list":
            filter_prefix = query_params.get("filter_prefix", "testuser-")
            result = manager.list_test_users(filter_prefix)
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "user_count": len(result),
                    "users": result,
                }),
            }

        elif operation == "reset_password":
            new_password = query_params.get("new_password", "")

            if not new_password:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "new_password パラメータが必須です",
                    }),
                }

            result = manager.reset_test_user_password(email, new_password)
            return {
                "statusCode": 200,
                "body": json.dumps(result),
            }

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"不正な operation: {operation}",
                    "valid_operations": ["create", "delete", "get", "list", "reset_password"],
                }),
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "内部エラー",
                "message": str(e),
            }),
        }
