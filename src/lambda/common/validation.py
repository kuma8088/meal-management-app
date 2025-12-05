"""
バリデーションユーティリティ
"""
from typing import Any, Optional, List
from datetime import datetime
from .exceptions import ValidationError


def validate_required(value: Any, field_name: str) -> None:
    """
    必須フィールドの検証
    
    Args:
        value: 検証する値
        field_name: フィールド名
        
    Raises:
        ValidationError: 値がNoneまたは空の場合
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(
            f"{field_name}は必須です",
            details={"field": field_name}
        )


def validate_positive_number(value: float, field_name: str) -> None:
    """
    正の数値の検証
    
    Args:
        value: 検証する値
        field_name: フィールド名
        
    Raises:
        ValidationError: 値が正の数値でない場合
    """
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValidationError(
            f"{field_name}は正の数値である必要があります",
            details={"field": field_name, "value": value}
        )


def validate_non_negative_number(value: float, field_name: str) -> None:
    """
    非負の数値の検証
    
    Args:
        value: 検証する値
        field_name: フィールド名
        
    Raises:
        ValidationError: 値が非負の数値でない場合
    """
    if not isinstance(value, (int, float)) or value < 0:
        raise ValidationError(
            f"{field_name}は0以上の数値である必要があります",
            details={"field": field_name, "value": value}
        )


def validate_range(value: float, field_name: str, min_value: float, max_value: float) -> None:
    """
    範囲の検証
    
    Args:
        value: 検証する値
        field_name: フィールド名
        min_value: 最小値
        max_value: 最大値
        
    Raises:
        ValidationError: 値が範囲外の場合
    """
    if not isinstance(value, (int, float)) or value < min_value or value > max_value:
        raise ValidationError(
            f"{field_name}は{min_value}から{max_value}の範囲である必要があります",
            details={
                "field": field_name,
                "value": value,
                "min": min_value,
                "max": max_value
            }
        )


def validate_choice(value: str, field_name: str, choices: List[str]) -> None:
    """
    選択肢の検証
    
    Args:
        value: 検証する値
        field_name: フィールド名
        choices: 有効な選択肢のリスト
        
    Raises:
        ValidationError: 値が選択肢に含まれない場合
    """
    if value not in choices:
        raise ValidationError(
            f"{field_name}は{', '.join(choices)}のいずれかである必要があります",
            details={
                "field": field_name,
                "value": value,
                "choices": choices
            }
        )


def validate_date_format(date_str: str, field_name: str, format_str: str = "%Y-%m-%d") -> None:
    """
    日付形式の検証
    
    Args:
        date_str: 検証する日付文字列
        field_name: フィールド名
        format_str: 期待される日付形式
        
    Raises:
        ValidationError: 日付形式が不正な場合
    """
    try:
        datetime.strptime(date_str, format_str)
    except (ValueError, TypeError):
        raise ValidationError(
            f"{field_name}の形式が不正です（期待される形式: {format_str}）",
            details={
                "field": field_name,
                "value": date_str,
                "expected_format": format_str
            }
        )


def validate_email(email: str, field_name: str = "email") -> None:
    """
    メールアドレスの検証（簡易版）
    
    Args:
        email: 検証するメールアドレス
        field_name: フィールド名
        
    Raises:
        ValidationError: メールアドレス形式が不正な場合
    """
    if not isinstance(email, str) or "@" not in email or "." not in email.split("@")[-1]:
        raise ValidationError(
            f"{field_name}の形式が不正です",
            details={"field": field_name, "value": email}
        )


def validate_string_length(
    value: str,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> None:
    """
    文字列長の検証
    
    Args:
        value: 検証する文字列
        field_name: フィールド名
        min_length: 最小文字数
        max_length: 最大文字数
        
    Raises:
        ValidationError: 文字列長が範囲外の場合
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name}は文字列である必要があります",
            details={"field": field_name, "value": value}
        )
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        raise ValidationError(
            f"{field_name}は{min_length}文字以上である必要があります",
            details={
                "field": field_name,
                "length": length,
                "min_length": min_length
            }
        )
    
    if max_length is not None and length > max_length:
        raise ValidationError(
            f"{field_name}は{max_length}文字以下である必要があります",
            details={
                "field": field_name,
                "length": length,
                "max_length": max_length
            }
        )
