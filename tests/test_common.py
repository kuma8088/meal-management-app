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


class TestBMRCalculator:
    """BMR/TDEE計算のテスト"""
    
    def test_calculate_bmr_male(self):
        """男性のBMR計算が正しく動作することを確認"""
        from common import BMRCalculator, Gender
        
        # テストケース: 30歳、175cm、70kgの男性
        # 期待値: 88.362 + (13.397 × 70) + (4.799 × 175) - (5.677 × 30)
        #       = 88.362 + 937.79 + 839.825 - 170.31
        #       = 1695.67
        bmr = BMRCalculator.calculate_bmr(
            age=30,
            height=175.0,
            weight=70.0,
            gender=Gender.MALE
        )
        
        assert bmr == 1695.67
    
    def test_calculate_bmr_female(self):
        """女性のBMR計算が正しく動作することを確認"""
        from common import BMRCalculator, Gender
        
        # テストケース: 25歳、160cm、55kgの女性
        # 期待値: 447.593 + (9.247 × 55) + (3.098 × 160) - (4.330 × 25)
        #       = 447.593 + 508.585 + 495.68 - 108.25
        #       = 1343.61
        bmr = BMRCalculator.calculate_bmr(
            age=25,
            height=160.0,
            weight=55.0,
            gender=Gender.FEMALE
        )
        
        assert bmr == 1343.61
    
    def test_calculate_bmr_invalid_age(self):
        """無効な年齢でValidationErrorが発生することを確認"""
        from common import BMRCalculator, Gender, ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            BMRCalculator.calculate_bmr(
                age=0,
                height=175.0,
                weight=70.0,
                gender=Gender.MALE
            )
        assert "年齢" in str(exc_info.value.message)
        
        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(
                age=-5,
                height=175.0,
                weight=70.0,
                gender=Gender.MALE
            )
    
    def test_calculate_bmr_invalid_height(self):
        """無効な身長でValidationErrorが発生することを確認"""
        from common import BMRCalculator, Gender, ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            BMRCalculator.calculate_bmr(
                age=30,
                height=0,
                weight=70.0,
                gender=Gender.MALE
            )
        assert "身長" in str(exc_info.value.message)
        
        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(
                age=30,
                height=-10,
                weight=70.0,
                gender=Gender.MALE
            )
    
    def test_calculate_bmr_invalid_weight(self):
        """無効な体重でValidationErrorが発生することを確認"""
        from common import BMRCalculator, Gender, ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            BMRCalculator.calculate_bmr(
                age=30,
                height=175.0,
                weight=0,
                gender=Gender.MALE
            )
        assert "体重" in str(exc_info.value.message)
        
        with pytest.raises(ValidationError):
            BMRCalculator.calculate_bmr(
                age=30,
                height=175.0,
                weight=-5,
                gender=Gender.MALE
            )
    
    def test_calculate_tdee_sedentary(self):
        """ほとんど運動しない場合のTDEE計算が正しく動作することを確認"""
        from common import BMRCalculator, ActivityLevel
        
        bmr = 1695.67
        tdee = BMRCalculator.calculate_tdee(bmr, ActivityLevel.SEDENTARY)
        
        # 期待値: 1695.67 × 1.2 = 2034.80
        assert tdee == 2034.80
    
    def test_calculate_tdee_light(self):
        """軽い運動の場合のTDEE計算が正しく動作することを確認"""
        from common import BMRCalculator, ActivityLevel
        
        bmr = 1695.67
        tdee = BMRCalculator.calculate_tdee(bmr, ActivityLevel.LIGHT)
        
        # 期待値: 1695.67 × 1.375 = 2331.55
        assert tdee == 2331.55
    
    def test_calculate_tdee_moderate(self):
        """中程度の運動の場合のTDEE計算が正しく動作することを確認"""
        from common import BMRCalculator, ActivityLevel
        
        bmr = 1695.67
        tdee = BMRCalculator.calculate_tdee(bmr, ActivityLevel.MODERATE)
        
        # 期待値: 1695.67 × 1.55 = 2628.29
        assert tdee == 2628.29
    
    def test_calculate_tdee_active(self):
        """激しい運動の場合のTDEE計算が正しく動作することを確認"""
        from common import BMRCalculator, ActivityLevel
        
        bmr = 1695.67
        tdee = BMRCalculator.calculate_tdee(bmr, ActivityLevel.ACTIVE)
        
        # 期待値: 1695.67 × 1.725 = 2925.03
        assert tdee == 2925.03
    
    def test_calculate_tdee_very_active(self):
        """非常に激しい運動の場合のTDEE計算が正しく動作することを確認"""
        from common import BMRCalculator, ActivityLevel
        
        bmr = 1695.67
        tdee = BMRCalculator.calculate_tdee(bmr, ActivityLevel.VERY_ACTIVE)
        
        # 期待値: 1695.67 × 1.9 = 3221.77
        assert tdee == 3221.77
    
    def test_calculate_tdee_invalid_bmr(self):
        """無効なBMRでValidationErrorが発生することを確認"""
        from common import BMRCalculator, ActivityLevel, ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            BMRCalculator.calculate_tdee(-100, ActivityLevel.SEDENTARY)
        assert "BMR" in str(exc_info.value.message)
    
    def test_calculate_bmr_and_tdee(self):
        """BMRとTDEEを一度に計算できることを確認"""
        from common import BMRCalculator, Gender, ActivityLevel
        
        result = BMRCalculator.calculate_bmr_and_tdee(
            age=30,
            height=175.0,
            weight=70.0,
            gender=Gender.MALE,
            activity_level=ActivityLevel.MODERATE
        )
        
        assert "bmr" in result
        assert "tdee" in result
        assert result["bmr"] == 1695.67
        assert result["tdee"] == 2628.29
    
    def test_calculate_bmr_and_tdee_female(self):
        """女性のBMRとTDEEを一度に計算できることを確認"""
        from common import BMRCalculator, Gender, ActivityLevel
        
        result = BMRCalculator.calculate_bmr_and_tdee(
            age=25,
            height=160.0,
            weight=55.0,
            gender=Gender.FEMALE,
            activity_level=ActivityLevel.LIGHT
        )
        
        assert result["bmr"] == 1343.61
        # 1343.61 × 1.375 = 1847.46
        assert result["tdee"] == 1847.46


