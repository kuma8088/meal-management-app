/**
 * 1日の総評コンポーネント
 */

import React, { useState, useEffect } from 'react';
import { getMeals } from '../api/meals';
import { getDailyAdvice } from '../api/advice';
import type { Meal, DailyAdvice } from '../types/api';
import './DailySummary.css';

interface DailySummaryProps {
  date: string;
  userGoal?: {
    targetCalories?: number;
    targetProtein?: number;
    targetFat?: number;
    targetCarbs?: number;
  };
}

const DailySummary: React.FC<DailySummaryProps> = ({ date, userGoal }) => {
  const [meals, setMeals] = useState<Meal[]>([]);
  const [advice, setAdvice] = useState<DailyAdvice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  /**
   * データを読み込み
   */
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError('');

        // 本日の食事記録を取得
        const mealsData = await getMeals({
          start_date: date,
          end_date: date,
        });
        setMeals(mealsData);

        // AIアドバイスを取得
        try {
          const adviceData = await getDailyAdvice({ date });
          setAdvice(adviceData);
        } catch (err: any) {
          // アドバイス取得失敗は重大なエラーではないので無視
          if (err.error?.code !== 'NOT_FOUND') {
            console.warn('Failed to get advice:', err);
          }
        }
      } catch (err: any) {
        setError(err.error?.message || 'データの読み込みに失敗しました');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [date]);

  /**
   * 合計栄養情報を計算
   */
  const getTotalNutrition = () => {
    return meals.reduce(
      (acc, meal) => ({
        calories: acc.calories + meal.total_calories,
        protein: acc.protein + meal.total_protein,
        fat: acc.fat + meal.total_fat,
        carbs: acc.carbs + meal.total_carbs,
      }),
      { calories: 0, protein: 0, fat: 0, carbs: 0 }
    );
  };

  /**
   * パーセンテージを計算
   */
  const getPercentage = (actual: number, target?: number): number => {
    if (!target || target === 0) return 0;
    return Math.round((actual / target) * 100);
  };

  /**
   * プログレスバーの色を取得
   */
  const getBarColor = (percentage: number): string => {
    if (percentage >= 95 && percentage <= 105) return 'success';
    if (percentage >= 80 && percentage < 95) return 'warning';
    if (percentage > 105) return 'over';
    return 'under';
  };

  if (loading) {
    return <div className="daily-summary loading">読み込み中...</div>;
  }

  const totalNutrition = getTotalNutrition();
  const dateObj = new Date(date);
  const dateStr = dateObj.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  });

  return (
    <div className="daily-summary">
      {error && <div className="error-message">{error}</div>}

      <div className="summary-header">
        <h2>{dateStr}の総評</h2>
        <p className="meal-count">
          食事記録: {meals.length}件
        </p>
      </div>

      {meals.length === 0 ? (
        <div className="no-meals">
          <p>本日の食事記録がありません</p>
        </div>
      ) : (
        <>
          {/* 栄養サマリー */}
          <div className="nutrition-section">
            <h3>栄養情報サマリー</h3>

            <div className="nutrition-bars">
              {/* カロリー */}
              <div className="nutrition-item">
                <div className="nutrition-label">
                  <span className="label-name">カロリー</span>
                  <span className="label-value">
                    {totalNutrition.calories.toLocaleString()}kcal
                  </span>
                </div>
                {userGoal?.targetCalories && (
                  <div className="nutrition-bar-container">
                    <div className="nutrition-bar-background">
                      <div
                        className={`nutrition-bar ${getBarColor(
                          getPercentage(
                            totalNutrition.calories,
                            userGoal.targetCalories
                          )
                        )}`}
                        style={{
                          width: `${Math.min(
                            getPercentage(
                              totalNutrition.calories,
                              userGoal.targetCalories
                            ),
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <div className="nutrition-target">
                      目標: {userGoal.targetCalories.toLocaleString()}kcal
                      ({getPercentage(
                        totalNutrition.calories,
                        userGoal.targetCalories
                      )}
                      %)
                    </div>
                  </div>
                )}
              </div>

              {/* PFC */}
              <div className="pfc-items">
                <div className="nutrition-item">
                  <div className="nutrition-label">
                    <span className="label-name">タンパク質</span>
                    <span className="label-value">
                      {totalNutrition.protein.toFixed(1)}g
                    </span>
                  </div>
                  {userGoal?.targetProtein && (
                    <div className="nutrition-info">
                      目標: {userGoal.targetProtein.toFixed(1)}g
                      ({getPercentage(
                        totalNutrition.protein,
                        userGoal.targetProtein
                      )}
                      %)
                    </div>
                  )}
                </div>

                <div className="nutrition-item">
                  <div className="nutrition-label">
                    <span className="label-name">脂質</span>
                    <span className="label-value">
                      {totalNutrition.fat.toFixed(1)}g
                    </span>
                  </div>
                  {userGoal?.targetFat && (
                    <div className="nutrition-info">
                      目標: {userGoal.targetFat.toFixed(1)}g
                      ({getPercentage(totalNutrition.fat, userGoal.targetFat)}%)
                    </div>
                  )}
                </div>

                <div className="nutrition-item">
                  <div className="nutrition-label">
                    <span className="label-name">炭水化物</span>
                    <span className="label-value">
                      {totalNutrition.carbs.toFixed(1)}g
                    </span>
                  </div>
                  {userGoal?.targetCarbs && (
                    <div className="nutrition-info">
                      目標: {userGoal.targetCarbs.toFixed(1)}g
                      ({getPercentage(
                        totalNutrition.carbs,
                        userGoal.targetCarbs
                      )}
                      %)
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* AIアドバイス */}
          {advice && (
            <div className="advice-section">
              <h3>AI栄養アドバイス</h3>

              <div className="advice-content">
                <p className="advice-text">{advice.advice}</p>
              </div>

              <div className="advice-info">
                <span className="usage-count">
                  本日の利用回数: {advice.usage_count} / {advice.max_usage}
                </span>
                {advice.usage_count >= advice.max_usage && (
                  <span className="usage-limit-reached">
                    利用制限に達しました
                  </span>
                )}
              </div>
            </div>
          )}

          {/* 統計情報 */}
          <div className="stats-section">
            <h3>摂取量分析</h3>

            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">カロリーバランス</div>
                <div className="stat-value">
                  {userGoal?.targetCalories
                    ? totalNutrition.calories - userGoal.targetCalories > 0
                      ? `+${(totalNutrition.calories - userGoal.targetCalories).toLocaleString()} kcal`
                      : `${(totalNutrition.calories - userGoal.targetCalories).toLocaleString()} kcal`
                    : '-'}
                </div>
                {userGoal?.targetCalories && (
                  <div
                    className={`stat-description ${
                      totalNutrition.calories > userGoal.targetCalories
                        ? 'over'
                        : 'under'
                    }`}
                  >
                    {totalNutrition.calories > userGoal.targetCalories
                      ? '目標超過'
                      : '目標未達'}
                  </div>
                )}
              </div>

              <div className="stat-card">
                <div className="stat-label">PFCバランス</div>
                <div className="stat-grid-mini">
                  <div className="ratio">
                    <span className="ratio-label">P</span>
                    <span className="ratio-value">
                      {totalNutrition.calories > 0
                        ? (
                            (totalNutrition.protein * 4) /
                            totalNutrition.calories *
                            100
                          ).toFixed(1)
                        : 0}
                      %
                    </span>
                  </div>
                  <div className="ratio">
                    <span className="ratio-label">F</span>
                    <span className="ratio-value">
                      {totalNutrition.calories > 0
                        ? (
                            (totalNutrition.fat * 9) /
                            totalNutrition.calories *
                            100
                          ).toFixed(1)
                        : 0}
                      %
                    </span>
                  </div>
                  <div className="ratio">
                    <span className="ratio-label">C</span>
                    <span className="ratio-value">
                      {totalNutrition.calories > 0
                        ? (
                            (totalNutrition.carbs * 4) /
                            totalNutrition.calories *
                            100
                          ).toFixed(1)
                        : 0}
                      %
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DailySummary;
