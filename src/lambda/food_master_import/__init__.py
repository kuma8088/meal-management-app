"""
食品マスタデータインポート Lambda関数

日本食品標準成分表やOpen Food Factsからデータをインポートし、
DynamoDBとS3に保存する。

要件: 2.1, 2.2, 2.3
"""
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

# src/lambda/commonをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from common import (
    DynamoDBHelper,
    S3Helper,
    get_logger,
    success_response,
    error_response,
    Food,
    FoodMasterImporter,
    ValidationError,
    ExternalServiceError,
)

logger = get_logger(__name__)


class FoodMasterImportHandler:
    """食品マスタインポートハンドラー"""

    def __init__(self):
        """初期化"""
        self.importer = FoodMasterImporter()
        self.dynamodb = DynamoDBHelper(
            table_name=os.environ.get('FOODS_TABLE', 'Foods')
        )
        self.s3 = S3Helper(
            bucket_name=os.environ.get('FOOD_MASTER_BUCKET', 'food-master')
        )

    def handle_import_csv(
        self,
        csv_content: str,
        source_name: str = "standard"
    ) -> Tuple[int, int, List[str]]:
        """
        CSVをインポート

        Args:
            csv_content: CSV形式の文字列
            source_name: ソース名（ログ用）

        Returns:
            (インポート成功数, 失敗数, エラーメッセージリスト)
        """
        imported_count = 0
        failed_count = 0
        errors = []

        logger.info(f"Starting food master import from {source_name}")

        try:
            # CSVをパース
            foods, parse_errors = self.importer.import_from_csv(csv_content)
            errors.extend(parse_errors)

            if not foods:
                error_msg = f"No valid foods parsed from {source_name}"
                logger.warning(error_msg)
                errors.append(error_msg)
                return imported_count, failed_count, errors

            # DynamoDBに保存
            imported_count, failed_items = self._save_to_dynamodb(foods)
            failed_count = len(failed_items)

            if failed_items:
                error_msg = f"Failed to save {failed_count} items to DynamoDB"
                logger.warning(error_msg)
                errors.append(error_msg)

            # S3に CSV を保存
            s3_errors = self._save_csv_to_s3(csv_content, source_name)
            errors.extend(s3_errors)

            logger.info(
                f"Food import completed: "
                f"imported={imported_count}, failed={failed_count}"
            )

        except Exception as e:
            error_msg = f"Unexpected error during import: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            failed_count += 1

        return imported_count, failed_count, errors

    def _save_to_dynamodb(self, foods: List[Food]) -> Tuple[int, List[Food]]:
        """
        DynamoDBに食品データを保存

        Args:
            foods: 保存対象の食品リスト

        Returns:
            (成功数, 失敗リスト)
        """
        successful = 0
        failed = []

        batch_size = 25  # DynamoDBバッチ制限

        for i in range(0, len(foods), batch_size):
            batch = foods[i:i + batch_size]

            try:
                with self.dynamodb.batch_writer(
                    overwrite_by_pkeys=['food_id']
                ) as batch_writer:
                    for food in batch:
                        item = food.to_dict()
                        batch_writer.put_item(Item=item)

                successful += len(batch)
                logger.info(f"Saved {len(batch)} foods to DynamoDB")

            except Exception as e:
                logger.error(f"Batch save failed: {str(e)}")
                failed.extend(batch)

        return successful, failed

    def _save_csv_to_s3(
        self,
        csv_content: str,
        source_name: str
    ) -> List[str]:
        """
        CSVをS3に保存

        Args:
            csv_content: CSV形式の文字列
            source_name: ソース名

        Returns:
            エラーメッセージリスト
        """
        errors = []

        try:
            timestamp = datetime.utcnow().isoformat()
            key = f"food-master/{source_name}_{timestamp}.csv"

            self.s3.put_object(
                key=key,
                body=csv_content.encode('utf-8'),
                content_type='text/csv'
            )

            logger.info(f"CSV saved to S3: {key}")

        except Exception as e:
            error_msg = f"Failed to save CSV to S3: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        return errors


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda ハンドラー

    期待されるイベント:
    {
        "action": "import_csv" | "import_url",
        "source": "standard" | "open_food_facts",
        "csv_content": "...",  # action=import_csv の場合
        "csv_url": "...",       # action=import_url の場合
    }
    """
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'

    logger.info(f"Food master import handler invoked: {event}")

    try:
        action = event.get('action', 'import_csv')
        source = event.get('source', 'standard')

        handler = FoodMasterImportHandler()

        if action == 'import_csv':
            csv_content = event.get('csv_content')
            if not csv_content:
                return error_response(
                    "csv_content is required",
                    request_id=request_id
                )

            imported, failed, errors = handler.handle_import_csv(
                csv_content,
                source_name=source
            )

            return success_response({
                'imported_count': imported,
                'failed_count': failed,
                'errors': errors
            }, request_id=request_id)

        elif action == 'import_url':
            csv_url = event.get('csv_url')
            if not csv_url:
                return error_response(
                    "csv_url is required",
                    request_id=request_id
                )

            imported, failed, errors = handler._import_from_url(csv_url, source)
            return success_response({
                'imported_count': imported,
                'failed_count': failed,
                'errors': errors
            }, request_id=request_id)

        else:
            return error_response(
                f"Unknown action: {action}",
                request_id=request_id
            )

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return error_response(
            str(e),
            request_id=request_id,
            status_code=400
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return error_response(
            "Internal server error",
            request_id=request_id,
            status_code=500
        )


# For local testing
if __name__ == "__main__":
    # テスト用イベント
    test_event = {
        "action": "import_csv",
        "source": "standard",
        "csv_content": """食品名,エネルギー（kcal）,たんぱく質（g）,脂質（g）,炭水化物（g）,JANコード
白米,168,2.5,0.3,37.1,1234567890123
食パン,265,9.3,4.4,48.5,9876543210987"""
    }

    class MockContext:
        request_id = "test-request-id"

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