class TestNutritionCalculator:
    """栄養計算のテスト"""
    
    def test_calculate_nutrition_for_amount(self):
        """指定された量の食品の栄養情報が正しく計算されることを確認"""
        from common import Food, FoodSource, NutritionCalculator
        
        # テスト用の食品を作成（100gあたりの栄養情報）
        food = Food(
            food_id="test-food-1",
            name="テスト食品",
            calories_per_100g=200.0,
            protein_per_100g=20.0,
            fat_per_100g=10.0,
            carbs_per_100g=30.0,
            source=FoodSource.STANDARD
        )
        
        # 100gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 100.0)
        assert nutrition["calories"] == 200.0
        assert nutrition["protein"] == 20.0
        assert nutrition["fat"] == 10.0
        assert nutrition["carbs"] == 30.0
        
        # 50gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 50.0)
        assert nutrition["calories"] == 100.0
        assert nutrition["protein"] == 10.0
        assert nutrition["fat"] == 5.0
        assert nutrition["carbs"] == 15.0
        
        # 200gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 200.0)
        assert nutrition["calories"] == 400.0
        assert nutrition["protein"] == 40.0
        assert nutrition["fat"] == 20.0
        assert nutrition["carbs"] == 60.0
        
        # 0gの場合
        nutrition = NutritionCalculator.calculate_nutrition_for_amount(food, 0.0)
        assert nutrition["calories"] == 0.0
        assert nutrition["protein"] == 0.0
        assert nutrition["fat"] == 0.0
        assert nutrition["carbs"] == 0.0
    
    def test_calculate_nutrition_for_amount_negative(self):
        """負の量でValidationErrorが発生することを確認"""
        from common import Food, FoodSource, NutritionCalculator, ValidationError
        
        food = Food(
            food_id="test-food-1",
            name="テスト食品",
            calories_per_100g=200.0,
            protein_per_100g=20.0,
            fat_per_100g=10.0,
            carbs_per_100g=30.0,
            source=FoodSource.STANDARD
        )
        
        with pytest.raises(ValidationError):
            NutritionCalculator.calculate_nutrition_for_amount(food, -10.0)
    
    def test_calculate_total_nutrition(self):
        """複数の食品の栄養情報が正しく合計されることを確認"""
        from common import NutritionCalculator
        
        foods_nutrition = [
            {"calories": 100.0, "protein": 10.0, "fat": 5.0, "carbs": 15.0},
            {"calories": 200.0, "protein": 20.0, "fat": 10.0, "carbs": 30.0},
            {"calories": 150.0, "protein": 15.0, "fat": 7.5, "carbs": 22.5}
        ]
        
        total = NutritionCalculator.calculate_total_nutrition(foods_nutrition)
        
        assert total["total_calories"] == 450.0
        assert total["total_protein"] == 45.0
        assert total["total_fat"] == 22.5
        assert total["total_carbs"] == 67.5
    
    def test_calculate_total_nutrition_empty(self):
        """空のリストで0が返されることを確認"""
        from common import NutritionCalculator
        
        total = NutritionCalculator.calculate_total_nutrition([])
        
        assert total["total_calories"] == 0.0
        assert total["total_protein"] == 0.0
        assert total["total_fat"] == 0.0
        assert total["total_carbs"] == 0.0
    
    def test_calculate_total_nutrition_single_item(self):
        """単一の食品で正しく動作することを確認"""
        from common import NutritionCalculator
        
        foods_nutrition = [
            {"calories": 100.0, "protein": 10.0, "fat": 5.0, "carbs": 15.0}
        ]
        
        total = NutritionCalculator.calculate_total_nutrition(foods_nutrition)
        
        assert total["total_calories"] == 100.0
        assert total["total_protein"] == 10.0
        assert total["total_fat"] == 5.0
        assert total["total_carbs"] == 15.0
    
    def test_calculate_meal_nutrition(self):
        """食事全体の栄養情報が正しく計算されることを確認"""
        from common import Food, MealFood, FoodSource, NutritionCalculator
        
        # テスト用の食品データベースを作成
        food1 = Food(
            food_id="food-1",
            name="食品1",
            calories_per_100g=200.0,
            protein_per_100g=20.0,
            fat_per_100g=10.0,
            carbs_per_100g=30.0,
            source=FoodSource.STANDARD
        )
        
        food2 = Food(
            food_id="food-2",
            name="食品2",
            calories_per_100g=300.0,
            protein_per_100g=15.0,
            fat_per_100g=20.0,
            carbs_per_100g=40.0,
            source=FoodSource.STANDARD
        )
        
        food_database = {
            "food-1": food1,
            "food-2": food2
        }
        
        # 食事に含まれる食品
        meal_foods = [
            MealFood(food_id="food-1", amount=100.0),  # 100g
            MealFood(food_id="food-2", amount=50.0)    # 50g
        ]
        
        # 栄養情報を計算
        nutrition = NutritionCalculator.calculate_meal_nutrition(meal_foods, food_database)
        
        # 期待値: food1(100g) + food2(50g)
        # calories: 200 + 150 = 350
        # protein: 20 + 7.5 = 27.5
        # fat: 10 + 10 = 20
        # carbs: 30 + 20 = 50
        assert nutrition["total_calories"] == 350.0
        assert nutrition["total_protein"] == 27.5
        assert nutrition["total_fat"] == 20.0
        assert nutrition["total_carbs"] == 50.0
    
    def test_calculate_meal_nutrition_food_not_found(self):
        """存在しない食品IDでValidationErrorが発生することを確認"""
        from common import MealFood, NutritionCalculator, ValidationError
        
        food_database = {}
        meal_foods = [
            MealFood(food_id="non-existent", amount=100.0)
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            NutritionCalculator.calculate_meal_nutrition(meal_foods, food_database)
        
        assert "non-existent" in str(exc_info.value.message)
