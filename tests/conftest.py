"""
共通テストフィクスチャとヘルパー関数
"""
import pytest
import boto3
from moto import mock_dynamodb, mock_s3


@pytest.fixture
def aws_credentials(monkeypatch):
    """AWS認証情報のモック"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-1")


@pytest.fixture
def dynamodb_mock(aws_credentials):
    """DynamoDBのモック"""
    with mock_dynamodb():
        yield boto3.resource("dynamodb", region_name="ap-northeast-1")


@pytest.fixture
def s3_mock(aws_credentials):
    """S3のモック"""
    with mock_s3():
        yield boto3.client("s3", region_name="ap-northeast-1")
