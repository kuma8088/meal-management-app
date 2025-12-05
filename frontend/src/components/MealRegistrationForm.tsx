/**
 * 食事登録フォームコンポーネント
 */

import React, { useState } from 'react';
import type { MealType, MealFood, Food } from '../types/api';
import './MealRegistrationForm.css';

interface MealRegistrationFormProps {
  onSubmit: (meal: { meal_type: MealType; timestamp: string; foods: MealFood[] }) => Promise<void>;
  onFoodSearch: (query: string) => Promise<Food[]>;
}

const MealRegistrationForm: React.FC<MealRegistrationFormProps> = ({ onSubmit, onFoodSearch }) => {
  const [mealType, setMealType] = useState<MealType>('breakfast');
  const [timestamp, setTimestamp] = useState<string>(new Date().toISOString().slice(0, 16));
  const [foods, setFoods] = useState<MealFood[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Food[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string>('');

  /**
   * 食品検索
   */
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('食品名を入力してください');
      return;
    }

    try {
      setSearching(true);
      setError('');
      const results = await onFoodSearch(searchQuery);
      setSearchResults(results);

      if (results.length === 0) {
        setError('該当する食品が見つかりませんでした');
      }
    } catch (err: any) {
      setError(err.error?.message || '食品検索に失敗しました');
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  /**
   * 食品を追加
   */
  const handleAddFood = (food: Food) => {
    const newFood: MealFood = {
      food_id: food.food_id,
      name: food.name,
      amount: 100, // デフォルト100g
      unit: 'g',
      calories: food.calories_per_100g,
      protein: food.protein_per_100g,
      fat: food.fat_per_100g,
      carbs: food.carbs_per_100g,
    };

    setFoods([...foods, newFood]);
    setSearchQuery('');
    setSearchResults([]);
  };

  /**
   * 食品を削除
   */
  const handleRemoveFood = (index: number) => {
    setFoods(foods.filter((_, i) => i !== index));
  };

  /**
   * 食品の量を変更
   */
  const handleAmountChange = (index: number, amount: number) => {
    const newFoods = [...foods];
    newFoods[index].amount = amount;
    setFoods(newFoods);
  };

  /**
   * 栄養情報を計算
   */
  const calculateNutrition = () => {
    return foods.reduce(
      (acc, food) => {
        const ratio = food.amount / 100;
        return {
          calories: acc.calories + (food.calories || 0) * ratio,
          protein: acc.protein + (food.protein || 0) * ratio,
          fat: acc.fat + (food.fat || 0) * ratio,
          carbs: acc.carbs + (food.carbs || 0) * ratio,
        };
      },
      { calories: 0, protein: 0, fat: 0, carbs: 0 }
    );
  };

  /**
   * フォーム送信
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (foods.length === 0) {
      setError('少なくとも1つの食品を追加してください');
      return;
    }

    try {
      setLoading(true);
      setError('');

      await onSubmit({
        meal_type: mealType,
        timestamp: new Date(timestamp).toISOString(),
        foods,
      });

      // リセット
      setFoods([]);
      setTimestamp(new Date().toISOString().slice(0, 16));
    } catch (err: any) {
      setError(err.error?.message || '食事の登録に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const nutrition = calculateNutrition();

  return (
    <form className="meal-registration-form" onSubmit={handleSubmit}>
      {/* 食事タイプ */}
      <div className="form-section">
        <label htmlFor="meal-type">食事タイプ</label>
        <select
          id="meal-type"
          value={mealType}
          onChange={(e) => setMealType(e.target.value as MealType)}
          required
        >
          <option value="breakfast">朝食</option>
          <option value="lunch">昼食</option>
          <option value="dinner">夕食</option>
          <option value="snack">間食</option>
        </select>
      </div>

      {/* 日時 */}
      <div className="form-section">
        <label htmlFor="timestamp">日時</label>
        <input
          type="datetime-local"
          id="timestamp"
          value={timestamp}
          onChange={(e) => setTimestamp(e.target.value)}
          required
        />
      </div>

      {/* 食品検索 */}
      <div className="form-section">
        <label htmlFor="food-search">食品検索</label>
        <div className="search-container">
          <input
            type="text"
            id="food-search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleSearch())}
            placeholder="食品名を入力"
          />
          <button
            type="button"
            onClick={handleSearch}
            disabled={searching}
            className="search-button"
          >
            {searching ? '検索中...' : '検索'}
          </button>
        </div>

        {/* 検索結果 */}
        {searchResults.length > 0 && (
          <div className="search-results">
            {searchResults.map((food) => (
              <div key={food.food_id} className="search-result-item">
                <div className="food-info">
                  <div className="food-name">{food.name}</div>
                  <div className="food-nutrition">
                    {food.calories_per_100g.toFixed(1)} kcal / 100g
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleAddFood(food)}
                  className="add-button"
                >
                  追加
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 追加された食品リスト */}
      {foods.length > 0 && (
        <div className="form-section">
          <label>追加された食品</label>
          <div className="foods-list">
            {foods.map((food, index) => (
              <div key={index} className="food-item">
                <div className="food-item-header">
                  <span className="food-item-name">{food.name}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveFood(index)}
                    className="remove-button"
                  >
                    削除
                  </button>
                </div>
                <div className="food-item-amount">
                  <label htmlFor={`amount-${index}`}>量</label>
                  <input
                    type="number"
                    id={`amount-${index}`}
                    value={food.amount}
                    onChange={(e) => handleAmountChange(index, Number(e.target.value))}
                    min="1"
                    step="1"
                    required
                  />
                  <span>{food.unit}</span>
                </div>
                <div className="food-item-nutrition">
                  <span>{((food.calories || 0) * (food.amount / 100)).toFixed(1)} kcal</span>
                  <span>P: {((food.protein || 0) * (food.amount / 100)).toFixed(1)}g</span>
                  <span>F: {((food.fat || 0) * (food.amount / 100)).toFixed(1)}g</span>
                  <span>C: {((food.carbs || 0) * (food.amount / 100)).toFixed(1)}g</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 合計栄養情報 */}
      {foods.length > 0 && (
        <div className="form-section nutrition-summary">
          <label>栄養情報（合計）</label>
          <div className="nutrition-grid">
            <div className="nutrition-item">
              <span className="nutrition-label">カロリー</span>
              <span className="nutrition-value">{nutrition.calories.toFixed(1)} kcal</span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">たんぱく質</span>
              <span className="nutrition-value">{nutrition.protein.toFixed(1)} g</span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">脂質</span>
              <span className="nutrition-value">{nutrition.fat.toFixed(1)} g</span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">炭水化物</span>
              <span className="nutrition-value">{nutrition.carbs.toFixed(1)} g</span>
            </div>
          </div>
        </div>
      )}

      {/* エラーメッセージ */}
      {error && <div className="error-message">{error}</div>}

      {/* 送信ボタン */}
      <button type="submit" disabled={loading || foods.length === 0} className="submit-button">
        {loading ? '登録中...' : '食事を登録'}
      </button>
    </form>
  );
};

export default MealRegistrationForm;
