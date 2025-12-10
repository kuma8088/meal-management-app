"""
DynamoDBヘルパー関数
"""
import boto3
from typing import Dict, List, Any, Optional
from decimal import Decimal
from botocore.exceptions import ClientError
from .exceptions import RetryableError, ResourceNotFoundError, DataIntegrityError
from .logger import get_logger
from .retry import exponential_backoff_retry

logger = get_logger(__name__)


class DynamoDBHelper:
    """DynamoDB操作のヘルパークラス"""
    
    def __init__(self, table_name: str, region_name: str = "ap-northeast-1"):
        """
        初期化
        
        Args:
            table_name: DynamoDBテーブル名
            region_name: AWSリージョン名
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(table_name)
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        アイテムを保存する
        
        Args:
            item: 保存するアイテム
            
        Returns:
            保存されたアイテム
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
            DataIntegrityError: データ整合性エラーが発生した場合
        """
        try:
            # PythonのfloatをDecimalに変換
            item = self._convert_floats_to_decimal(item)
            
            response = self.table.put_item(Item=item)
            
            logger.info(
                f"アイテムを保存しました: {self.table_name}",
                extra={
                    "extra_data": {
                        "table": self.table_name,
                        "item_keys": list(item.keys())
                    }
                }
            )
            
            return item
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code in ["ProvisionedThroughputExceededException", "RequestLimitExceeded"]:
                raise RetryableError(
                    f"DynamoDBのスループット制限に達しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            elif error_code == "ConditionalCheckFailedException":
                raise DataIntegrityError(
                    f"条件チェックに失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            else:
                logger.error(
                    f"DynamoDBエラー: {self.table_name}",
                    extra={
                        "extra_data": {
                            "table": self.table_name,
                            "error_code": error_code,
                            "error": str(e)
                        }
                    }
                )
                raise RetryableError(
                    f"DynamoDB操作に失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        アイテムを取得する
        
        Args:
            key: 取得するアイテムのキー
            
        Returns:
            取得されたアイテム（存在しない場合はNone）
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            key = self._convert_floats_to_decimal(key)
            
            response = self.table.get_item(Key=key)
            item = response.get("Item")
            
            if item:
                # Decimalをfloatに変換
                item = self._convert_decimals_to_float(item)
                
                logger.info(
                    f"アイテムを取得しました: {self.table_name}",
                    extra={
                        "extra_data": {
                            "table": self.table_name,
                            "key": key
                        }
                    }
                )
            
            return item
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code in ["ProvisionedThroughputExceededException", "RequestLimitExceeded"]:
                raise RetryableError(
                    f"DynamoDBのスループット制限に達しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            else:
                logger.error(
                    f"DynamoDBエラー: {self.table_name}",
                    extra={
                        "extra_data": {
                            "table": self.table_name,
                            "error_code": error_code,
                            "error": str(e)
                        }
                    }
                )
                raise RetryableError(
                    f"DynamoDB操作に失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def query(
        self,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True
    ) -> List[Dict[str, Any]]:
        """
        クエリを実行する
        
        Args:
            key_condition_expression: キー条件式
            expression_attribute_values: 式の属性値
            expression_attribute_names: 式の属性名
            index_name: インデックス名（GSIを使用する場合）
            limit: 取得する最大アイテム数
            scan_index_forward: ソート順（Trueで昇順、Falseで降順）
            
        Returns:
            取得されたアイテムのリスト
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            expression_attribute_values = self._convert_floats_to_decimal(expression_attribute_values)
            
            query_params = {
                "KeyConditionExpression": key_condition_expression,
                "ExpressionAttributeValues": expression_attribute_values,
                "ScanIndexForward": scan_index_forward
            }
            
            if expression_attribute_names:
                query_params["ExpressionAttributeNames"] = expression_attribute_names
            
            if index_name:
                query_params["IndexName"] = index_name
            
            if limit:
                query_params["Limit"] = limit
            
            response = self.table.query(**query_params)
            items = response.get("Items", [])
            
            # Decimalをfloatに変換
            items = [self._convert_decimals_to_float(item) for item in items]
            
            logger.info(
                f"クエリを実行しました: {self.table_name}",
                extra={
                    "extra_data": {
                        "table": self.table_name,
                        "index": index_name,
                        "count": len(items)
                    }
                }
            )
            
            return items
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code in ["ProvisionedThroughputExceededException", "RequestLimitExceeded"]:
                raise RetryableError(
                    f"DynamoDBのスループット制限に達しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            else:
                logger.error(
                    f"DynamoDBエラー: {self.table_name}",
                    extra={
                        "extra_data": {
                            "table": self.table_name,
                            "error_code": error_code,
                            "error": str(e)
                        }
                    }
                )
                raise RetryableError(
                    f"DynamoDB操作に失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        アイテムを更新する
        
        Args:
            key: 更新するアイテムのキー
            update_expression: 更新式
            expression_attribute_values: 式の属性値
            expression_attribute_names: 式の属性名
            condition_expression: 条件式
            
        Returns:
            更新されたアイテム
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
            DataIntegrityError: データ整合性エラーが発生した場合
        """
        try:
            key = self._convert_floats_to_decimal(key)
            expression_attribute_values = self._convert_floats_to_decimal(expression_attribute_values)
            
            update_params = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_attribute_values,
                "ReturnValues": "ALL_NEW"
            }
            
            if expression_attribute_names:
                update_params["ExpressionAttributeNames"] = expression_attribute_names
            
            if condition_expression:
                update_params["ConditionExpression"] = condition_expression
            
            response = self.table.update_item(**update_params)
            item = response.get("Attributes", {})
            
            # Decimalをfloatに変換
            item = self._convert_decimals_to_float(item)
            
            logger.info(
                f"アイテムを更新しました: {self.table_name}",
                extra={
                    "extra_data": {
                        "table": self.table_name,
                        "key": key
                    }
                }
            )
            
            return item
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code in ["ProvisionedThroughputExceededException", "RequestLimitExceeded"]:
                raise RetryableError(
                    f"DynamoDBのスループット制限に達しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            elif error_code == "ConditionalCheckFailedException":
                raise DataIntegrityError(
                    f"条件チェックに失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            else:
                logger.error(
                    f"DynamoDBエラー: {self.table_name}",
                    extra={
                        "extra_data": {
                            "table": self.table_name,
                            "error_code": error_code,
                            "error": str(e)
                        }
                    }
                )
                raise RetryableError(
                    f"DynamoDB操作に失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        テーブルをスキャンする

        ページネーションを使用してフィルタ条件に一致するアイテムを取得する。
        limit は「結果として取得したいアイテム数」として扱われる。

        Args:
            filter_expression: フィルタ式
            expression_attribute_values: 式の属性値
            expression_attribute_names: 式の属性名
            limit: 取得する最大アイテム数（フィルタ適用後の結果数）
            max_pages: 最大ページネーション回数（デフォルト10）

        Returns:
            取得されたアイテムのリスト

        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            scan_params = {}

            if filter_expression:
                scan_params["FilterExpression"] = filter_expression

            if expression_attribute_values:
                expression_attribute_values = self._convert_floats_to_decimal(expression_attribute_values)
                scan_params["ExpressionAttributeValues"] = expression_attribute_values

            if expression_attribute_names:
                scan_params["ExpressionAttributeNames"] = expression_attribute_names

            # ページネーションで結果を収集
            all_items = []
            pages_scanned = 0
            last_evaluated_key = None

            while pages_scanned < max_pages:
                if last_evaluated_key:
                    scan_params["ExclusiveStartKey"] = last_evaluated_key

                response = self.table.scan(**scan_params)
                items = response.get("Items", [])
                all_items.extend(items)
                pages_scanned += 1

                # limit に達したら終了
                if limit and len(all_items) >= limit:
                    all_items = all_items[:limit]
                    break

                # 次のページがなければ終了
                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break

            # Decimalをfloatに変換
            all_items = [self._convert_decimals_to_float(item) for item in all_items]

            logger.info(
                f"スキャンを実行しました: {self.table_name}",
                extra={
                    "extra_data": {
                        "table": self.table_name,
                        "count": len(all_items),
                        "pages_scanned": pages_scanned
                    }
                }
            )

            return all_items

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code in ["ProvisionedThroughputExceededException", "RequestLimitExceeded"]:
                raise RetryableError(
                    f"DynamoDBのスループット制限に達しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            else:
                logger.error(
                    f"DynamoDBエラー: {self.table_name}",
                    extra={
                        "extra_data": {
                            "table": self.table_name,
                            "error_code": error_code,
                            "error": str(e)
                        }
                    }
                )
                raise RetryableError(
                    f"DynamoDB操作に失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )

    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def delete_item(self, key: Dict[str, Any]) -> None:
        """
        アイテムを削除する
        
        Args:
            key: 削除するアイテムのキー
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            key = self._convert_floats_to_decimal(key)
            
            self.table.delete_item(Key=key)
            
            logger.info(
                f"アイテムを削除しました: {self.table_name}",
                extra={
                    "extra_data": {
                        "table": self.table_name,
                        "key": key
                    }
                }
            )
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code in ["ProvisionedThroughputExceededException", "RequestLimitExceeded"]:
                raise RetryableError(
                    f"DynamoDBのスループット制限に達しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
            else:
                logger.error(
                    f"DynamoDBエラー: {self.table_name}",
                    extra={
                        "extra_data": {
                            "table": self.table_name,
                            "error_code": error_code,
                            "error": str(e)
                        }
                    }
                )
                raise RetryableError(
                    f"DynamoDB操作に失敗しました: {self.table_name}",
                    details={"table": self.table_name, "error": str(e)}
                )
    
    def _convert_floats_to_decimal(self, obj: Any) -> Any:
        """
        floatをDecimalに変換する（DynamoDB用）
        
        Args:
            obj: 変換するオブジェクト
            
        Returns:
            変換されたオブジェクト
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(item) for item in obj]
        else:
            return obj
    
    def _convert_decimals_to_float(self, obj: Any) -> Any:
        """
        Decimalをfloatに変換する（Python用）
        
        Args:
            obj: 変換するオブジェクト
            
        Returns:
            変換されたオブジェクト
        """
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_float(item) for item in obj]
        else:
            return obj
