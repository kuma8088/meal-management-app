"""
APIレスポンスヘルパー
"""
import json
from typing import Any, Dict, Optional
from .exceptions import AppException


def create_response(
    status_code: int,
    body: Any,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    API Gatewayレスポンスを作成する
    
    Args:
        status_code: HTTPステータスコード
        body: レスポンスボディ
        headers: 追加のヘッダー
        
    Returns:
        API Gatewayレスポンス
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, ensure_ascii=False)
    }


def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """
    成功レスポンスを作成する
    
    Args:
        data: レスポンスデータ
        status_code: HTTPステータスコード（デフォルト: 200）
        
    Returns:
        API Gatewayレスポンス
    """
    return create_response(status_code, data)


def error_response(
    error: Exception,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    エラーレスポンスを作成する
    
    Args:
        error: 例外オブジェクト
        request_id: リクエストID
        
    Returns:
        API Gatewayレスポンス
    """
    if isinstance(error, AppException):
        status_code = _get_status_code_from_error_code(error.code)
        error_body = {
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details
            }
        }
    else:
        status_code = 500
        error_body = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "内部エラーが発生しました",
                "details": {}
            }
        }
    
    if request_id:
        error_body["error"]["request_id"] = request_id
    
    return create_response(status_code, error_body)


def _get_status_code_from_error_code(error_code: str) -> int:
    """
    エラーコードからHTTPステータスコードを取得する
    
    Args:
        error_code: エラーコード
        
    Returns:
        HTTPステータスコード
    """
    status_code_map = {
        "VALIDATION_ERROR": 400,
        "AUTHENTICATION_ERROR": 401,
        "AUTHORIZATION_ERROR": 403,
        "RESOURCE_NOT_FOUND": 404,
        "DATA_INTEGRITY_ERROR": 409,
        "EXTERNAL_SERVICE_ERROR": 502,
        "RETRYABLE_ERROR": 503,
        "INTERNAL_ERROR": 500
    }
    
    return status_code_map.get(error_code, 500)
