/**
 * 食事記録一覧コンポーネント
 */

import React, { useState } from 'react';
import { deleteMeal } from '../api/meals';
import type { Meal } from '../types/api';
import './MealsList.css';

interface MealsListProps {
  meals: Meal[];
  onEdit?: (meal: Meal) => void;
  onDeleteSuccess?: () => void;
  loading?: boolean;
}

const MealsList: React.FC<MealsListProps> = ({
  meals,
  onEdit,
  onDeleteSuccess,
  loading = false,
}) => {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string>('');

  /**
   * 食事記録を削除
   */
  const handleDelete = async (mealId: string) => {
    if (!window.confirm('この食事記録を削除してもよろしいですか？')) {
      return;
    }

    try {
      setDeletingId(mealId);
      setError('');
      await deleteMeal(mealId);
      onDeleteSuccess?.();
    } catch (err: any) {
      setError(err.error?.message || '削除に失敗しました');
    } finally {
      setDeletingId(null);
    }
  };

  /**
   * 食事タイプのラベルを取得
   */
  const getMealTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      breakfast: '朝食',
      lunch: '昼食',
      dinner: '夕食',
      snack: '間食',
    };
    return labels[type] || type;
  };

  /**
   * 日時をフォーマット
   */
  const formatDateTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (meals.length === 0) {
    return (
      <div className="meals-empty">
        <p>食事記録がありません</p>
      </div>
    );
  }

  /**
   * 日付でグループ化
   */
  const mealsByDate = meals.reduce(
    (acc, meal) => {
      const date = new Date(meal.timestamp).toLocaleDateString('ja-JP');
      if (!acc[date]) {
        acc[date] = [];
      }
      acc[date].push(meal);
      return acc;
    },
    {} as Record<string, Meal[]>
  );

  return (
    <div className="meals-list">
      {error && <div className="error-message">{error}</div>}

      {Object.entries(mealsByDate).map(([date, dayMeals]) => {
        // その日の合計栄養情報を計算
        const totalNutrition = dayMeals.reduce(
          (acc, meal) => ({
            calories: acc.calories + meal.total_calories,
            protein: acc.protein + meal.total_protein,
            fat: acc.fat + meal.total_fat,
            carbs: acc.carbs + meal.total_carbs,
          }),
          { calories: 0, protein: 0, fat: 0, carbs: 0 }
        );

        return (
          <div key={date} className="meals-group">
            <div className="date-header">
              <h3 className="date-label">{date}</h3>
              <div className="daily-summary">
                <span className="summary-item">
                  <span className="summary-label">合計:</span>
                  <span className="summary-value">
                    {totalNutrition.calories.toLocaleString()}kcal
                  </span>
                </span>
                <span className="summary-item">
                  <span className="summary-label">タンパク質:</span>
                  <span className="summary-value">
                    {totalNutrition.protein.toFixed(1)}g
                  </span>
                </span>
                <span className="summary-item">
                  <span className="summary-label">脂質:</span>
                  <span className="summary-value">
                    {totalNutrition.fat.toFixed(1)}g
                  </span>
                </span>
                <span className="summary-item">
                  <span className="summary-label">炭水化物:</span>
                  <span className="summary-value">
                    {totalNutrition.carbs.toFixed(1)}g
                  </span>
                </span>
              </div>
            </div>

            <div className="meals-day-list">
              {dayMeals.map((meal) => (
                <div key={meal.meal_id} className="meal-item">
                  <div className="meal-header">
                    <div className="meal-type-and-time">
                      <span className="meal-type">
                        {getMealTypeLabel(meal.meal_type)}
                      </span>
                      <span className="meal-time">
                        {new Date(meal.timestamp).toLocaleTimeString('ja-JP', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <div className="meal-actions">
                      {onEdit && (
                        <button
                          className="action-button edit-button"
                          onClick={() => onEdit(meal)}
                          disabled={loading || deletingId !== null}
                        >
                          編集
                        </button>
                      )}
                      <button
                        className="action-button delete-button"
                        onClick={() => handleDelete(meal.meal_id)}
                        disabled={loading || deletingId === meal.meal_id}
                      >
                        {deletingId === meal.meal_id ? '削除中...' : '削除'}
                      </button>
                    </div>
                  </div>

                  <div className="meal-foods">
                    <h4 className="foods-title">食品</h4>
                    <div className="foods-list">
                      {meal.foods.map((food, index) => (
                        <div key={index} className="food-entry">
                          <div className="food-name">
                            {food.name}
                            <span className="food-amount">
                              {food.amount}
                              {food.unit}
                            </span>
                          </div>
                          {(food.calories ||
                            food.protein ||
                            food.fat ||
                            food.carbs) && (
                            <div className="food-nutrition">
                              {food.calories && (
                                <span className="nutrition-item">
                                  {food.calories.toFixed(0)}kcal
                                </span>
                              )}
                              {food.protein && (
                                <span className="nutrition-item">
                                  P{food.protein.toFixed(1)}g
                                </span>
                              )}
                              {food.fat && (
                                <span className="nutrition-item">
                                  F{food.fat.toFixed(1)}g
                                </span>
                              )}
                              {food.carbs && (
                                <span className="nutrition-item">
                                  C{food.carbs.toFixed(1)}g
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="meal-nutrition">
                    <div className="nutrition-item">
                      <span className="nutrition-label">カロリー</span>
                      <span className="nutrition-value">
                        {meal.total_calories.toLocaleString()}kcal
                      </span>
                    </div>
                    <div className="nutrition-item">
                      <span className="nutrition-label">タンパク質</span>
                      <span className="nutrition-value">
                        {meal.total_protein.toFixed(1)}g
                      </span>
                    </div>
                    <div className="nutrition-item">
                      <span className="nutrition-label">脂質</span>
                      <span className="nutrition-value">
                        {meal.total_fat.toFixed(1)}g
                      </span>
                    </div>
                    <div className="nutrition-item">
                      <span className="nutrition-label">炭水化物</span>
                      <span className="nutrition-value">
                        {meal.total_carbs.toFixed(1)}g
                      </span>
                    </div>
                  </div>

                  <div className="meal-meta">
                    <span className="meta-item">
                      登録日時: {formatDateTime(meal.created_at)}
                    </span>
                    {meal.updated_at !== meal.created_at && (
                      <span className="meta-item">
                        更新日時: {formatDateTime(meal.updated_at)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default MealsList;
