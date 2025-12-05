"""
リトライロジック
"""
import time
import functools
from typing import Callable, Type, Tuple, Any
from .exceptions import RetryableError
from .logger import get_logger

logger = get_logger(__name__)


def exponential_backoff_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (RetryableError,)
):
    """
    指数バックオフを使用したリトライデコレーター
    
    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本遅延時間（秒）
        max_delay: 最大遅延時間（秒）
        retryable_exceptions: リトライ対象の例外タプル
        
    Returns:
        デコレーター関数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        logger.error(
                            f"最大リトライ回数に達しました: {func.__name__}",
                            extra={
                                "extra_data": {
                                    "function": func.__name__,
                                    "attempt": attempt + 1,
                                    "max_retries": max_retries,
                                    "error": str(e)
                                }
                            }
                        )
                        raise
                    
                    # 指数バックオフで遅延時間を計算
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    logger.warning(
                        f"リトライします: {func.__name__}",
                        extra={
                            "extra_data": {
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "delay": delay,
                                "error": str(e)
                            }
                        }
                    )
                    
                    time.sleep(delay)
            
            # ここには到達しないはずだが、念のため
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator
