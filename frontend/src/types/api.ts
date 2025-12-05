/**
 * API型定義
 *
 * バックエンドAPIのリクエスト・レスポンス型を定義
 */

// ========================================
// 共通型
// ========================================

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    request_id?: string;
  };
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}

// ========================================
// ユーザー関連
// ========================================

export type Gender = 'male' | 'female';
export type ActivityLevel = 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';

export interface UserProfile {
  user_id: string;
  age: number;
  height: number;
  weight: number;
  gender: Gender;
  activity_level: ActivityLevel;
  bmr?: number;
  tdee?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateUserProfileRequest {
  age: number;
  height: number;
  weight: number;
  gender: Gender;
  activity_level: ActivityLevel;
}

export interface UpdateUserProfileRequest {
  age?: number;
  height?: number;
  weight?: number;
  gender?: Gender;
  activity_level?: ActivityLevel;
}

// ========================================
// 目標管理
// ========================================

export type GoalType = 'gain' | 'maintain' | 'lose';

export interface Goal {
  goal_id: string;
  user_id: string;
  goal_type: GoalType;
  target_weight: number;
  target_date: string;
  target_calories: number;
  recommended_protein: number;
  recommended_fat: number;
  recommended_carbs: number;
  recommended_exercise_minutes?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateGoalRequest {
  goal_type: GoalType;
  target_weight: number;
  target_date: string;
}

// ========================================
// 食事記録
// ========================================

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

export interface MealFood {
  food_id?: string;
  name: string;
  amount: number;
  unit: string;
  calories?: number;
  protein?: number;
  fat?: number;
  carbs?: number;
}

export interface Meal {
  meal_id: string;
  user_id: string;
  meal_type: MealType;
  timestamp: string;
  foods: MealFood[];
  total_calories: number;
  total_protein: number;
  total_fat: number;
  total_carbs: number;
  created_at: string;
  updated_at: string;
}

export interface CreateMealRequest {
  meal_type: MealType;
  timestamp: string;
  foods: MealFood[];
}

export interface UpdateMealRequest {
  meal_type?: MealType;
  timestamp?: string;
  foods?: MealFood[];
}

export interface GetMealsParams extends PaginationParams {
  start_date?: string;
  end_date?: string;
}

// ========================================
// 食品検索
// ========================================

export type FoodSource = 'STANDARD_TABLES' | 'OPEN_FOOD_FACTS' | 'AI_GENERATED';

export interface Food {
  food_id: string;
  name: string;
  calories_per_100g: number;
  protein_per_100g: number;
  fat_per_100g: number;
  carbs_per_100g: number;
  jan_code?: string;
  source: FoodSource;
  description?: string;
}

export interface SearchFoodParams {
  query?: string;
  jan_code?: string;
  use_ai?: boolean;
  limit?: number;
}

// ========================================
// AIアドバイス
// ========================================

export interface DailyAdvice {
  date: string;
  total_calories: number;
  total_protein: number;
  total_fat: number;
  total_carbs: number;
  target_calories?: number;
  target_protein?: number;
  target_fat?: number;
  target_carbs?: number;
  advice: string;
  usage_count: number;
  max_usage: number;
}

export interface GetDailyAdviceRequest {
  date: string;
}

// ========================================
// 認証
// ========================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface SignUpRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  idToken: string;
}
