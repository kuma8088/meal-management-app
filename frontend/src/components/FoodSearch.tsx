/**
 * 食品検索コンポーネント
 */

import React, { useState } from 'react';
import { searchFoods } from '../api/foods';
import type { Food } from '../types/api';
import './FoodSearch.css';

interface FoodSearchProps {
  onSelectFood?: (food: Food) => void;
  showSelectButton?: boolean;
}

type SearchType = 'name' | 'jan_code';

const FoodSearch: React.FC<FoodSearchProps> = ({
  onSelectFood,
  showSelectButton = false,
}) => {
  const [searchType, setSearchType] = useState<SearchType>('name');
  const [query, setQuery] = useState<string>('');
  const [useAi, setUseAi] = useState<boolean>(false);
  const [results, setResults] = useState<Food[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string>('');
  const [hasSearched, setHasSearched] = useState(false);

  /**
   * 検索実行
   */
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      setError('検索キーワードを入力してください');
      return;
    }

    try {
      setIsSearching(true);
      setError('');
      setHasSearched(true);

      const params =
        searchType === 'name'
          ? { query: query.trim(), use_ai: useAi }
          : { jan_code: query.trim() };

      const foods = await searchFoods(params);
      setResults(foods);

      if (foods.length === 0) {
        setError('該当する食品が見つかりませんでした');
      }
    } catch (err: any) {
      setError(err.error?.message || '検索に失敗しました');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  /**
   * 検索タイプ変更
   */
  const handleSearchTypeChange = (type: SearchType) => {
    setSearchType(type);
    setQuery('');
    setResults([]);
    setError('');
    setHasSearched(false);
  };

  /**
   * 食品の出典バッジ
   */
  const getSourceBadge = (source: string) => {
    const badges: Record<string, { label: string; className: string }> = {
      STANDARD_TABLES: { label: '日本食品標準成分表', className: 'badge-standard' },
      OPEN_FOOD_FACTS: { label: 'Open Food Facts', className: 'badge-open' },
      AI_GENERATED: { label: 'AI生成', className: 'badge-ai' },
    };

    const badge = badges[source] || { label: source, className: 'badge-default' };
    return <span className={`source-badge ${badge.className}`}>{badge.label}</span>;
  };

  return (
    <div className="food-search">
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-type-tabs">
          <button
            type="button"
            className={`tab ${searchType === 'name' ? 'active' : ''}`}
            onClick={() => handleSearchTypeChange('name')}
          >
            食品名で検索
          </button>
          <button
            type="button"
            className={`tab ${searchType === 'jan_code' ? 'active' : ''}`}
            onClick={() => handleSearchTypeChange('jan_code')}
          >
            JANコードで検索
          </button>
        </div>

        <div className="search-input-container">
          <input
            type="text"
            id="search-query"
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              searchType === 'name'
                ? '食品名を入力（例: りんご）'
                : 'JANコードを入力（例: 4901427401234）'
            }
            disabled={isSearching}
          />
          <button
            type="submit"
            className="search-button"
            disabled={isSearching || !query.trim()}
          >
            {isSearching ? '検索中...' : '検索'}
          </button>
        </div>

        {searchType === 'name' && (
          <div className="ai-option">
            <label>
              <input
                type="checkbox"
                checked={useAi}
                onChange={(e) => setUseAi(e.target.checked)}
                disabled={isSearching}
              />
              AI検索を使用（データベースに見つからない場合）
            </label>
          </div>
        )}
      </form>

      {error && <div className="error-message">{error}</div>}

      {hasSearched && results.length > 0 && (
        <div className="search-results">
          <div className="results-header">
            <h3>検索結果 ({results.length}件)</h3>
          </div>

          <div className="results-list">
            {results.map((food) => (
              <div key={food.food_id} className="food-item">
                <div className="food-info">
                  <div className="food-name-row">
                    <h4 className="food-name">{food.name}</h4>
                    {getSourceBadge(food.source)}
                  </div>

                  {food.description && (
                    <p className="food-description">{food.description}</p>
                  )}

                  {food.jan_code && (
                    <p className="food-jan">JANコード: {food.jan_code}</p>
                  )}

                  <div className="nutrition-summary">
                    <div className="nutrition-item">
                      <span className="nutrition-label">カロリー</span>
                      <span className="nutrition-value">
                        {food.calories_per_100g.toFixed(1)}kcal
                      </span>
                    </div>
                    <div className="nutrition-item">
                      <span className="nutrition-label">タンパク質</span>
                      <span className="nutrition-value">
                        {food.protein_per_100g.toFixed(1)}g
                      </span>
                    </div>
                    <div className="nutrition-item">
                      <span className="nutrition-label">脂質</span>
                      <span className="nutrition-value">
                        {food.fat_per_100g.toFixed(1)}g
                      </span>
                    </div>
                    <div className="nutrition-item">
                      <span className="nutrition-label">炭水化物</span>
                      <span className="nutrition-value">
                        {food.carbs_per_100g.toFixed(1)}g
                      </span>
                    </div>
                  </div>
                </div>

                {showSelectButton && onSelectFood && (
                  <button
                    className="select-button"
                    onClick={() => onSelectFood(food)}
                  >
                    選択
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {hasSearched && results.length === 0 && !error && (
        <div className="no-results">
          <p>該当する食品が見つかりませんでした</p>
          {searchType === 'name' && !useAi && (
            <p className="hint">AI検索を有効にすると、より多くの食品を検索できます。</p>
          )}
        </div>
      )}
    </div>
  );
};

export default FoodSearch;
