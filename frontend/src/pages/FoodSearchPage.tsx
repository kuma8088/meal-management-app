/**
 * 食品検索ページ
 */

import React from 'react';
import FoodSearch from '../components/FoodSearch';
import './FoodSearchPage.css';

const FoodSearchPage: React.FC = () => {
  return (
    <div className="food-search-page">
      <div className="food-search-container">
        <h1 className="page-title">食品検索</h1>

        <div className="page-intro">
          <p>
            食品名またはJANコードで食品を検索できます。
            データベースに見つからない場合は、AI検索を使用することもできます。
          </p>
        </div>

        <FoodSearch />
      </div>
    </div>
  );
};

export default FoodSearchPage;
