"""
パフォーマンステスト（Locust）

使用方法:
    # ヘッドレスモード（10ユーザー、60秒間）
    locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 60s --host https://868t2tljy9.execute-api.ap-northeast-1.amazonaws.com/dev

    # WebUIモード
    locust -f tests/performance/locustfile.py --host https://868t2tljy9.execute-api.ap-northeast-1.amazonaws.com/dev
"""

import os
import json
import time
from locust import HttpUser, task, between
import boto3


class MealManagementUser(HttpUser):
    """食事管理アプリのパフォーマンステストユーザー"""

    wait_time = between(1, 3)  # リクエスト間隔: 1-3秒

    def on_start(self):
        """テスト開始時に認証トークンを取得"""
        self.token = self._get_auth_token()
        self.user_id = os.environ.get("TEST_USER_ID", "test-user-id")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _get_auth_token(self):
        """Cognitoからトークンを取得"""
        # 環境変数からトークンを取得（事前に設定が必要）
        token = os.environ.get("TEST_AUTH_TOKEN")
        if token:
            return token

        # トークンがない場合はCognitoから取得を試行
        try:
            client = boto3.client('cognito-idp', region_name='ap-northeast-1')
            user_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "ap-northeast-1_fmIO9wUwC")
            client_id = os.environ.get("COGNITO_CLIENT_ID", "7fjjol84obkgbj4mh29qtjp6i8")
            username = os.environ.get("TEST_USERNAME", "e2e-test@example.com")
            password = os.environ.get("TEST_PASSWORD", "TestPassword123!")

            response = client.initiate_auth(
                ClientId=client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            return response['AuthenticationResult']['IdToken']
        except Exception as e:
            print(f"認証エラー: {e}")
            return "dummy-token"

    @task(3)
    def get_profile(self):
        """プロフィール取得（高頻度）"""
        with self.client.get(
            f"/users/{self.user_id}/profile",
            headers=self.headers,
            name="/users/{user_id}/profile [GET]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("認証エラー")
            elif response.status_code == 404:
                response.success()  # プロフィール未作成も正常
            else:
                response.failure(f"エラー: {response.status_code}")

    @task(2)
    def search_food_by_name(self):
        """食品名検索"""
        queries = ["白米", "鶏肉", "豆腐", "卵", "牛乳"]
        query = queries[int(time.time()) % len(queries)]

        with self.client.get(
            f"/foods/search?query={query}&search_type=name&limit=10",
            headers=self.headers,
            name="/foods/search [GET]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"エラー: {response.status_code}")

    @task(2)
    def get_meals(self):
        """食事記録一覧取得"""
        with self.client.get(
            f"/users/{self.user_id}/meals?limit=20",
            headers=self.headers,
            name="/users/{user_id}/meals [GET]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"エラー: {response.status_code}")

    @task(1)
    def get_goals(self):
        """目標取得"""
        with self.client.get(
            f"/users/{self.user_id}/goals",
            headers=self.headers,
            name="/users/{user_id}/goals [GET]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"エラー: {response.status_code}")

    @task(1)
    def get_daily_summary(self):
        """1日の総評取得"""
        today = time.strftime("%Y-%m-%d")
        with self.client.get(
            f"/users/{self.user_id}/summary/{today}",
            headers=self.headers,
            name="/users/{user_id}/summary/{date} [GET]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"エラー: {response.status_code}")


class HealthCheckUser(HttpUser):
    """ヘルスチェック専用ユーザー（認証不要）"""

    wait_time = between(2, 5)
    weight = 1  # 低い重み

    @task
    def health_check(self):
        """APIヘルスチェック"""
        with self.client.get(
            "/health",
            name="/health [GET]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"エラー: {response.status_code}")
