"""
S3ヘルパー関数
"""
import boto3
from typing import Optional, BinaryIO, Union
from botocore.exceptions import ClientError
from .exceptions import RetryableError, ResourceNotFoundError
from .logger import get_logger
from .retry import exponential_backoff_retry

logger = get_logger(__name__)


class S3Helper:
    """S3操作のヘルパークラス"""
    
    def __init__(self, bucket_name: str, region_name: str = "ap-northeast-1"):
        """
        初期化
        
        Args:
            bucket_name: S3バケット名
            region_name: AWSリージョン名
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3", region_name=region_name)
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        ファイルをS3にアップロードする
        
        Args:
            file_path: アップロードするファイルのパス
            object_key: S3オブジェクトキー
            content_type: コンテンツタイプ
            
        Returns:
            S3オブジェクトのURL
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            url = f"s3://{self.bucket_name}/{object_key}"
            
            logger.info(
                f"ファイルをアップロードしました: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "url": url
                    }
                }
            )
            
            return url
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            logger.error(
                f"S3アップロードエラー: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "error_code": error_code,
                        "error": str(e)
                    }
                }
            )
            
            raise RetryableError(
                f"S3へのアップロードに失敗しました: {object_key}",
                details={"bucket": self.bucket_name, "key": object_key, "error": str(e)}
            )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        ファイルオブジェクトをS3にアップロードする
        
        Args:
            file_obj: アップロードするファイルオブジェクト
            object_key: S3オブジェクトキー
            content_type: コンテンツタイプ
            
        Returns:
            S3オブジェクトのURL
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            url = f"s3://{self.bucket_name}/{object_key}"
            
            logger.info(
                f"ファイルオブジェクトをアップロードしました: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "url": url
                    }
                }
            )
            
            return url
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            logger.error(
                f"S3アップロードエラー: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "error_code": error_code,
                        "error": str(e)
                    }
                }
            )
            
            raise RetryableError(
                f"S3へのアップロードに失敗しました: {object_key}",
                details={"bucket": self.bucket_name, "key": object_key, "error": str(e)}
            )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def download_file(self, object_key: str, file_path: str) -> None:
        """
        S3からファイルをダウンロードする
        
        Args:
            object_key: S3オブジェクトキー
            file_path: ダウンロード先のファイルパス
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
            ResourceNotFoundError: オブジェクトが存在しない場合
        """
        try:
            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                file_path
            )
            
            logger.info(
                f"ファイルをダウンロードしました: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "path": file_path
                    }
                }
            )
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code in ["NoSuchKey", "404"]:
                raise ResourceNotFoundError(
                    f"S3オブジェクトが見つかりません: {object_key}",
                    details={"bucket": self.bucket_name, "key": object_key}
                )
            
            logger.error(
                f"S3ダウンロードエラー: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "error_code": error_code,
                        "error": str(e)
                    }
                }
            )
            
            raise RetryableError(
                f"S3からのダウンロードに失敗しました: {object_key}",
                details={"bucket": self.bucket_name, "key": object_key, "error": str(e)}
            )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def get_object(self, object_key: str) -> bytes:
        """
        S3オブジェクトの内容を取得する
        
        Args:
            object_key: S3オブジェクトキー
            
        Returns:
            オブジェクトの内容（バイト列）
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
            ResourceNotFoundError: オブジェクトが存在しない場合
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            content = response["Body"].read()
            
            logger.info(
                f"オブジェクトを取得しました: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "size": len(content)
                    }
                }
            )
            
            return content
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code == "NoSuchKey":
                raise ResourceNotFoundError(
                    f"S3オブジェクトが見つかりません: {object_key}",
                    details={"bucket": self.bucket_name, "key": object_key}
                )
            
            logger.error(
                f"S3取得エラー: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "error_code": error_code,
                        "error": str(e)
                    }
                }
            )
            
            raise RetryableError(
                f"S3オブジェクトの取得に失敗しました: {object_key}",
                details={"bucket": self.bucket_name, "key": object_key, "error": str(e)}
            )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def put_object(
        self,
        object_key: str,
        body: Union[bytes, str],
        content_type: Optional[str] = None
    ) -> str:
        """
        S3にオブジェクトを保存する
        
        Args:
            object_key: S3オブジェクトキー
            body: オブジェクトの内容
            content_type: コンテンツタイプ
            
        Returns:
            S3オブジェクトのURL
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            put_params = {
                "Bucket": self.bucket_name,
                "Key": object_key,
                "Body": body
            }
            
            if content_type:
                put_params["ContentType"] = content_type
            
            self.s3_client.put_object(**put_params)
            
            url = f"s3://{self.bucket_name}/{object_key}"
            
            logger.info(
                f"オブジェクトを保存しました: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "url": url
                    }
                }
            )
            
            return url
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            logger.error(
                f"S3保存エラー: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "error_code": error_code,
                        "error": str(e)
                    }
                }
            )
            
            raise RetryableError(
                f"S3への保存に失敗しました: {object_key}",
                details={"bucket": self.bucket_name, "key": object_key, "error": str(e)}
            )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def delete_object(self, object_key: str) -> None:
        """
        S3オブジェクトを削除する
        
        Args:
            object_key: S3オブジェクトキー
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(
                f"オブジェクトを削除しました: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key
                    }
                }
            )
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            logger.error(
                f"S3削除エラー: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "error_code": error_code,
                        "error": str(e)
                    }
                }
            )
            
            raise RetryableError(
                f"S3オブジェクトの削除に失敗しました: {object_key}",
                details={"bucket": self.bucket_name, "key": object_key, "error": str(e)}
            )
    
    @exponential_backoff_retry(
        max_retries=3,
        retryable_exceptions=(RetryableError, ClientError)
    )
    def object_exists(self, object_key: str) -> bool:
        """
        S3オブジェクトが存在するか確認する
        
        Args:
            object_key: S3オブジェクトキー
            
        Returns:
            存在する場合True、存在しない場合False
            
        Raises:
            RetryableError: リトライ可能なエラーが発生した場合
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            
            if error_code == "404":
                return False
            
            logger.error(
                f"S3存在確認エラー: {object_key}",
                extra={
                    "extra_data": {
                        "bucket": self.bucket_name,
                        "key": object_key,
                        "error_code": error_code,
                        "error": str(e)
                    }
                }
            )
            
            raise RetryableError(
                f"S3オブジェクトの存在確認に失敗しました: {object_key}",
                details={"bucket": self.bucket_name, "key": object_key, "error": str(e)}
            )
