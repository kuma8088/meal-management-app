"""
共通ライブラリのテスト
"""
import pytest
import sys
import io
import tempfile
from pathlib import Path
from decimal import Decimal
from botocore.exceptions import ClientError

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "lambda"))

from common import (
    ValidationError,
    ResourceNotFoundError,
    RetryableError,
    DataIntegrityError,
    get_logger,
    validate_required,
    validate_positive_number,
    validate_non_negative_number,
    validate_range,
    validate_choice,
    validate_date_format,
    validate_email,
    validate_string_length,
    success_response,
    error_response,
    DynamoDBHelper,
    S3Helper
)


class TestExceptions:
    """例外クラスのテスト"""
    
    def test_validation_error(self):
        """ValidationErrorが正しく動作することを確認"""
        error = ValidationError("テストエラー", details={"field": "test"})
        assert error.message == "テストエラー"
        assert error.code == "VALIDATION_ERROR"
        assert error.details["field"] == "test"
    
    def test_resource_not_found_error(self):
        """ResourceNotFoundErrorが正しく動作することを確認"""
        error = ResourceNotFoundError("リソースが見つかりません")
        assert error.code == "RESOURCE_NOT_FOUND"


class TestLogger:
    """ロガーのテスト"""
    
    def test_get_logger(self):
        """ロガーが取得できることを確認"""
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"


class TestValidation:
    """バリデーションのテスト"""
    
    def test_validate_required_success(self):
        """必須フィールドの検証が成功することを確認"""
        validate_required("test", "field")
        validate_required("  test  ", "field")  # 空白を含む文字列
        validate_required(0, "field")  # 0も有効
        validate_required(False, "field")  # Falseも有効
        # 例外が発生しなければ成功
    
    def test_validate_required_failure(self):
        """必須フィールドの検証が失敗することを確認"""
        with pytest.raises(ValidationError) as exc_info:
            validate_required(None, "field")
        assert "field" in str(exc_info.value.message)
        
        with pytest.raises(ValidationError):
            validate_required("", "field")
        
        with pytest.raises(ValidationError):
            validate_required("   ", "field")  # 空白のみ
    
    def test_validate_positive_number_success(self):
        """正の数値の検証が成功することを確認"""
        validate_positive_number(10, "field")
        validate_positive_number(0.1, "field")
        validate_positive_number(1, "field")
    
    def test_validate_positive_number_failure(self):
        """正の数値の検証が失敗することを確認"""
        with pytest.raises(ValidationError):
            validate_positive_number(0, "field")
        
        with pytest.raises(ValidationError):
            validate_positive_number(-1, "field")
        
        with pytest.raises(ValidationError):
            validate_positive_number("not a number", "field")
    
    def test_validate_non_negative_number_success(self):
        """非負の数値の検証が成功することを確認"""
        validate_non_negative_number(0, "field")
        validate_non_negative_number(10, "field")
        validate_non_negative_number(0.5, "field")
    
    def test_validate_non_negative_number_failure(self):
        """非負の数値の検証が失敗することを確認"""
        with pytest.raises(ValidationError):
            validate_non_negative_number(-1, "field")
        
        with pytest.raises(ValidationError):
            validate_non_negative_number(-0.1, "field")
    
    def test_validate_range_success(self):
        """範囲の検証が成功することを確認"""
        validate_range(5, "field", 0, 10)
        validate_range(0, "field", 0, 10)
        validate_range(10, "field", 0, 10)
    
    def test_validate_range_failure(self):
        """範囲の検証が失敗することを確認"""
        with pytest.raises(ValidationError):
            validate_range(-1, "field", 0, 10)
        
        with pytest.raises(ValidationError):
            validate_range(11, "field", 0, 10)
    
    def test_validate_choice_success(self):
        """選択肢の検証が成功することを確認"""
        validate_choice("option1", "field", ["option1", "option2"])
        validate_choice("option2", "field", ["option1", "option2"])
    
    def test_validate_choice_failure(self):
        """選択肢の検証が失敗することを確認"""
        with pytest.raises(ValidationError) as exc_info:
            validate_choice("option3", "field", ["option1", "option2"])
        assert "option1" in str(exc_info.value.message)
        assert "option2" in str(exc_info.value.message)
    
    def test_validate_date_format_success(self):
        """日付形式の検証が成功することを確認"""
        validate_date_format("2024-01-01", "field")
        validate_date_format("2024-12-31", "field")
    
    def test_validate_date_format_failure(self):
        """日付形式の検証が失敗することを確認"""
        with pytest.raises(ValidationError):
            validate_date_format("2024/01/01", "field")
        
        with pytest.raises(ValidationError):
            validate_date_format("invalid", "field")
        
        with pytest.raises(ValidationError):
            validate_date_format("2024-13-01", "field")  # 無効な月
    
    def test_validate_email_success(self):
        """メールアドレスの検証が成功することを確認"""
        validate_email("test@example.com", "email")
        validate_email("user.name@example.co.jp", "email")
    
    def test_validate_email_failure(self):
        """メールアドレスの検証が失敗することを確認"""
        with pytest.raises(ValidationError):
            validate_email("invalid", "email")
        
        with pytest.raises(ValidationError):
            validate_email("test@invalid", "email")  # ドットがない
        
        with pytest.raises(ValidationError):
            validate_email("test@", "email")  # @の後に何もない
    
    def test_validate_string_length_success(self):
        """文字列長の検証が成功することを確認"""
        validate_string_length("test", "field", min_length=1, max_length=10)
        validate_string_length("test", "field", min_length=4, max_length=4)
    
    def test_validate_string_length_failure(self):
        """文字列長の検証が失敗することを確認"""
        with pytest.raises(ValidationError):
            validate_string_length("test", "field", min_length=5)
        
        with pytest.raises(ValidationError):
            validate_string_length("test", "field", max_length=3)
        
        with pytest.raises(ValidationError):
            validate_string_length(123, "field")  # 文字列でない


