#!/usr/bin/env python3
"""
LINE ユーザー移行のデータ検証スクリプト

Feature: Cognito ID Federation, Phase 4.2

移行後の line_user_id と cognito_user_id の整合性を確認する。

使用方法:
    # 検証実行
    python scripts/validate_migration.py

    # 特定の環境を指定
    python scripts/validate_migration.py --environment prod

    # 詳細ログを出力
    python scripts/validate_migration.py --verbose

検証項目:
1. DynamoDB の line_user_id と cognito_user_id の対応が正しいか
2. Cognito の custom:line_user_id 属性が DynamoDB と一致するか
3. 移行漏れ（line_user_id があるが cognito_user_id がない）がないか
4. 孤立した Cognito ユーザー（DynamoDB に対応がない）がないか
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field
from typing import Iterator

import boto3
from botocore.exceptions import ClientError

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """検証結果"""
    total_users: int = 0
    line_users: int = 0
    cognito_users: int = 0
    migrated_users: int = 0
    pending_migration: int = 0
    mismatched: int = 0
    orphaned_cognito_users: int = 0
    errors: list = field(default_factory=list)


class MigrationValidator:
    """移行データを検証するクラス"""

    def __init__(
        self,
        environment: str = 'dev',
        region: str = 'ap-northeast-1'
    ):
        self.environment = environment
        self.region = region
        self.project_name = 'meal-management-app'

        # AWS クライアント
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.cognito = boto3.client('cognito-idp', region_name=region)

        # テーブル名
        self.users_table_name = f'{self.project_name}-users-{environment}'
        self.users_table = self.dynamodb.Table(self.users_table_name)

        # Cognito User Pool ID を取得
        self.user_pool_id = self._get_user_pool_id()

        logger.info(f"Environment: {environment}")
        logger.info(f"Users Table: {self.users_table_name}")
        logger.info(f"User Pool ID: {self.user_pool_id}")

    def _get_user_pool_id(self) -> str:
        """Cognito User Pool ID を取得"""
        user_pool_name = f'{self.project_name}-user-pool-{self.environment}'

        response = self.cognito.list_user_pools(MaxResults=60)
        for pool in response.get('UserPools', []):
            if pool['Name'] == user_pool_name:
                return pool['Id']

        raise ValueError(f"User Pool not found: {user_pool_name}")

    def scan_all_users(self) -> Iterator[dict]:
        """DynamoDB の全ユーザーをスキャン"""
        scan_kwargs = {}

        while True:
            response = self.users_table.scan(**scan_kwargs)
            for item in response.get('Items', []):
                yield item

            if 'LastEvaluatedKey' not in response:
                break
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    def get_cognito_user(self, username: str) -> dict | None:
        """Cognito ユーザーを取得"""
        try:
            response = self.cognito.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                return None
            raise

    def get_cognito_user_attribute(self, user: dict, attr_name: str) -> str | None:
        """Cognito ユーザーの属性を取得"""
        for attr in user.get('UserAttributes', []):
            if attr['Name'] == attr_name:
                return attr['Value']
        return None

    def list_cognito_line_users(self) -> Iterator[dict]:
        """Cognito の LINE ユーザー（プレースホルダーメールを持つユーザー）を列挙"""
        pagination_token = None

        while True:
            kwargs = {
                'UserPoolId': self.user_pool_id,
                'Filter': 'email ^= "U"',  # LINE User ID は U で始まる
                'Limit': 60
            }
            if pagination_token:
                kwargs['PaginationToken'] = pagination_token

            response = self.cognito.list_users(**kwargs)

            for user in response.get('Users', []):
                # プレースホルダーメール形式のユーザーのみ対象
                email = self.get_cognito_user_attribute(user, 'email')
                if email and email.endswith('@line.placeholder.local'):
                    yield user

            pagination_token = response.get('PaginationToken')
            if not pagination_token:
                break

    def validate_user(self, user: dict, result: ValidationResult) -> None:
        """単一ユーザーの検証"""
        user_id = user['user_id']
        line_user_id = user.get('line_user_id')
        cognito_user_id = user.get('cognito_user_id')

        result.total_users += 1

        if line_user_id:
            result.line_users += 1

        if cognito_user_id:
            result.cognito_users += 1

        # LINE ユーザーの場合の検証
        if line_user_id:
            if not cognito_user_id:
                # 移行漏れ
                result.pending_migration += 1
                logger.warning(f"Pending migration: {user_id} (LINE: {line_user_id[:10]}...)")
                result.errors.append({
                    'type': 'pending_migration',
                    'user_id': user_id,
                    'line_user_id': line_user_id
                })
            else:
                # 移行済み - Cognito との整合性確認
                result.migrated_users += 1
                # 移行スクリプトはプレースホルダーメールを username として使用
                placeholder_email = f'{line_user_id}@line.placeholder.local'
                cognito_user = self.get_cognito_user(placeholder_email)

                if not cognito_user:
                    # Cognito にユーザーが存在しない
                    logger.error(f"Cognito user not found: {placeholder_email}")
                    result.mismatched += 1
                    result.errors.append({
                        'type': 'cognito_user_missing',
                        'user_id': user_id,
                        'expected_username': placeholder_email,
                        'cognito_user_id': cognito_user_id
                    })
                else:
                    # sub の一致確認
                    cognito_sub = self.get_cognito_user_attribute(cognito_user, 'sub')
                    if cognito_sub != cognito_user_id:
                        logger.error(
                            f"Sub mismatch: {user_id} - "
                            f"DynamoDB: {cognito_user_id}, Cognito: {cognito_sub}"
                        )
                        result.mismatched += 1
                        result.errors.append({
                            'type': 'sub_mismatch',
                            'user_id': user_id,
                            'dynamodb_cognito_id': cognito_user_id,
                            'cognito_sub': cognito_sub
                        })

                    # custom:line_user_id の一致確認
                    cognito_line_id = self.get_cognito_user_attribute(
                        cognito_user, 'custom:line_user_id'
                    )
                    if cognito_line_id and cognito_line_id != line_user_id:
                        logger.error(
                            f"LINE ID mismatch: {user_id} - "
                            f"DynamoDB: {line_user_id}, Cognito: {cognito_line_id}"
                        )
                        result.mismatched += 1
                        result.errors.append({
                            'type': 'line_id_mismatch',
                            'user_id': user_id,
                            'dynamodb_line_id': line_user_id,
                            'cognito_line_id': cognito_line_id
                        })

    def validate_orphaned_cognito_users(self, result: ValidationResult) -> None:
        """孤立した Cognito ユーザーを検出"""
        logger.info("Checking for orphaned Cognito users...")

        for cognito_user in self.list_cognito_line_users():
            email = self.get_cognito_user_attribute(cognito_user, 'email')
            if not email:
                continue
            # プレースホルダーメールから LINE User ID を抽出
            line_user_id = email.replace('@line.placeholder.local', '')

            # DynamoDB で対応するユーザーを検索
            response = self.users_table.query(
                IndexName='LineUserIdIndex',
                KeyConditionExpression='line_user_id = :lid',
                ExpressionAttributeValues={':lid': line_user_id}
            )

            if not response.get('Items'):
                logger.warning(f"Orphaned Cognito user: {email}")
                result.orphaned_cognito_users += 1
                result.errors.append({
                    'type': 'orphaned_cognito_user',
                    'email': email,
                    'line_user_id': line_user_id
                })

    def run(self) -> ValidationResult:
        """検証を実行"""
        result = ValidationResult()

        logger.info("=" * 60)
        logger.info("Migration Data Validation")
        logger.info("=" * 60)

        # Step 1: DynamoDB ユーザーの検証
        logger.info("Validating DynamoDB users...")
        for user in self.scan_all_users():
            self.validate_user(user, result)

        # Step 2: 孤立した Cognito ユーザーの検出
        self.validate_orphaned_cognito_users(result)

        # 結果サマリー
        logger.info("=" * 60)
        logger.info("Validation Summary")
        logger.info("=" * 60)
        logger.info(f"Total DynamoDB users:      {result.total_users}")
        logger.info(f"Users with LINE ID:        {result.line_users}")
        logger.info(f"Users with Cognito ID:     {result.cognito_users}")
        logger.info(f"Migrated LINE users:       {result.migrated_users}")
        logger.info(f"Pending migration:         {result.pending_migration}")
        logger.info(f"Mismatched records:        {result.mismatched}")
        logger.info(f"Orphaned Cognito users:    {result.orphaned_cognito_users}")
        logger.info(f"Total errors:              {len(result.errors)}")

        if result.errors:
            logger.info("")
            logger.info("Errors found:")
            for error in result.errors[:10]:  # 最初の10件のみ表示
                logger.info(f"  - {error['type']}: {error}")
            if len(result.errors) > 10:
                logger.info(f"  ... and {len(result.errors) - 10} more errors")

        # 検証結果
        if result.pending_migration == 0 and result.mismatched == 0:
            logger.info("")
            logger.info("✅ Validation PASSED - All LINE users are properly migrated")
        else:
            logger.info("")
            logger.info("❌ Validation FAILED - Issues found")

        return result


def main():
    parser = argparse.ArgumentParser(
        description='LINE ユーザー移行のデータ検証'
    )
    parser.add_argument(
        '--environment', '-e',
        default='dev',
        choices=['dev', 'staging', 'prod'],
        help='対象環境 (default: dev)'
    )
    parser.add_argument(
        '--region', '-r',
        default='ap-northeast-1',
        help='AWS リージョン (default: ap-northeast-1)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを出力'
    )
    parser.add_argument(
        '--output-errors', '-o',
        help='エラーをJSONファイルに出力'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        validator = MigrationValidator(
            environment=args.environment,
            region=args.region
        )
        result = validator.run()

        # エラーをファイルに出力
        if args.output_errors and result.errors:
            import json
            with open(args.output_errors, 'w') as f:
                json.dump(result.errors, f, indent=2, ensure_ascii=False)
            logger.info(f"Errors written to: {args.output_errors}")

        # 問題があれば非ゼロで終了
        has_issues = result.pending_migration > 0 or result.mismatched > 0
        sys.exit(1 if has_issues else 0)

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
