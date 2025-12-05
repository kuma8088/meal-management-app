"""
共通ライブラリ

このモジュールは、Lambda関数で共通して使用されるユーティリティを提供します。
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

from .food_parser import (
    StandardFoodParser,
    OpenFoodFactsClient,
    FoodMasterImporter
)

from .nutrition_calculator import NutritionCalculator

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

    # Food Parser
    "StandardFoodParser",
    "OpenFoodFactsClient",
    "FoodMasterImporter",
    
    # Nutrition Calculator
    "NutritionCalculator",
]
