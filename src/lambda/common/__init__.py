"""
共通ライブラリ

このモジュールは、Lambda関数で共通して使用されるユーティリティを提供します。

注意: 一部のモジュール（food_parser, barcode_recognition等）は外部依存関係が
必要なため、デフォルトではインポートされません。必要に応じて明示的にインポートしてください。

例:
    from common.food_parser import StandardFoodParser
    from common.barcode_recognition import BarcodeRecognition
"""

from .exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    DataIntegrityError,
    ExternalServiceError,
    RetryableError
)

from .logger import get_logger, log_with_context

from .dynamodb_helper import DynamoDBHelper

from .s3_helper import S3Helper

from .validation import (
    validate_required,
    validate_positive_number,
    validate_non_negative_number,
    validate_range,
    validate_choice,
    validate_date_format,
    validate_email,
    validate_string_length
)

from .retry import exponential_backoff_retry

from .response import (
    create_response,
    success_response,
    error_response
)

from .models import (
    User,
    Meal,
    MealFood,
    Food,
    Goal,
    AdviceUsage,
    Gender,
    ActivityLevel,
    MealType,
    GoalType,
    FoodSource
)

from .nutrition_calculator import NutritionCalculator

from .bmr_calculator import BMRCalculator

from .goal_calculator import GoalCalculator

from .profile_manager import ProfileManager

from .food_search import FoodSearch

from .ai_food_search import AIFoodSearch

# 以下のモジュールは外部依存関係（requests）が必要なため、
# デフォルトではインポートしない。必要に応じて明示的にインポートすること。
# from .food_parser import StandardFoodParser, OpenFoodFactsClient, FoodMasterImporter
from .barcode_recognition import BarcodeRecognition

__all__ = [
    # Exceptions
    "AppException",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "DataIntegrityError",
    "ExternalServiceError",
    "RetryableError",

    # Logger
    "get_logger",
    "log_with_context",

    # Helpers
    "DynamoDBHelper",
    "S3Helper",

    # Validation
    "validate_required",
    "validate_positive_number",
    "validate_non_negative_number",
    "validate_range",
    "validate_choice",
    "validate_date_format",
    "validate_email",
    "validate_string_length",

    # Retry
    "exponential_backoff_retry",

    # Response
    "create_response",
    "success_response",
    "error_response",

    # Models
    "User",
    "Meal",
    "MealFood",
    "Food",
    "Goal",
    "AdviceUsage",
    "Gender",
    "ActivityLevel",
    "MealType",
    "GoalType",
    "FoodSource",

    # Nutrition Calculator
    "NutritionCalculator",

    # BMR Calculator
    "BMRCalculator",

    # Goal Calculator
    "GoalCalculator",

    # Profile Manager
    "ProfileManager",

    # Food Search
    "FoodSearch",

    # AI Food Search
    "AIFoodSearch",

    # Barcode Recognition
    "BarcodeRecognition",
]