class TestResponse:
    """レスポンスヘルパーのテスト"""
    
    def test_success_response(self):
        """成功レスポンスが正しく作成されることを確認"""
        response = success_response({"message": "success"})
        assert response["statusCode"] == 200
        assert "application/json" in response["headers"]["Content-Type"]
        assert "success" in response["body"]
    
    def test_error_response(self):
        """エラーレスポンスが正しく作成されることを確認"""
        error = ValidationError("テストエラー")
        response = error_response(error)
        assert response["statusCode"] == 400
        assert "VALIDATION_ERROR" in response["body"]


class TestDynamoDBHelper:
    """DynamoDBヘルパーのテスト"""
    
    def test_initialization(self, dynamodb_mock):
        """DynamoDBヘルパーが初期化できることを確認"""
        # テーブルを作成
        dynamodb_mock.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        helper = DynamoDBHelper("test-table")
        assert helper.table_name == "test-table"
        assert helper.table is not None
    
    def test_put_and_get_item(self, dynamodb_mock):
        """アイテムの保存と取得ができることを確認"""
        # テーブルを作成
        dynamodb_mock.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        helper = DynamoDBHelper("test-table")
        
        # アイテムを保存
        item = {"id": "test-id", "name": "テスト", "value": 123.45}
        result = helper.put_item(item)
        assert result["id"] == "test-id"
        
        # アイテムを取得
        retrieved = helper.get_item({"id": "test-id"})
        assert retrieved is not None
        assert retrieved["id"] == "test-id"
        assert retrieved["name"] == "テスト"
        assert retrieved["value"] == 123.45
    
    def test_get_item_not_found(self, dynamodb_mock):
        """存在しないアイテムの取得でNoneが返ることを確認"""
        dynamodb_mock.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        helper = DynamoDBHelper("test-table")
        retrieved = helper.get_item({"id": "non-existent"})
        assert retrieved is None
    
    def test_query(self, dynamodb_mock):
        """クエリが正しく動作することを確認"""
        dynamodb_mock.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        helper = DynamoDBHelper("test-table")
        
        # テストデータを保存
        helper.put_item({"pk": "user1", "sk": "2024-01-01", "value": 100})
        helper.put_item({"pk": "user1", "sk": "2024-01-02", "value": 200})
        helper.put_item({"pk": "user2", "sk": "2024-01-01", "value": 300})
        
        # クエリを実行
        results = helper.query(
            key_condition_expression="pk = :pk",
            expression_attribute_values={":pk": "user1"}
        )
        
        assert len(results) == 2
        assert all(item["pk"] == "user1" for item in results)
    
    def test_update_item(self, dynamodb_mock):
        """アイテムの更新が正しく動作することを確認"""
        dynamodb_mock.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        helper = DynamoDBHelper("test-table")
        
        # アイテムを保存
        helper.put_item({"id": "test-id", "value": 100})
        
        # アイテムを更新
        updated = helper.update_item(
            key={"id": "test-id"},
            update_expression="SET #v = :val",
            expression_attribute_names={"#v": "value"},
            expression_attribute_values={":val": 200}
        )
        
        assert updated["value"] == 200
    
    def test_delete_item(self, dynamodb_mock):
        """アイテムの削除が正しく動作することを確認"""
        dynamodb_mock.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        helper = DynamoDBHelper("test-table")
        
        # アイテムを保存
        helper.put_item({"id": "test-id", "value": 100})
        
        # アイテムを削除
        helper.delete_item({"id": "test-id"})
        
        # 削除されたことを確認
        retrieved = helper.get_item({"id": "test-id"})
        assert retrieved is None
    
    def test_float_to_decimal_conversion(self, dynamodb_mock):
        """floatとDecimalの変換が正しく動作することを確認"""
        dynamodb_mock.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        helper = DynamoDBHelper("test-table")
        
        # floatを含むアイテムを保存
        item = {
            "id": "test-id",
            "float_value": 123.45,
            "nested": {
                "float_value": 67.89
            },
            "list_values": [1.1, 2.2, 3.3]
        }
        helper.put_item(item)
        
        # 取得して確認
        retrieved = helper.get_item({"id": "test-id"})
        assert isinstance(retrieved["float_value"], float)
        assert retrieved["float_value"] == 123.45
        assert isinstance(retrieved["nested"]["float_value"], float)
        assert retrieved["list_values"][0] == 1.1


