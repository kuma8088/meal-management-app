"""
ロギング設定
"""
import logging
import json
import os
from typing import Any, Dict
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        # 追加のコンテキスト情報を含める
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # extra フィールドを含める
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # 例外情報を含める
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    ロガーを取得する
    
    Args:
        name: ロガー名
        
    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)
    
    # 既にハンドラーが設定されている場合はそのまま返す
    if logger.handlers:
        return logger
    
    # ログレベルを環境変数から取得（デフォルトはINFO）
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # ハンドラーを設定
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # 親ロガーへの伝播を防ぐ
    logger.propagate = False
    
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    コンテキスト情報付きでログを出力する
    
    Args:
        logger: ロガー
        level: ログレベル（"debug", "info", "warning", "error", "critical"）
        message: ログメッセージ
        **kwargs: 追加のコンテキスト情報
    """
    log_func = getattr(logger, level.lower())
    
    # extraフィールドとして追加情報を渡す
    extra = {"extra_data": kwargs}
    log_func(message, extra=extra)
