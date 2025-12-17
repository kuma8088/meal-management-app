/**
 * 食事登録ページ
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from '../contexts/UnifiedAuthContext';
import { createMeal } from '../api/meals';
import { searchFoodsByName } from '../api/foods';
import MealRegistrationForm from '../components/MealRegistrationForm';
import type { MealType, MealFood, Food } from '../types/api';
import './MealRegistrationPage.css';

const MealRegistrationPage: React.FC = () => {
  const { user: _user } = useUnifiedAuth();
  const navigate = useNavigate();
  const [successMessage, setSuccessMessage] = useState<string>('');

  /**
   * 食品検索
   */
  const handleFoodSearch = async (query: string): Promise<Food[]> => {
    const results = await searchFoodsByName(query);
    return results;
  };

  /**
   * 食事登録
   */
  const handleSubmit = async (meal: { meal_type: MealType; timestamp: string; foods: MealFood[] }) => {
    try {
      await createMeal(meal);
      setSuccessMessage('食事を登録しました！');

      // 3秒後に食事記録一覧ページに遷移
      setTimeout(() => {
        navigate('/meals');
      }, 3000);
    } catch (error) {
      throw error; // フォームでエラーハンドリングする
    }
  };

  return (
    <div className="meal-registration-page">
      <div className="meal-registration-container">
        <h1 className="page-title">食事登録</h1>

        <div className="page-intro">
          食品を検索して追加し、食事を記録しましょう。栄養情報が自動的に計算されます。
        </div>

        {successMessage && (
          <div className="success-message">
            {successMessage}
            <br />
            <small>食事記録一覧ページに移動します...</small>
          </div>
        )}

        {!successMessage && (
          <MealRegistrationForm
            onSubmit={handleSubmit}
            onFoodSearch={handleFoodSearch}
          />
        )}
      </div>
    </div>
  );
};

export default MealRegistrationPage;