class TestS3Helper:
    """S3ヘルパーのテスト"""
    
    def test_initialization(self, s3_mock):
        """S3ヘルパーが初期化できることを確認"""
        helper = S3Helper("test-bucket")
        assert helper.bucket_name == "test-bucket"
        assert helper.s3_client is not None
    
    def test_put_and_get_object(self, s3_mock):
        """オブジェクトの保存と取得ができることを確認"""
        # バケットを作成
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        # オブジェクトを保存
        content = "テストコンテンツ"
        url = helper.put_object("test-key", content)
        assert url == "s3://test-bucket/test-key"
        
        # オブジェクトを取得
        retrieved = helper.get_object("test-key")
        assert retrieved.decode("utf-8") == content
    
    def test_put_object_with_content_type(self, s3_mock):
        """コンテンツタイプを指定してオブジェクトを保存できることを確認"""
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        # コンテンツタイプを指定して保存
        helper.put_object("test.json", '{"key": "value"}', content_type="application/json")
        
        # オブジェクトを取得
        retrieved = helper.get_object("test.json")
        assert retrieved.decode("utf-8") == '{"key": "value"}'
    
    def test_get_object_not_found(self, s3_mock):
        """存在しないオブジェクトの取得でResourceNotFoundErrorが発生することを確認"""
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        with pytest.raises(ResourceNotFoundError):
            helper.get_object("non-existent-key")
    
    def test_upload_file(self, s3_mock):
        """ファイルのアップロードができることを確認"""
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("テストファイル")
            temp_path = f.name
        
        try:
            # ファイルをアップロード
            url = helper.upload_file(temp_path, "uploaded.txt")
            assert url == "s3://test-bucket/uploaded.txt"
            
            # アップロードされたことを確認
            retrieved = helper.get_object("uploaded.txt")
            assert retrieved.decode("utf-8") == "テストファイル"
        finally:
            # 一時ファイルを削除
            Path(temp_path).unlink()
    
    def test_upload_fileobj(self, s3_mock):
        """ファイルオブジェクトのアップロードができることを確認"""
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        # ファイルオブジェクトを作成
        file_obj = io.BytesIO(b"test content")
        
        # アップロード
        url = helper.upload_fileobj(file_obj, "uploaded.txt")
        assert url == "s3://test-bucket/uploaded.txt"
        
        # アップロードされたことを確認
        retrieved = helper.get_object("uploaded.txt")
        assert retrieved == b"test content"
    
    def test_download_file(self, s3_mock):
        """ファイルのダウンロードができることを確認"""
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        # オブジェクトを保存
        helper.put_object("test.txt", "ダウンロードテスト")
        
        # 一時ファイルパスを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            # ファイルをダウンロード
            helper.download_file("test.txt", temp_path)
            
            # ダウンロードされたことを確認
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "ダウンロードテスト"
        finally:
            # 一時ファイルを削除
            Path(temp_path).unlink()
    
    def test_download_file_not_found(self, s3_mock):
        """存在しないファイルのダウンロードでResourceNotFoundErrorが発生することを確認"""
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(ResourceNotFoundError):
                helper.download_file("non-existent.txt", temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_delete_object(self, s3_mock):
        """オブジェクトの削除ができることを確認"""
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        # オブジェクトを保存
        helper.put_object("test-key", "content")
        assert helper.object_exists("test-key")
        
        # オブジェクトを削除
        helper.delete_object("test-key")
        
        # 削除されたことを確認
        assert not helper.object_exists("test-key")
    
    def test_object_exists(self, s3_mock):
        """オブジェクトの存在確認ができることを確認"""
        # バケットを作成
        s3_mock.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        helper = S3Helper("test-bucket")
        
        # 存在しないオブジェクト
        assert not helper.object_exists("non-existent-key")
        
        # オブジェクトを保存
        helper.put_object("test-key", "content")
        
        # 存在するオブジェクト
        assert helper.object_exists("test-key")
