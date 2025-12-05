"""
カスタム例外クラス
"""


class AppException(Exception):
    """アプリケーション基底例外"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """バリデーションエラー"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class AuthenticationError(AppException):
    """認証エラー"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(AppException):
    """認可エラー"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="AUTHORIZATION_ERROR", details=details)


class ResourceNotFoundError(AppException):
    """リソースが見つからないエラー"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="RESOURCE_NOT_FOUND", details=details)


class DataIntegrityError(AppException):
    """データ整合性エラー"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="DATA_INTEGRITY_ERROR", details=details)


class ExternalServiceError(AppException):
    """外部サービスエラー"""
    def __init__(self, message: str, service: str = None, details: dict = None):
        details = details or {}
        if service:
            details["service"] = service
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR", details=details)


class RetryableError(AppException):
    """リトライ可能なエラー"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="RETRYABLE_ERROR", details=details)
